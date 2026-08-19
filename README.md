# claude-code

Configuração para deixar o Claude Code mais autônomo — menos prompts de permissão
e fim do `clasp login` diário.

## Instalação

**Windows (PowerShell):**

```powershell
git clone https://github.com/Leaderei/claude-code
cd claude-code
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

**Linux / Mac:**

```bash
git clone https://github.com/Leaderei/claude-code && cd claude-code
./install.sh --dry-run   # confere o que vai mudar
./install.sh             # aplica
```

Os scripts em `bin/*.sh` são só para Linux/Mac. No Windows, use
`python "$env:USERPROFILE\.claude\clasp\clasp-refresh.py" --status` para
inspecionar o token do clasp.

Faz backup do seu `~/.claude/settings.json` antes de qualquer coisa, e é
idempotente — rodar duas vezes não duplica nada.

> **Rode você mesmo.** O classificador do auto mode bloqueia o agente quando ele
> tenta alterar as próprias permissões. É proposital, e é uma boa proteção.

## Diagnóstico

```bash
./bin/claude-doctor.sh          # por que ainda estou aprovando tudo?
./bin/clasp-doctor.sh           # estado da credencial do clasp
./bin/clasp-doctor.sh --refresh # testa a renovação de verdade
```

## Conteúdo

| Arquivo | O quê |
|---|---|
| `install.sh` | Funde as permissões, instala os scripts e o hook `SessionStart` |
| `config/permissions.json` | `defaultMode: auto` + ~70 regras allow / 5 ask / 13 deny |
| `bin/clasp-refresh.py` | Renova o token do clasp e **grava de volta** — o que o clasp não faz |
| `bin/clasp-doctor.sh` | Diagnostica a credencial do clasp |
| `bin/claude-doctor.sh` | Acha o que está desligando o auto mode |
| `docs/AUTONOMIA.md` | Explicação completa, causas e como voltar atrás |

## Resumo das duas causas

**Permissões.** O auto mode já é o padrão em Pro/Max/Team. A pegadinha:
`"defaultMode": "auto"` só vale em `~/.claude/settings.json` — colocado no
`.claude/settings.json` do projeto, ele é ignorado *e* faz o Claude Code parar de
ler o `defaultMode` do seu arquivo global.

**clasp.** O `~/.clasprc.json` não é regravado depois que o clasp renova o token em
memória, então o arquivo envelhece até vencer. O `refresh_token` continua válido —
só não é usado. O `clasp-refresh.py` usa e persiste.

Detalhes em [`docs/AUTONOMIA.md`](docs/AUTONOMIA.md).
