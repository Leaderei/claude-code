#!/usr/bin/env bash
# Descobre por que o Claude Code ainda pede permissao pra tudo.
# Somente leitura: nao altera nenhum arquivo.

set -uo pipefail

DIR_CLAUDE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

titulo(){ printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '  \033[32mOK\033[0m    %s\n' "$*"; }
alerta(){ printf '  \033[33mAVISO\033[0m %s\n' "$*"; }
erro()  { printf '  \033[31mFALHA\033[0m %s\n' "$*"; }

le_modo() {  # $1 = arquivo json -> imprime o defaultMode ou vazio
  [[ -f "$1" ]] || return 1
  python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1],encoding='utf-8'))
except Exception as e:
    print('ERRO_JSON'); sys.exit(0)
print(d.get('permissions',{}).get('defaultMode',''))
" "$1" 2>/dev/null
}

conta_regras() {
  [[ -f "$1" ]] || return 1
  python3 -c "
import json,sys
try:
    p=json.load(open(sys.argv[1],encoding='utf-8')).get('permissions',{})
except Exception:
    sys.exit(0)
print('allow=%d ask=%d deny=%d' % (len(p.get('allow',[])),len(p.get('ask',[])),len(p.get('deny',[]))))
" "$1" 2>/dev/null
}

titulo "Versao"
if command -v claude >/dev/null 2>&1; then
  ok "$(claude --version 2>&1 | head -1)"
else
  alerta "'claude' nao esta no PATH (talvez voce use so a extensao/desktop)"
fi

titulo "Suas configuracoes ($DIR_CLAUDE/settings.json)"
USER_SETTINGS="$DIR_CLAUDE/settings.json"
if [[ -f "$USER_SETTINGS" ]]; then
  MODO=$(le_modo "$USER_SETTINGS")
  if [[ "$MODO" == "ERRO_JSON" ]]; then
    erro "JSON invalido -- o Claude Code ignora o arquivo inteiro assim"
  elif [[ "$MODO" == "auto" ]]; then
    ok "defaultMode = auto (e o lugar certo pra isso)"
  elif [[ -z "$MODO" ]]; then
    alerta "sem defaultMode. Em Pro/Max/Team o padrao embutido ja e 'auto',"
    alerta "mas deixar explicito evita surpresa."
  else
    alerta "defaultMode = '$MODO' -- e isso que esta te fazendo aprovar tudo"
  fi
  REGRAS=$(conta_regras "$USER_SETTINGS")
  [[ -n "$REGRAS" ]] && ok "regras: $REGRAS"
else
  alerta "nao existe -- rode ./install.sh"
fi

titulo "Configuracoes do projeto atual"
ACHOU_PROJ=0
for ARQ in .claude/settings.json .claude/settings.local.json; do
  if [[ -f "$ARQ" ]]; then
    ACHOU_PROJ=1
    MODO=$(le_modo "$ARQ")
    if [[ "$MODO" == "auto" ]]; then
      erro "$ARQ define defaultMode='auto' -- IGNORADO nesse arquivo."
      erro "  Pior: por causa disso o Claude Code passa a usar o padrao embutido"
      erro "  e nem le o defaultMode do seu ~/.claude/settings.json. Remova daqui."
    elif [[ -n "$MODO" && "$MODO" != "ERRO_JSON" ]]; then
      alerta "$ARQ define defaultMode='$MODO', que tem prioridade sobre o seu global"
    elif [[ "$MODO" == "ERRO_JSON" ]]; then
      erro "$ARQ tem JSON invalido"
    else
      ok "$ARQ existe, sem defaultMode (nao interfere)"
    fi
  fi
done
[[ $ACHOU_PROJ -eq 0 ]] && ok "nenhuma config de projeto sobrepondo a sua"

titulo "Politica da organizacao (managed settings)"
ACHOU_MGMT=0
for ARQ in \
  "/Library/Application Support/ClaudeCode/managed-settings.json" \
  "/etc/claude-code/managed-settings.json"
do
  if [[ -f "$ARQ" ]]; then
    ACHOU_MGMT=1
    alerta "existe: $ARQ (tem prioridade maxima, acima de tudo)"
    MODO=$(le_modo "$ARQ")
    [[ -n "$MODO" && "$MODO" != "ERRO_JSON" ]] && alerta "  defaultMode = '$MODO'"
    if grep -q '"disableAutoMode"' "$ARQ" 2>/dev/null; then
      erro "  disableAutoMode presente: o auto mode foi desligado pela sua org."
      erro "  Nesse caso so o allowlist resolve; fale com o admin do workspace."
    fi
  fi
done
[[ $ACHOU_MGMT -eq 0 ]] && ok "nenhuma politica gerenciada instalada"

titulo "disableAutoMode nas suas proprias configs"
ACHOU_DAM=0
for ARQ in "$USER_SETTINGS" .claude/settings.json .claude/settings.local.json; do
  if [[ -f "$ARQ" ]] && grep -q '"disableAutoMode"' "$ARQ" 2>/dev/null; then
    erro "$ARQ desliga o auto mode"
    ACHOU_DAM=1
  fi
done
[[ $ACHOU_DAM -eq 0 ]] && ok "nada desligando o auto mode"

titulo "Resumo"
cat <<'FIM'
  Se o auto mode continuar indisponivel mesmo com tudo verde acima, as causas
  restantes sao: (a) plano sem auto mode, (b) modelo selecionado nao suporta,
  (c) sessao na web/nuvem, onde o seletor mostra 'Accept edits' em vez de Manual.
  Confirme dentro do Claude Code com /status e alterne o modo com Shift+Tab.
FIM
printf '\n'
