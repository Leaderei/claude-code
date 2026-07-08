# Raspador de contatos — Secretarias Municipais de Educação

Sistema de raspagem que usa a **API pública do [Querido Diário](https://queridodiario.ok.org.br/)**
(Open Knowledge Brasil) para localizar, nos Diários Oficiais municipais, menções à
**Secretaria de Educação** e extrair **e-mails e telefones** para prospecção comercial.

A API indexa o texto completo dos diários oficiais de centenas de municípios
brasileiros. O fluxo é:

```
município (nome/UF)  ──►  GET /cities        ──►  código IBGE (territory_id)
territory_id + texto ──►  GET /gazettes      ──►  diários que citam a educação
cada diário (txt_url)──►  download + regex   ──►  e-mails e telefones
todos os contatos    ──►  dedup + ranking    ──►  CSV / JSON prontos p/ CRM
```

---

## ⚠️ Aviso importante sobre este ambiente

O host `api.queridodiario.ok.org.br` está **bloqueado pela política de rede do
ambiente remoto do Claude Code** (o proxy de egress responde `403` no CONNECT).
Por isso o código **não foi executado contra a API real aqui** — apenas os testes
de extração (que rodam offline) e um teste de ponta a ponta com cliente simulado.

Para rodar de verdade, execute **na sua máquina** (ou em um ambiente cuja
política de rede libere o domínio `*.queridodiario.ok.org.br`).

---

## Instalação

```bash
cd raspagem-educacao
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Requer Python 3.9+ e a biblioteca `requests`.

## Uso

```bash
# Um município, últimos meses
python -m raspador_educacao --municipio "Sorocaba/SP" --desde 2025-01-01

# Vários municípios de uma lista
python -m raspador_educacao --lista exemplos/municipios.txt --saida resultados/

# Por código IBGE, ampliando o alcance (extrai de todo o diário)
python -m raspador_educacao --municipio 3550308 --sem-filtro-contexto
```

### Principais opções

| Opção | Descrição |
|-------|-----------|
| `--municipio` | `"Nome/UF"`, `"Nome"` ou código IBGE de 7 dígitos. Pode repetir. |
| `--lista ARQ` | Arquivo com um município por linha. |
| `--desde AAAA-MM-DD` | Data inicial (`published_since`). |
| `--ate AAAA-MM-DD` | Data final (`published_until`). |
| `--max-diarios N` | Máximo de diários analisados por município (padrão 60). |
| `--sem-filtro-contexto` | Extrai contatos de todo o diário, não só perto de "educação". Mais recall, menos precisão. |
| `--saida DIR` | Diretório de saída (padrão `./resultados`). |
| `-v` | Log detalhado. |

## Saídas geradas

No diretório de saída são criados três arquivos:

- **`prospeccao.csv`** — uma linha por município, com o melhor e-mail/telefone e
  alternativos. Colunas alinhadas a CRMs (ex.: HubSpot: *empresa, email, phone*).
- **`contatos.csv`** — uma linha por contato, com pontuação e trecho de evidência.
- **`contatos.json`** — dados completos, incluindo todas as evidências (trecho +
  URL + data do diário) de cada contato, para conferência manual.

Cada contato traz:
- `score` — relevância (proximidade da menção à Secretaria de Educação,
  quantas vezes apareceu, e bônus para domínios governamentais);
- `governamental` — se o e-mail é de domínio `.gov.br`/prefeitura;
- `evidencias` — de onde o dado foi extraído (fonte + data + trecho).

## Como funciona a extração (precisão)

1. Localiza no texto as **janelas de contexto** ao redor de termos como
   *"secretaria municipal de educação"*, *"SEMED"*, *"fundo municipal de educação"*.
2. A janela **para no cabeçalho de outra secretaria** (ex.: "Secretaria de Obras"),
   evitando capturar o contato da pasta errada.
3. Dentro dessas janelas, captura e-mails (regex) e telefones brasileiros
   (fixo e celular, com DDD, tolerando `+55`, `Tel:`, `Fone:` etc.).
4. Deduplica e ordena: **governamental → score → nº de ocorrências**.

## Limitações e boas práticas

- **Os diários não são um cadastro oficial de contatos.** Os e-mails/telefones
  vêm de editais, chamamentos e licitações. Trate-os como *leads a validar* —
  cada um vem com a evidência para conferência.
- Priorize e-mails de domínio **`.gov.br`** e telefones com **rótulo** próximo.
- A API é mantida por uma organização sem fins lucrativos: o cliente já aplica
  *rate limit* (~0,6 s entre requisições) e *retry* com backoff. Não paralelize
  agressivamente.
- Nem todo município tem diário indexado. Se um município retornar vazio,
  amplie o período ou tente `--sem-filtro-contexto`.

## Testes

```bash
python3 tests/test_extracao.py     # roda offline, sem rede
# ou, se tiver pytest:
pytest tests/
```

## Estrutura

```
raspador_educacao/
  api.py        Cliente da API do Querido Diário (retry, rate limit, paginação)
  extracao.py   Regex + janelas de contexto + ranking de contatos
  pipeline.py   Orquestra: resolve município → busca diários → extrai
  exportar.py   Exportadores JSON / CSV
  cli.py        Interface de linha de comando
tests/
  test_extracao.py
exemplos/
  municipios.txt
```

## Próximos passos sugeridos

- **Importar direto no HubSpot**: o `prospeccao.csv` já sai com colunas de CRM;
  dá para automatizar a criação de *companies*/*contacts* via API do HubSpot.
- **Enriquecimento cruzado**: complementar com o portal da transparência /
  site oficial da prefeitura para confirmar o contato atual da secretaria.
- **Agendamento**: rodar periodicamente para captar diários novos.
