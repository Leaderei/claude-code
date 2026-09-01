# Base de prospecção — BM Estrutural (Louveira/SP)

Gera a lista de CNPJs de engenharias, construtoras e escritórios de arquitetura
na macro-região de Louveira a partir dos **Dados Abertos do CNPJ** da Receita
Federal. Fonte oficial, gratuita, atualizada mensalmente.

## Rodar — caminho rápido

**Windows:** clique duas vezes em `rodar.bat`
**Mac / Linux:** `./rodar.sh`

Faz tudo: instala dependências, baixa e filtra a Receita, e monta a planilha
formatada. No fim é só arrastar o `.xlsx` para o Google Drive.

## Rodar — passo a passo

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

## Calibrar o ICP com os clientes reais — faça isto primeiro

Antes de gerar a base definitiva, descubra o perfil de quem **já compra**. Sem
isso o recorte do `config.py` é achismo com aparência de dado.

```bash
python gerar_base.py --indice-amplo          # uma vez, gera o índice regional
python calibrar_icp.py clientes_ricardo.xlsx
```

`--indice-amplo` produz `saida/indice_regional_AAAA-MM.csv`: **todos** os
estabelecimentos ativos da região, sem filtro de CNAE nem de capital, incluindo
o anel 3. O filtro amplo é proposital — só assim dá para ver se os clientes
atuais caem *fora* do recorte.

### O que o script responde

1. **Qual o perfil real** — distribuição de CNAE, município, anel, porte, capital
   social (percentis) e idade das empresas que já compram.
2. **Quantos clientes atuais o filtro mataria** — e, se a planilha trouxer valor
   de venda, **quanto faturamento** isso representa. Este é o número que decide
   se o `config.py` está certo.
3. **Quais CNAEs de clientes reais estão ausentes** do `config.py`, ranqueados
   por volume e faturamento.

### A planilha pode vir suja

O script detecta as colunas sozinho (`CNPJ`, `Cliente`, `Cidade`, `Valor`),
acha o cabeçalho mesmo com linhas de título acima, aceita CNPJ formatado ou não,
lê `R$ 45.000,00` e `45000.00`, casa por nome quando não houver CNPJ, e soma o
faturamento de clientes recorrentes num único CNPJ.

Casamentos por aproximação vêm marcados com a coluna `confianca` —
**confira antes de decidir com base neles.** Ajuste o rigor com `--corte 0.80`.

Saídas: `saida/icp_clientes_casados.csv` e `saida/icp_nao_encontrados.csv`
(normalmente pessoa física, obra particular ou empresa fora da região).

## Levar para o Google Sheets

```bash
python montar_sheets.py saida/base_bm_estrutural_2026-08.csv
```

Gera `saida/base_bm_estrutural.xlsx` já formatado. Arraste para o Google Drive e
abra como Google Sheets — dropdowns, filtros e formatação são preservados na
conversão.

A planilha tem duas abas:

- **Base** — cabeçalho fixo, filtro automático, colunas dimensionadas, prioridade
  A destacada em laranja e listas suspensas em `status_sdr`, `tipologia_obra` e
  `responsavel`.
- **Como usar** — briefing para a equipe de SDR: como a fila funciona, divisão
  por anel, o que preencher em `tipologia_obra` e a regra de LGPD.

Os status seguem a cadência multicanal de 13 dias (`D1 LinkedIn` → `D13 Breakup`).
A referência de 6 a 12 tentativas por lead está na aba de instruções — abaixo de 6
a conversão cai de forma relevante, e é o erro mais comum de SDR sem processo.

Rodar `python montar_sheets.py` sem argumento gera a planilha vazia, só com a
estrutura — útil para preparar o Sheets e dar acesso ao time antes da base existir.

As duas últimas colunas (`data_ultimo_contato`, `proximo_passo`) não vêm do CSV:
existem só para uso manual da SDR, e por isso ficam depois de todas as colunas
importadas.

## Próximas etapas

1. **Enriquecer o site do resto.** Google Places API (Text Search) com
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

O `calibrar_icp.py` foi testado com uma planilha propositalmente suja — cabeçalho
na terceira linha, CNPJ ora formatado ora não, cliente recorrente em duas linhas,
pessoa física no meio e clientes fora de cada um dos filtros.
