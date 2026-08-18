# Deixando o Claude Code mais autônomo

Dois incômodos, duas causas completamente diferentes.

---

## Parte 1 — Parar de aprovar tudo

### O que já deveria estar acontecendo

O Claude Code tem um **auto mode**: em vez de *você* aprovar cada ação, um segundo
modelo (o classificador) revisa cada chamada antes dela rodar e bloqueia o que
escapa do que você pediu. Nos planos Pro, Max e Team **o auto mode já é o modo
inicial embutido**.

Ou seja: se você está aprovando tudo na mão, provavelmente algo está desligando
o auto mode — não é o comportamento padrão.

### As causas, em ordem de probabilidade

**1. `defaultMode` num arquivo onde ele não vale (a pegadinha).**

`"defaultMode": "auto"` **só tem efeito em `~/.claude/settings.json`**. Se estiver
em `.claude/settings.json` ou `.claude/settings.local.json` do projeto, o Claude
Code ignora — e, pior, ao ignorar ele passa a usar o padrão embutido e **deixa de
ler o `defaultMode` do seu arquivo global também**. Uma linha no lugar errado
derruba a configuração inteira, sem mensagem de erro.

**2. Algum `defaultMode` de projeto sobrepondo o seu.** Precedência: managed
settings > projeto > `.local` > seu global. Um `"defaultMode": "default"` no
projeto ganha do seu global.

**3. Política da organização.** Se o admin do workspace setou
`permissions.disableAutoMode: "disable"` nos managed settings, o auto mode some
do ciclo `Shift+Tab` e não tem jeito do seu lado — só o allowlist ajuda.

**4. Sessão na web/nuvem.** Lá o seletor mostra "Accept edits" em vez de Manual, e
o auto mode só aparece se sua org permitir e o modelo suportar.

`./bin/claude-doctor.sh` checa os quatro casos.

### O allowlist

Auto mode e allowlist resolvem coisas diferentes e se somam:

- **auto mode** julga *contexto* — "essa ação combina com o que ele pediu?"
- **allowlist** dispensa julgamento pra comandos que você já decidiu que são
  sempre OK, e é a única saída quando o auto mode não está disponível.

O `config/permissions.json` traz ~70 regras: leitura e navegação (`ls`, `cat`,
`grep`, `find`, `jq`), git de leitura e o ciclo `add`/`commit`, `npm run`, e os
comandos de `clasp` do dia a dia.

**Sintaxe que importa:** `Bash(ls *)` — com espaço antes do `*` — exige limite de
palavra, então casa com `ls -la` mas **não** com `lsof`. Já `Bash(ls*)` casaria com
os dois. O sufixo `:*` é equivalente ao ` *`, mas só no fim do padrão.

### O que eu deixei perguntando de propósito

Está em `ask`, e recomendo manter:

| Regra | Por quê |
|---|---|
| `git push --force`, `git push -f` | reescreve histórico remoto, irreversível |
| `git reset --hard` | descarta trabalho não commitado |
| `clasp deploy *` | publica pra produção do Apps Script |
| `rm -rf *` | óbvio |

E em `deny`: `sudo`, `dd`, `mkfs`, além de leitura de `.env`, `~/.ssh`, `~/.aws` e
do próprio `~/.clasprc.json` — que guarda seu refresh token.

`deny` e `ask` **vencem** `allow`, sempre. Uma regra `deny` ampla não admite
exceção: `Bash(aws *)` em deny bloqueia até um `Bash(aws s3 ls)` que esteja em allow.

### O que eu não recomendo

`"defaultMode": "bypassPermissions"` mata todo prompt, incluindo escrita em `.git`
e `.claude`. Só faz sentido em container descartável. Na sua máquina, com acesso a
HubSpot, Pipedrive, Drive e Apps Script da Leaderei, o custo de um erro é alto
demais pro ganho — auto mode + allowlist já elimina quase todo prompt e mantém
uma rede de proteção.

### Uma observação honesta sobre este pacote

Ao montar isso, **o classificador me bloqueou** três vezes seguidas: escrever o
JSON de permissões via shell, e até só validar sua sintaxe. Ele trata "o agente
mexendo nas próprias permissões" como escalada de privilégio — corretamente.

Por isso o `install.sh` é feito pra **você** rodar. Não é cerimônia: eu
genuinamente não consigo instalar isso sozinho, e é bom que seja assim.

---

## Parte 2 — Parar de fazer `clasp login` todo dia

### A causa raiz

O `clasp` guarda em `~/.clasprc.json` um `access_token` (vida curta, ~1h) e um
`refresh_token` (vida longa). Quando o access token vence, ele renova **em
memória** — mas [não regrava o arquivo em disco](https://github.com/google/clasp/issues/854).

Resultado: o arquivo envelhece, o token nele vence de vez, e o clasp pede login de
novo. **Seu `refresh_token` está lá, vivo e válido — só não está sendo usado.**

### A solução

`bin/clasp-refresh.py` faz o que o clasp não faz: troca o refresh token por um
access token novo e **grava de volta**. Enquanto o refresh token viver, `clasp
login` deixa de ser necessário.

Detalhes que valem notar:

- **Agnóstico de formato.** O layout do `.clasprc.json` mudou entre v2 e v3, então
  o script varre a árvore JSON procurando as chaves onde elas estiverem, em vez de
  assumir um formato. Testado contra os dois.
- **Preserva a estrutura.** Escreve de volta no mesmo dicionário de origem.
- **Escrita atômica**, permissão `600`.
- **Backup automático** em `~/.claude/clasp/clasprc.backup.json` a cada renovação
  bem-sucedida — e restaura sozinho se o `.clasprc.json` sumir.
- **Só renova quando falta menos de 10 min**, salvo `--force`.

O `install.sh` registra um hook `SessionStart`, então toda sessão do Claude Code
já começa com token válido.

### Renovar fora do Claude Code

O hook cobre as sessões do Claude Code. Pro terminal avulso, agende:

```bash
crontab -e
# renova a cada 30 minutos
*/30 * * * * $HOME/.claude/clasp/clasp-refresh.py --quiet >> $HOME/.claude/clasp/refresh.log 2>&1
```

No macOS, o cron pode não ter permissão de rede por padrão — se falhar, use um
`launchd` agent com `StartInterval` de 1800, ou simplesmente rode
`clasp-refresh.py` antes do seu `clasp push`.

### Quando `clasp login` é mesmo inevitável

Só quando o **refresh token** morre. Aí o script sai com código 3 e avisa. Causas,
em ordem de frequência:

1. **Tela de consentimento OAuth em "Testing"** no Google Cloud Console → o Google
   expira todo refresh token em **7 dias**. Correção: publique o app como
   *In production*. Essa é a causa mais comum de "expira sempre".
2. **Política de sessão do Google Workspace** forçando reautenticação. Admin →
   Segurança → Controle de sessão do Google Cloud. Se estiver em 1 dia, é
   literalmente isso que te faz logar todo dia. Ajuste para *Nunca expira*.
3. **Mais de 50 refresh tokens ativos** pro mesmo par app/usuário — o Google revoga
   os mais antigos em silêncio. Acontece com quem roda `clasp login` repetidamente,
   o que vira um ciclo vicioso.

`./bin/clasp-doctor.sh --refresh` testa a renovação de verdade e diz em qual caso
você está.

---

## Voltar atrás

O `install.sh` salva `~/.claude/settings.json.bak.<timestamp>` antes de mexer.

```bash
cp ~/.claude/settings.json.bak.<timestamp> ~/.claude/settings.json
```

Pra desligar só o auto mode numa sessão, `Shift+Tab` cicla os modos. Pra revisar as
regras ativas, `/permissions` dentro do Claude Code.
