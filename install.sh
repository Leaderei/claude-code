#!/usr/bin/env bash
# Instala a configuracao de autonomia do Claude Code + o auto-refresh do clasp.
#
# Rode VOCE MESMO, na sua maquina:
#     ./install.sh            # instala tudo
#     ./install.sh --dry-run  # so mostra o que faria
#
# O Claude nao consegue rodar isto sozinho: o classificador do auto mode bloqueia
# o agente quando ele tenta mexer nas proprias permissoes. E de proposito.

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR_CLAUDE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$DIR_CLAUDE/settings.json"
DIR_CLASP="$DIR_CLAUDE/clasp"
DRY_RUN=0

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

diga()  { printf '  %s\n' "$*"; }
titulo(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

command -v python3 >/dev/null || { echo "erro: python3 e necessario"; exit 1; }

titulo "1. Backup"
mkdir -p "$DIR_CLAUDE"
if [[ -f "$SETTINGS" ]]; then
  BACKUP="$SETTINGS.bak.$(date +%Y%m%d-%H%M%S)"
  if [[ $DRY_RUN -eq 0 ]]; then
    cp "$SETTINGS" "$BACKUP"
    diga "settings.json salvo em $BACKUP"
  else
    diga "[dry-run] copiaria $SETTINGS -> $BACKUP"
  fi
else
  diga "nao existe settings.json ainda; sera criado"
fi

titulo "2. Permissoes"
if [[ $DRY_RUN -eq 0 ]]; then
  python3 - "$SETTINGS" "$AQUI/config/permissions.json" <<'PYEOF'
import json, os, sys

destino, origem = sys.argv[1], sys.argv[2]

atual = {}
if os.path.exists(destino):
    with open(destino, encoding="utf-8") as fh:
        conteudo = fh.read().strip()
    if conteudo:
        atual = json.loads(conteudo)

with open(origem, encoding="utf-8") as fh:
    novo = json.load(fh)["permissions"]

perms = atual.setdefault("permissions", {})

# defaultMode: nao sobrescreve uma escolha explicita que nao seja 'default'.
anterior = perms.get("defaultMode")
if anterior in (None, "default", "manual"):
    perms["defaultMode"] = novo["defaultMode"]
    print(f"  defaultMode: {anterior or '(nenhum)'} -> {novo['defaultMode']}")
else:
    print(f"  defaultMode: mantido em '{anterior}' (ja estava configurado)")

# allow/ask/deny: uniao, preservando o que ja existia e a ordem.
for chave in ("allow", "ask", "deny"):
    existentes = perms.get(chave, [])
    vistos = set(existentes)
    adicionados = [r for r in novo[chave] if r not in vistos]
    perms[chave] = existentes + adicionados
    print(f"  {chave}: {len(existentes)} existentes + {len(adicionados)} novas = {len(perms[chave])}")

tmp = destino + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(atual, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
os.replace(tmp, destino)
PYEOF
else
  diga "[dry-run] fundiria config/permissions.json em $SETTINGS"
fi

titulo "3. Auto-refresh do clasp"
if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "$DIR_CLASP"
  chmod 700 "$DIR_CLASP"
  cp "$AQUI/bin/clasp-refresh.py" "$DIR_CLASP/clasp-refresh.py"
  cp "$AQUI/bin/clasp-doctor.sh"  "$DIR_CLASP/clasp-doctor.sh"
  chmod +x "$DIR_CLASP/clasp-refresh.py" "$DIR_CLASP/clasp-doctor.sh"
  diga "scripts instalados em $DIR_CLASP"
else
  diga "[dry-run] copiaria clasp-refresh.py e clasp-doctor.sh para $DIR_CLASP"
fi

titulo "4. Hook SessionStart (renova o token a cada sessao)"
# Usa '~' quando o caminho e o padrao, para o settings.json ficar portatil;
# caso contrario grava o caminho real de CLAUDE_CONFIG_DIR.
if [[ "$DIR_CLASP" == "$HOME/.claude/clasp" ]]; then
  HOOK_CMD="~/.claude/clasp/clasp-refresh.py --quiet || true"
else
  HOOK_CMD="$DIR_CLASP/clasp-refresh.py --quiet || true"
fi

if [[ $DRY_RUN -eq 0 ]]; then
  python3 - "$SETTINGS" "$HOOK_CMD" <<'PYEOF'
import json, os, sys

destino = sys.argv[1]
comando = sys.argv[2]

with open(destino, encoding="utf-8") as fh:
    cfg = json.load(fh)

hooks = cfg.setdefault("hooks", {})
sessao = hooks.setdefault("SessionStart", [])

ja_existe = any(
    h.get("command") == comando
    for grupo in sessao
    for h in grupo.get("hooks", [])
)

if ja_existe:
    print("  hook ja estava instalado; nada a fazer")
else:
    sessao.append({"hooks": [{"type": "command", "command": comando}]})
    tmp = destino + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, destino)
    print("  hook SessionStart adicionado")
PYEOF
else
  diga "[dry-run] adicionaria o hook SessionStart"
fi

titulo "5. Verificacao"
if [[ $DRY_RUN -eq 0 ]]; then
  python3 -m json.tool "$SETTINGS" >/dev/null && diga "settings.json continua sendo JSON valido"
  diga "rode 'claude' e confira com /status e /permissions"
  diga "para o clasp: $DIR_CLASP/clasp-doctor.sh"
else
  diga "[dry-run] nada foi alterado"
fi

printf '\n'
