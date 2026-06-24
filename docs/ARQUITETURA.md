# Arquitetura — qdedu

## Visão geral do fluxo

```
        IBGE /localidades                 Querido Diário /gazettes
              │                                    │
              ▼                                    ▼
   ┌────────────────────┐   territory_ids  ┌──────────────────┐
   │ enumerar municípios │ ───────────────▶ │ buscar diários de │
   │   da UF (cidades)   │                  │  educação (texto) │
   └────────────────────┘                  └──────────────────┘
              │                                    │ txt_url
              │                                    ▼
              │                          ┌──────────────────┐
              │                          │  extrair contatos │  regex:
              │                          │  (email/tel/sec.) │  e-mail, telefone BR,
              │                          └──────────────────┘  nome do(a) secretário(a)
              │                                    │
              ▼                                    ▼
        ┌──────────────────────────────────────────────┐
        │              SQLite (resumível)                │
        │  municipalities · gazettes · contacts · progress
        └──────────────────────────────────────────────┘
                              │
                  enrich.py (pluggável)        export CSV
                  site prefeitura, etc.        p/ revisão → CRM
```

## Por que IBGE para enumerar municípios

A API do Querido Diário busca municípios **por nome** (`/cities?city_name=`),
não por UF. A API de localidades do IBGE lista todos os municípios de uma UF e
seu **código de 7 dígitos**, que é exatamente o `territory_id` usado pelo
Querido Diário. Por isso enumeramos via IBGE e cacheamos em `municipalities`.

> Nem todo município é coberto pelo Querido Diário (só os que têm diário
> raspado). Municípios sem cobertura simplesmente retornam zero diários.

## Mapa de campos da API

`GET /gazettes` → cada item é normalizado em `qdedu.api.Gazette`:

| API                         | Gazette        | Uso                          |
|-----------------------------|----------------|------------------------------|
| `territory_id`              | `territory_id` | join com municípios          |
| `territory_name`,`state_code` | idem         | rótulo                       |
| `date`,`edition`            | idem           | proveniência                 |
| `txt_url` / `file_raw_txt`  | `txt_url`      | **texto completo** p/ extração |
| `excerpts`                  | `excerpts`     | fallback quando não há txt   |

O parser é tolerante a variações de nome de campo entre versões da API.

## Extração de contatos (`extract.py`)

- **E-mails:** regex padrão + filtro de ruído (imagens `@2x.png`, `example.`).
- **Telefones:** regex para formatos BR (fixo, móvel 9 dígitos, 0800, DDI +55),
  normalizados para apenas dígitos e deduplicados.
- **Secretário(a):** heurística por proximidade entre um nome próprio e o cargo
  "Secretári[oa] (Municipal) de Educação", removendo verbos de portaria
  ("Nomeia", "Designa"…) do início do nome.

Cada contato guarda um **trecho de contexto** do diário para revisão manual —
essencial, porque texto de diário é ruidoso e os dados podem estar
desatualizados.

## Limitação central e enriquecimento

O Querido Diário **não é um diretório de contatos**. E-mails/telefones extraídos
do texto podem estar desatualizados ou ausentes. Por isso há a interface
`Enricher` (`enrich.py`), com duas implementações:

- **`NullEnricher`** — padrão, no-op.
- **`SitePrefeituraEnricher`** — busca contatos da Secretaria de Educação no
  **site oficial** do município. Fluxo:
  1. **Descobre o domínio**: `domain_map[territory_id]` (mapa curado) →, senão,
     `publication_urls` de `/cities/{id}` do Querido Diário, descartando
     plataformas de terceiros (`diariomunicipal`, `imprensaoficial`, etc.).
  2. **Baixa** caminhos prováveis (`/contato`, `/secretaria-de-educacao`,
     `/educacao`…), limitado por `max_pages`.
  3. **Extrai** e-mails/telefones de hrefs `mailto:`/`tel:` (mais confiáveis) e
     do texto (HTML convertido por `html.parser`, ignorando `<script>/<style>`).
  4. **Marca** como `título = "educação"` quando o e-mail/página é claramente da
     pasta de educação, e grava com `source = "site_prefeitura"`.

Ative com `qdedu scrape --enrich site [--domain-map arquivo]`. Contatos do site
e dos diários convivem na mesma tabela, distinguíveis pela coluna `fonte` —
priorize `site_prefeitura` na prospecção.

> **Por que `--domain-map` é recomendado:** `publication_urls` às vezes aponta
> para a plataforma de publicação, não para o site institucional. Um mapa curado
> (id IBGE → URL oficial) eleva muito a precisão. Pode ser construído uma vez e
> versionado.

## Idempotência e retomada

- `contacts` tem `UNIQUE(territory_id, kind, value)` → reexecutar não duplica.
- `progress` marca cada município como `done`/`error`; `scrape` pula os `done`
  (use `--no-resume` para reprocessar). Isso torna a raspagem de uma UF inteira
  segura para interromper e continuar.

## Rate limiting e robustez

`HttpClient` aplica rate limit (`QD_RATE_RPS`, padrão 2 req/s) e retry com
backoff exponencial (1s→2s→4s→8s) em erros transientes (429/5xx/rede). Um erro
em uma cidade é registrado e **não derruba** a varredura da UF.

## Considerações legais / de uso

- Dados de diários oficiais são **públicos**. Ainda assim, para prospecção
  (LGPD), prefira contatos **institucionais** (e-mail/telefone da secretaria),
  não dados pessoais, e respeite opt-out.
- Respeite os termos de uso da API do Querido Diário e mantenha o rate limit
  conservador.
