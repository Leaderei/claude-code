# Educa Open — Slide executivo de performance comercial

Slide único (16:9) para abrir a apresentação de performance da equipe de vendas.
Padrão visual Leaderei: fundo preto com bloom laranja, Manrope, filetes de 1px.

## Como regerar

```bash
npm install pptxgenjs
node slide.js          # gera educaopen-performance-comercial.pptx
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

| Canal | Entradas | Diag. agendado | Ganhos | Taxa de ganho |
|---|---|---|---|---|
| Parcerias / Indicações | 30 | 25 | 7 | 23% |
| Eventos | 38 | 25 | 1 | 3% |
| ABM* | 24 | 2 | 2 | 8% |
| Dripify | 175 | 7 | 0 | 0% |
| Webinar | 510 | 15 | 1 | 0,2% |

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
- **Topo de funil** = reuniões de diagnóstico criadas no mês (atividade).
  **Funil por canal** = negócios por etapa, acumulado do projeto. São recortes
  diferentes e não devem ser somados entre si.
