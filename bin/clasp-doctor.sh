#!/usr/bin/env bash
# Diagnostica por que o clasp fica pedindo `clasp login` toda hora.
# Somente leitura: nao altera nada (exceto se voce passar --refresh).

set -uo pipefail

CLASPRC="${CLASPRC:-$HOME/.clasprc.json}"
REFRESHER="$(dirname "${BASH_SOURCE[0]}")/clasp-refresh.py"
[[ -f "$REFRESHER" ]] || REFRESHER="$HOME/.claude/clasp/clasp-refresh.py"

titulo(){ printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '  \033[32mOK\033[0m    %s\n' "$*"; }
alerta(){ printf '  \033[33mAVISO\033[0m %s\n' "$*"; }
erro()  { printf '  \033[31mFALHA\033[0m %s\n' "$*"; }

titulo "clasp"
if command -v clasp >/dev/null 2>&1; then
  ok "instalado: $(clasp --version 2>&1 | head -1)"
else
  erro "clasp nao esta no PATH"
fi

titulo "Credencial global ($CLASPRC)"
if [[ -f "$CLASPRC" ]]; then
  ok "existe"
  PERM=$(stat -c '%a' "$CLASPRC" 2>/dev/null || stat -f '%Lp' "$CLASPRC" 2>/dev/null)
  if [[ "$PERM" == "600" ]]; then
    ok "permissoes $PERM"
  else
    alerta "permissoes $PERM (o ideal e 600 - contem seu refresh_token)"
  fi

  MOD=$(stat -c '%Y' "$CLASPRC" 2>/dev/null || stat -f '%m' "$CLASPRC" 2>/dev/null)
  AGORA=$(date +%s)
  DIAS=$(( (AGORA - MOD) / 86400 ))
  if [[ $DIAS -ge 1 ]]; then
    alerta "nao e reescrito ha $DIAS dia(s) -- e exatamente o bug: o clasp renova"
    alerta "o token em memoria mas nao grava de volta, entao o arquivo envelhece."
  else
    ok "reescrito hoje"
  fi
else
  erro "nao existe -- rode \`clasp login\` uma vez"
fi

titulo "Estado do token"
if [[ ! -f "$CLASPRC" ]]; then
  alerta "sem credencial para inspecionar; pulei"
elif [[ ! -f "$REFRESHER" ]]; then
  alerta "clasp-refresh.py nao encontrado; pulei"
else
  python3 "$REFRESHER" --file "$CLASPRC" --status 2>&1 | sed 's/^/  /'
fi

titulo "Credencial local no projeto atual"
if [[ -f ".clasprc.json" ]]; then
  alerta "existe um .clasprc.json AQUI, em $(pwd)"
  alerta "ele tem prioridade sobre o global e pode estar vencido de forma independente."
else
  ok "nenhum .clasprc.json local sobrepondo o global"
fi

titulo "Backup"
BKP="$HOME/.claude/clasp/clasprc.backup.json"
if [[ -f "$BKP" ]]; then
  ok "backup presente ($BKP)"
else
  alerta "sem backup ainda -- ele e criado no primeiro refresh bem-sucedido"
fi

titulo "Hook SessionStart do Claude Code"
if grep -q "clasp-refresh" "$HOME/.claude/settings.json" 2>/dev/null; then
  ok "hook instalado"
else
  alerta "hook nao instalado -- rode ./install.sh"
fi

titulo "Renovacao automatica agendada (cron)"
if crontab -l 2>/dev/null | grep -q "clasp-refresh"; then
  ok "entrada de cron presente"
else
  alerta "sem cron. O hook cobre as sessoes do Claude Code; para o terminal"
  alerta "avulso, veja docs/AUTONOMIA.md (secao 'Renovar fora do Claude Code')."
fi

if [[ "${1:-}" == "--refresh" ]]; then
  titulo "Teste real de renovacao"
  python3 "$REFRESHER" --file "$CLASPRC" --force 2>&1 | sed 's/^/  /'
  RC=${PIPESTATUS[0]}
  case $RC in
    0) ok 'renovacao funcionou. O `clasp login` diario nao e mais necessario.' ;;
    3) erro "o refresh_token nao vale mais. Causas mais comuns, nesta ordem:"
       erro "  1. Tela de consentimento OAuth em 'Testing' -> refresh token morre em 7 dias."
       erro "     Publique o app como 'In production' no Google Cloud Console."
       erro "  2. Politica de sessao do Google Workspace forcando reauth (Admin ->"
       erro "     Seguranca -> Controle de sessao do Google Cloud). Ajuste para 'Nunca'."
       erro "  3. Voce passou de 50 refresh tokens ativos para o mesmo par app/usuario:"
       erro "     o Google revoga os mais antigos silenciosamente."
       ;;
    *) erro "erro inesperado (rc=$RC)" ;;
  esac
fi

printf '\n'
