# qdedu — Raspagem de Secretarias Municipais de Educação (Querido Diário)

Sistema de raspagem para coletar inteligência e contatos de prospecção das
**Secretarias Municipais de Educação** a partir da API pública do
[Querido Diário](https://queridodiario.ok.org.br) (busca full-text em diários
oficiais municipais).

> ⚠️ **Leia antes:** o Querido Diário é um índice de **texto de diários
> oficiais**, não um diretório de contatos. E-mails e telefones são
> **extraídos do texto** das publicações e podem estar desatualizados ou
> ausentes. Para prospecção confiável, use o módulo de enriquecimento
> (`qdedu/enrich.py`) com fontes complementares (site da prefeitura, portal da
> transparência). Veja [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## O que ele faz

1. **Enumera** todos os municípios de uma UF via API do IBGE
   (o código IBGE de 7 dígitos = `territory_id` no Querido Diário).
2. **Busca** no Querido Diário os diários que mencionam a secretaria de
   educação de cada município (`territory_ids` + `querystring`).
3. **Baixa** o texto bruto (`txt_url`) e **extrai** e-mails, telefones e
   prováveis nomes/cargos (secretário(a) de educação) via regex.
4. **Persiste** tudo em **SQLite** (resumível/idempotente) e **exporta CSV**
   pronto para revisão antes de importar no CRM.

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
# 1. Listar/cachear municípios da UF (ex.: São Paulo)
qdedu cities --uf SP

# 2. Raspar a UF inteira (com janela de datas e limite opcional p/ teste)
qdedu scrape --uf SP --since 2023-01-01 --limit 20

# 3. Exportar contatos para CSV
qdedu export --uf SP --out data/sp_contatos.csv            # consolidado (padrão)
qdedu export --uf SP --out data/sp_long.csv --format long  # 1 linha por contato
```

Há dois formatos de CSV:

- **`wide`** (padrão) — **uma linha por município**, pronto para prospecção:
  `municipio, uf, codigo_ibge, melhor_email, melhor_telefone, secretario,
  todos_emails, todos_telefones, fontes, url_fonte`. Prioriza contatos do
  **site oficial** e marcados como **educação**.
- **`long`** — **uma linha por contato** (auditoria/revisão), com o trecho de
  contexto do diário/site de onde veio cada dado.

### Enriquecimento pelo site da prefeitura

Para contatos mais atuais que os do texto dos diários, ative o enricher que
busca e-mail/telefone da Secretaria de Educação no **site oficial** do
município (descobre o domínio via `publication_urls` do Querido Diário e/ou um
mapa curado):

```bash
# usa o domínio publicado no Querido Diário
qdedu scrape --uf SP --enrich site

# (recomendado) forneça um mapa curado id_ibge->url para maior precisão
qdedu scrape --uf SP --enrich site --domain-map dominios_sp.csv
```

`--domain-map` aceita JSON (`{"3550308": "https://prefeitura.sp.gov.br"}`) ou
CSV (`3550308,https://prefeitura.sp.gov.br`). Contatos do site são gravados com
`fonte = site_prefeitura` (vs. `querido_diario`), permitindo priorizá-los na
prospecção.

Ou sem instalar, via módulo:

```bash
python -m qdedu.cli scrape --uf SP --since 2023-01-01 --limit 20
```

### Variáveis de ambiente (`.env`)

Copie `.env.example` para `.env` e ajuste se necessário:

| Variável        | Padrão                                      | Descrição                        |
|-----------------|---------------------------------------------|----------------------------------|
| `QD_API_BASE`   | `https://api.queridodiario.ok.org.br`       | Base da API do Querido Diário    |
| `IBGE_API_BASE` | `https://servicodados.ibge.gov.br/api/v1`   | Base da API de localidades IBGE  |
| `QD_DB_PATH`    | `data/qdedu.sqlite`                         | Caminho do banco SQLite          |
| `QD_RATE_RPS`   | `2.0`                                        | Requisições/segundo (rate limit) |
| `QD_USER_AGENT` | `qdedu/0.1 (+prospeccao)`                    | User-Agent das requisições       |

## Acesso de rede

A raspagem depende de acesso de saída a `api.queridodiario.ok.org.br` e
`servicodados.ibge.gov.br`. Em ambientes com política de egresso restrita
(ex.: Claude Code on the web) esses hosts podem estar bloqueados — rode em
um ambiente com acesso liberado.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

Os testes de extração e parsing rodam **offline** (sem rede).
