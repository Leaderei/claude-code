# Viva Noz — projeto Mercado Livre

Marca de castanhas em lançamento no Mercado Livre. Posicionamento: **honestidade
premium** — blend próprio, proporção declarada e cumprida, envase em lote pequeno
com data carimbada. O buraco de mercado é documentado: 335 clientes dos líderes
reclamando por escrito que compraram castanha e receberam amendoim.

**Prazo de lançamento: 17/09/2026.**

## Onde está cada coisa

| O quê | Onde |
|---|---|
| Guia de marca & estratégia (16/08) | Artifact `bc9cf735-9230-4149-b21d-f53f4a1ab80f` |
| Kit de lançamento — anúncios, rótulo, fotos (19/08) | Artifact `68493170-04ac-4345-ab3e-528f127807bf` · fonte em `kit-lancamento.html` |
| Planilha central (insumos, receitas, simulador ML) | Google Sheets `13aEV3mAtK1WtVzfabXCyL28_jrZkk0iTeJ0PpFj3S7o` |
| Pesquisa de mercado (4.067 anúncios, avaliações, top 100) | Google Sheets `Pesquisa de Mercado \| Viva Noz` |
| Monitor diário ML | Tarefa do Windows "VivaNoz Monitor ML", 9h · pasta `Viva Noz` na área de trabalho |
| Texto puro dos 4 anúncios | `anuncios-ml.txt` |

## SKUs de estreia

| SKU | Preço | Papel |
|---|---|---|
| Mix Premium 1 kg | R$ 144,90 | Ataque ao líder (Supremo Nuts a R$ 149,90) |
| Mix Premium 500 g | R$ 64,90 | Vitrine da marca no termo nº 1 de busca |
| Caju caramelizada c/ gergelim 500 g | R$ 49,90 | Demanda provada (King Nuts, +5.000 vendidos) |
| Drágea de caju c/ chocolate 70% 200 g | R$ 54,90 | Aposta de margem (só 14 concorrentes) |

Kit 2× Mix 500 g (R$ 129,90) fica para a Fase 2, retrabalhado como presente.

Blend: **30% caju · 20% amêndoa · 20% castanha-do-pará · 20% nozes · 10% macadâmia**.
Custo do blend R$ 72,33/kg.

## Bloqueios abertos (19/08/2026)

Nenhum deles estava mapeado no plano original. Todos travam a compra do adesivo,
que é irreversível em lote de 500.

1. **Lupa preta no carro-chefe.** O mix tem 9,2 g de gordura saturada por 100 g —
   o gatilho da RDC 429/2020 é 6 g. Só o enquadramento como alimento minimamente
   processado mantém a frente do pacote limpa. Precisa de parecer escrito do
   responsável técnico.
2. **"Sem amendoim" × "pode conter amendoim".** A RDC 26/2015 obriga declarar
   traços. Precisa da declaração de segregação de linha da Divina Castanha. O
   claim já foi ajustado para "sem amendoim **na composição**" em todo o material.
3. **GTIN.** Sem código GS1 o anúncio nasce fora do catálogo. O registro não sai
   no mesmo dia e o código precisa estar impresso no adesivo.
4. **Drágea entrando no verão.** Estreia em 17/09 põe o chocolate em trânsito de
   outubro a dezembro. Decidir entre segurar até março, embalagem térmica, ou
   política de reembolso escrita no anúncio.

## Cálculo nutricional do mix

Calculado a partir da receita da planilha, com composição de referência das cinco
castanhas e o método energético da ANVISA (4/4/9/2). Por 100 g: 657 kcal,
20,6 g de carboidratos, 3,9 g de açúcares totais, 0 g adicionados, 15,5 g de
proteínas, 58,5 g de gorduras totais, 9,2 g de saturadas, 6,9 g de fibra,
7 mg de sódio.

Vira definitivo quando a Divina mandar as fichas dos insumos — a diferença
costuma ficar entre 3% e 8%, o bastante para mudar arredondamento de linha.

## Regras do ML que a redação obedece

- Título: **60 caracteres**, máximo. Os quatro títulos foram medidos.
- Descrição: texto puro. Sem HTML, sem link, sem dado de contato.
- Abaixo de R$ 79: custo fixo de R$ 6,75/venda e o comprador paga o frete.
- A partir de R$ 79: frete grátis obrigatório, tarifa por conta do vendedor.
- Taxa ML clássico 12% · Simples Nacional 4% · Ads 15% no lançamento, ~8% no cruzeiro.
