# Base de Construtoras, Engenharias e Arquiteturas — Macro-região de Louveira/SP

Arquivo: `base_construtoras_engenharias_arquiteturas_macro_louveira.csv` (75 registros, 26 colunas)

## Recorte geográfico
Louveira como centro, com anéis de distância rodoviária aproximada:
- **Eixo Louveira** (0–22 km): Louveira, Vinhedo, Valinhos, Itupeva
- **Eixo Jundiaí** (18–35 km): Jundiaí, Jarinu, Cabreúva
- **Eixo Itatiba/Morungaba** (27–38 km)
- **RMC — Campinas** (30 km) e **RMC — Indaiatuba** (45 km)
- **Fora da macro-região**: players nacionais/regionais com operação declarada na área

## Critério de Prioridade_ICP
- **A** — sede a até 22 km de Louveira
- **B** — sede entre 23 e 45 km
- **C** — sede fora do raio, mas com atuação declarada na região (decisão fora da praça)

## Coluna Confianca_do_Dado
- **Alta** — site institucional ou perfil oficial da própria empresa
- **Média** — diretório empresarial, ranking setorial ou matéria de imprensa
- **Baixa** — fonte única com inconsistência detectada (ver Observacoes)

## Limitação conhecida
Esta base **não é um censo**. Os diretórios que contêm o universo completo por CNAE + município
(Econodata, Casa dos Dados, cnpj.biz, GuiaMais) estão bloqueados pelo proxy de rede desta sessão.
Para fechar o universo, cruzar com:
1. Receita Federal — CNAEs 41.10-7, 41.20-4, 42.xx, 43.xx (construção) e 71.11-1 (arquitetura),
   filtrando por município e situação cadastral ativa
2. SindusCon-SP — Regional de Campinas (~300 construtoras associadas)
3. CREA-SP e CAU/SP — registro de pessoa jurídica por município
