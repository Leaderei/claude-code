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
territory_id         ──►  QEdu /v1/escolas   ──►  nº escolas + matrículas (rede municipal)
tudo unido por IBGE  ──►  dedup + ranking    ──►  CSV / JSON prontos p/ CRM
```

O **código IBGE de 7 dígitos** é a chave que une as duas fontes: é o
`territory_id` no Querido Diário e o `municipio_id` no QEdu.

---

## ⚠️ Aviso importante sobre este ambiente

Os hosts `api.queridodiario.ok.org.br` **e** `api.qedu.org.br` estão
**bloqueados pela política de rede do ambiente remoto do Claude Code** (o proxy
de egress responde `403` no CONNECT). Por isso o código **não foi executado
contra as APIs reais aqui** — apenas os testes offline (extração e cliente
QEdu com sessão simulada) e testes de ponta a ponta com clientes falsos.

Para rodar de verdade, execute **na sua máquina** (ou em um ambiente cuja
política de rede libere `*.queridodiario.ok.org.br` e `*.qedu.org.br`).

> **Sobre a fonte INEP:** a API `api.dadosabertosinep.org` (projeto comunitário
> de ~2013) foi **descontinuada** — o domínio nem resolve mais no DNS. Por isso
> os dados do INEP (escolas/matrículas) vêm do **QEdu** (`api.qedu.org.br`),
> plataforma da Iede que republica o Censo Escolar e está ativa. O contrato do
> QEdu está centralizado em constantes no topo de `qedu.py`; confirme os nomes
> de parâmetros/campos contra a doc oficial e ajuste ali se necessário.

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

# Com enriquecimento do Censo Escolar (nº de escolas municipais e matrículas)
export QEDU_API_TOKEN="seu_token_do_qedu"
python -m raspador_educacao --municipio "Sorocaba/SP" --qedu-ano 2024
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
| `--qedu-token TOKEN` | Token da API do QEdu (ou variável `QEDU_API_TOKEN`). Habilita escolas/matrículas. |
| `--qedu-ano AAAA` | Ano do Censo Escolar no QEdu (padrão: mais recente). |
| `-v` | Log detalhado. |

## Saídas geradas

No diretório de saída são criados três arquivos:

- **`prospeccao.csv`** — uma linha por município, com o melhor e-mail/telefone e
  alternativos, **+ nº de escolas municipais e matrículas** (QEdu). Colunas
  alinhadas a CRMs (ex.: HubSpot: *empresa, email, phone*).
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
  qedu.py       Cliente da API do QEdu (Censo Escolar: escolas + matrículas)
  extracao.py   Regex + janelas de contexto + ranking de contatos
  pipeline.py   Orquestra: resolve município → diários + QEdu → extrai
  exportar.py   Exportadores JSON / CSV
  cli.py        Interface de linha de comando
tests/
  test_extracao.py
  test_qedu.py
exemplos/
  municipios.txt
```

## Próximos passos sugeridos

- **Cruzar com o site da prefeitura**: confirmar o contato atual da secretaria
  no portal oficial / portal da transparência (próxima etapa combinada).
- **Importar direto no HubSpot**: o `prospeccao.csv` já sai com colunas de CRM;
  dá para automatizar a criação de *companies*/*contacts* via API do HubSpot.
- **Agendamento**: rodar periodicamente para captar diários novos.
