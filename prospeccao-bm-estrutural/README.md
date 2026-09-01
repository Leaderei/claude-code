# Base de prospecção — BM Estrutural (Louveira/SP)

Gera a lista de CNPJs de engenharias, construtoras e escritórios de arquitetura
na macro-região de Louveira a partir dos **Dados Abertos do CNPJ** da Receita
Federal. Fonte oficial, gratuita, atualizada mensalmente.

## Rodar

```bash
pip install -r requirements.txt
python gerar_base.py
```

Saída: `saida/base_bm_estrutural_AAAA-MM.csv` (UTF-8 com BOM — abre direto no
Excel e importa no Pipedrive sem ajuste).

Tempo: ~1h30 a ~3h, quase tudo download. Pico de disco ~1,5 GB.
Interrompeu? Rode de novo — os downloads são retomados de onde pararam.

### Opções

| Comando | Efeito |
|---|---|
| `python gerar_base.py` | competência mais recente publicada |
| `python gerar_base.py --mes 2026-08` | força uma competência |
| `python gerar_base.py --manter-zips` | não apaga os zips — permite re-rodar filtros offline em segundos |

**Dica:** na primeira execução use `--manter-zips`. Reajustar CNAE ou raio depois
custa 2 minutos em vez de baixar 6 GB de novo. Precisa de ~7 GB livres nesse modo.

## Por que baixa 6 GB para umas poucas cidades

O dump da Receita não é indexado por município: os estabelecimentos vêm
distribuídos aleatoriamente em 10 arquivos. Não existe API pública e gratuita
que busque por CNAE + cidade. O script contorna isso baixando um arquivo por
vez, filtrando em streaming e apagando antes do próximo — por isso o pico de
disco é baixo mesmo com 50 GB de CSV passando pelo processo.

## Ajustar o recorte

Tudo em `config.py`. Não mexa em `gerar_base.py`.

- **`ANEL_MAXIMO`** — comece em `1` (piloto, ~400-700 empresas), suba para `2`
  quando validar. Anel 1 sozinho não sustenta 12 meses de prospecção.
- **`CNAES`** / **`SOMENTE_NUCLEO`** — `True` usa só os 4 CNAEs núcleo.
  Mude para `False` para incluir a periferia (desenho técnico, alvenaria,
  incorporação) — valide em amostra antes de mandar para o SDR.
- **`CAPITAL_SOCIAL_MAX`** — o filtro mais importante. R$ 5M separa a engenharia
  de casas da incorporadora de prédio. É o que executa, na prática, a decisão
  de não prospectar grande construtora.

## Colunas da saída

Vêm preenchidas da Receita:

`cnpj` · `razao_social` · `nome_fantasia` · `segmento` · `prioridade` · `score` ·
`anel` · `municipio` · `bairro` · `endereco` · `cep` · `telefone_1` ·
`telefone_2` · `email` · `dominio` · `site` · `capital_social` · `porte` ·
`matriz` · `cnae_principal`

Vêm vazias, para as etapas seguintes:

`instagram` · `responsavel` · `tipologia_obra` · `status_sdr` · `obs`

### `site` e `dominio`

A Receita **não tem campo de site** — mas tem e-mail. O script extrai o domínio
quando ele não é genérico (gmail, hotmail, uol...). Isso entrega uma parte dos
sites de graça e com precisão alta. O resto vem do enriquecimento externo
(próxima etapa).

### `score` e `prioridade`

Score 0-100 com o que a Receita entrega: anel, CNAE, capital social, presença de
telefone/e-mail/domínio e idade da empresa. `A` ≥ 60 · `B` 40-59 · `C` < 40.

É um score **preliminar**. O sinal que realmente separa lead bom de ruído é a
tipologia de obra (casa × prédio), e essa só sai do scraping do site — coluna
`tipologia_obra`, ainda vazia.

## Próximas etapas

1. **Calibrar o ICP com a lista do Ricardo.** Rodar os CNPJs dos clientes atuais
   contra a base e extrair o perfil real: CNAE, capital, cidade, porte. É isso
   que valida (ou derruba) os filtros do `config.py`. **Faça antes de gerar a
   base definitiva** — sem isso o recorte é achismo.
2. **Enriquecer o site do resto.** Google Places API (Text Search) com
   `razão social + município`. Ordem de grandeza: ~US$32/1.000 buscas.
3. **Scraping.** Extrair contato, responsável técnico e — o que importa —
   tipologia do portfólio.
4. **Importar no Pipedrive** e distribuir por anel: anel 1 para vendedor externo,
   anel 2 para SDR interno.

## Validação

O pipeline foi testado contra fixtures no layout exato da Receita, cobrindo 15
casos: filtro de UF, situação cadastral, CNAE principal e secundário, idade
mínima, MEI, capital fora da faixa, capital zero, natureza jurídica excluída,
e-mail genérico, ausência de telefone e deduplicação matriz/filial.
