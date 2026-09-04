# Educa Open — Apresentação de performance comercial

Deck de 13 slides (16:9) para a reunião de performance do time de vendas.
Padrão visual Leaderei: fundo preto com bloom laranja, Manrope, filetes de 1px,
um layout diferente por slide.

## Roteiro

| # | Slide | Papel |
|---|---|---|
| 1 | Capa | Abertura |
| 2 | Panorama do período | Os 4 números e as 4 leituras do período |
| 3 | Topo de funil x meta | Realizado x meta mês a mês |
| 4 | Resultado financeiro | Ganhos, valor e ticket médio por mês |
| 5 | Saúde do funil | As 9 etapas com conversão e perda absoluta |
| 6 | Comparação com o padrão Leaderei | No-show, reunião→proposta e fechamento |
| 7 | Desempenho por canal | Quem agenda x quem fecha |
| 8 | Diagnóstico dos canais frios | Webinar, Dripify e ABM |
| 9 | Alocação de esforço | Plano de agosto x de onde vieram os ganhos |
| 10 | Consistência do plano de metas | 9,6% realizado x 18% assumido |
| 11 | Setembro | Ritmo diário e distribuição semanal |
| 12 | Plano de ação | Seis ações nas próximas 4 semanas |
| 13 | Fechamento | Três decisões |

Todos os slides têm notas do apresentador.

## Como regerar

```bash
npm install pptxgenjs
node deck.js          # gera educaopen-performance-comercial.pptx
```

A fonte **Manrope** precisa estar instalada na máquina que abre o arquivo.
No Windows ela não vem por padrão — apresentar da máquina com a fonte instalada
ou subir no Google Slides (Manrope é nativa lá).

## Dados usados

Período: jun–set/2026. Fonte: funil da Educa Open no Pipedrive (prints do
deck original) + planilha de metas do 2º semestre. Setembro parcial até 04/09.

### Topo de funil — reuniões de diagnóstico criadas no mês

| Mês | Realizado | Meta | Atingimento |
|---|---|---|---|
| jun | 4 | — | — |
| jul | 22 | 39 | 56% |
| ago | 36 | 28 | 129% |
| set (até 04/09) | 4 | 44 | ritmo de 48% |

### Negócios ganhos

| Mês | Qtd | Valor |
|---|---|---|
| jun | 4 | R$ 205 mil |
| jul | 2 | R$ 9,5 mil |
| ago | 5 | R$ 249 mil |
| set (parcial) | 1 | R$ 35 mil |
| **Total** | **12** | **R$ 498,5 mil** |

### Funil geral (acumulado, Pipedrive)

Pesquisa 915 → Em cadência 815 (89%) → Engajado 247 (30%) → Diagnóstico
agendado 125 (51%) → Diagnóstico realizado 114 (91%) → Validação externa
103 (90%) → Proposta enviada 62 (60%) → Contrato enviado 20 (32%) → Ganho 12 (60%).

### Funil por canal (acumulado)

| Canal | Entradas | Cadência | Engajado | Diag. agend. | Diag. real. | Validação | Proposta | Contrato | Ganho |
|---|---|---|---|---|---|---|---|---|---|
| Parcerias / Indicações | 30 | 30 | 29 | 25 | 25 | 23 | 14 | 8 | 7 |
| Eventos | 38 | 36 | 30 | 25 | 23 | 21 | 13 | 3 | 1 |
| ABM* | 24 | 24 | 4 | 2 | 2 | 2 | 2 | 2 | 2 |
| Dripify | 175 | 103 | 95 | 7 | 7 | 7 | 3 | 2 | 0 |
| Webinar | 510 | 486 | 31 | 15 | 9 | 8 | 4 | 1 | 1 |

Derivadas usadas no deck:

| Canal | Vira reunião (agend. ÷ entradas) | No-show | Fecha (ganhos ÷ propostas) |
|---|---|---|---|
| Parcerias / Indicações | 83% | 0% | 50% |
| Eventos | 66% | 8% | 8% |
| ABM | 8% | 0% | 100% |
| Dripify | 4% | 0% | 0% |
| Webinar | 3% | 40% | 25% |

A soma dos canais não fecha com o funil geral: 41% dos negócios de meio de funil
estão sem canal de origem preenchido no CRM (51 dos 125 diagnósticos agendados,
26 das 62 propostas, 1 dos 12 ganhos).

### Plano semanal de agosto (planilha de metas por SDR)

| Origem | S1 | S2 | S3 | S4 | Total | % da meta |
|---|---|---|---|---|---|---|
| ABM | 3 | 3 | 3 | 3 | 12 | 43% |
| Dripify | 2 | 2 | 2 | 2 | 8 | 29% |
| Parceiros / Indicações | 2 | 2 | 2 | 2 | 8 | 29% |
| **Meta de agendamentos** | 7 | 7 | 7 | 7 | **28** | |

Realizado registrado na planilha: 6 na S1. Total do mês pelo Pipedrive: 36.

### Comparação com os benchmarks Leaderei

| Métrica | Educa Open | Padrão Leaderei | Situação |
|---|---|---|---|
| No-show sobre agendados | 9% (114 de 125) | até 10–20% | acima do padrão |
| Reunião → proposta | 54% (62 de 114) | 50–70% | dentro do padrão |
| Fechamento sobre propostas | 19% (12 de 62) | 25–40% | abaixo do padrão |

\* Entradas de ABM sinalizadas como inconsistentes na origem (o deck original
já trazia a ressalva no título do slide).

### Metas do 2º semestre (planilha)

| Mês | Nota | Meta clientes | Valor contratado | Meta agendamentos |
|---|---|---|---|---|
| Julho | 7 | 9,31 | R$ 465.390,63 | 39 |
| Agosto | 3 | 3,99 | R$ 199.453,13 | 28 |
| Setembro | 5 | 6,65 | R$ 332.421,88 | 44 |
| Outubro | 7 | 9,31 | R$ 465.390,63 | 56 |
| Novembro | 7 | 9,31 | R$ 465.390,63 | 56 |
| Dezembro | 3 | 3,99 | R$ 199.453,13 | 11 |
| **Total** | **32** | **42,55** | **R$ 2.127.500,00** | **234** |

Referência de 1,33 cliente por ponto; ticket implícito de ~R$ 49.988 por cliente.

## Premissas declaradas no slide

- **Meta implícita de conversão = 18%**: 42,55 clientes ÷ 234 agendamentos
  planejados (jul–dez). A conversão realizada é 12 ganhos ÷ 125 diagnósticos
  agendados = 9,6%.
  Ressalva: há 103 negócios em validação externa e 62 em proposta que ainda
  podem fechar e elevar a taxa realizada.
- **Setembro tem 21 dias úteis** (22 dias de semana menos o feriado de 07/09).
  Meta de 44 = 2,1 reuniões/dia útil. Ritmo dos 4 primeiros dias = 1,0/dia.
  Restam 40 agendamentos em 17 dias úteis = 2,4/dia útil.
- **Ticket médio realizado** = R$ 498,5 mil ÷ 12 = R$ 41,5 mil, contra R$ 50 mil
  implícitos no plano. Julho puxa a média para baixo (dois negócios de R$ 4,8 mil).
- **R$ 25 mil por ponto percentual de fechamento** = 62 propostas × 1% × ticket
  médio de R$ 41,5 mil.
- **Topo de funil** = reuniões de diagnóstico criadas no mês (atividade).
  **Funil por canal** = negócios por etapa, acumulado do projeto. São recortes
  diferentes e não devem ser somados entre si.
