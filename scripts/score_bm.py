#!/usr/bin/env python3
"""Aplica o lead scoring do ICP da BM Estrutural e gera a aba das cidades de foco."""
import csv, re, sys, unicodedata
from collections import Counter

FOCO = ["Louveira", "Vinhedo", "Itatiba", "Jundiai", "Itupeva"]
ENTRADA, SAIDA = "dados/censo_limpo.csv", "dados/aba_foco_bm.csv"

# Clientes de referencia informados por Ricardo (31/08/2026). Servem de gabarito
# do ICP e nao devem ser prospectados como lead novo.
CLIENTES_BM = {"rezyd": "Rezyd", "jraconstrutora": "JRA", "labengenharia": "LAB",
               "jmsolucoes": "JM Solucoes", "hudson": "Hudson Engenharia",
               "arkaf": "Studio Arkaf", "patriciazampieri": "Patricia Zampieri",
               "curycamargo": "Cury Camargo (Sandra Cury)"}

def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()

# Sinais de que a empresa gerencia/executa obra -> qualificador central do ICP
GERENCIA = re.compile(r"gerenciamento de obra|gestao de obra|administracao de obra|"
                      r"e construcao|e construcoes|construcao e|obras e|e obras|"
                      r"engenharia e arquitetura|arquitetura e engenharia|"
                      r"projeto e obra|execucao|empreendimento")
# Sinais de que NAO compra estrutura
SO_INTERIORES = re.compile(r"interiores|design de interior|paisagism|decorac|"
                           r"ambientes planejados|marcenaria|moveis")
# Construtora de grande porte / incorporacao de larga escala -> fora do nicho
# Exclusao e por PORTE e modelo (predio/larga escala), nao pela palavra
# "incorporadora" - construtora pequena costuma ter as duas atividades no nome.
GRANDE = re.compile(r"loteamento|urbanismo|\bspe\b|participacoes|"
                    r"mrv|tenda|cury |direcional|patriani|helbor|bild|wtorre")

# Recalibrado contra os 11 clientes de referencia. A carteira atual e majoritariamente
# de construtoras; a reuniao prioriza engenharia/arquitetura por eficiencia de venda
# (negociacao direta com o socio), nao por serem clientes melhores. Logo as tres
# categorias pontuam alto e a diferenca entre elas e pequena.
PESO_CAT = {"Engenharia": 35, "Arquitetura": 32, "Construtora": 30,
            "Incorporadora": 25, "Terraplenagem/Infra": -35, "Empreiteira": -30}
DIST = {"Louveira": 0, "Vinhedo": 9, "Valinhos": 17, "Jundiai": 18, "Itupeva": 22, "Itatiba": 27}

def gerencia_obra(nome, cat):
    n = sa(nome)
    if SO_INTERIORES.search(n) and not GERENCIA.search(n) \
            and not re.search(r"engenharia|construcao|construtora|\bobra", n):
        return "Nao"
    if GERENCIA.search(n):
        return "Sim (indicio no nome)"
    if cat in ("Construtora", "Engenharia"):
        return "Provavel"
    return "A verificar"

def pontua(x):
    p, por = 0, []
    cat = x["Categoria"]
    v = PESO_CAT.get(cat, 0); p += v; por.append(f"{cat} {v:+d}")
    n = sa(x["Empresa"])
    if GRANDE.search(n):
        p -= 45; por.append("larga escala/loteamento -45")
    g = gerencia_obra(x["Empresa"], cat)
    # indicio de nome e proxy fraco: pesa pouco ate o scraping preencher o campo
    if g.startswith("Sim"): p += 12; por.append("gerencia obra +12")
    elif g == "Nao":        p -= 25; por.append("so interiores -25")
    # as 5 cidades ja estao dentro do raio atendido (BM tem vendedor em todas)
    d = DIST.get(x["Cidade_Sede"], 99)
    p += 15 if d <= 15 else 10
    por.append(f"{d}km +{15 if d <= 15 else 10}")
    if x["Site"]:     p += 10; por.append("site +10")
    if x["Telefone"]: p += 5;  por.append("tel +5")
    try:
        if float(x["Avaliacao"] or 0) >= 4.5 and int(x["Qtd_Avaliacoes"] or 0) >= 5:
            p += 5; por.append("reputacao +5")
    except ValueError:
        pass
    return p, "; ".join(por), g

def faixa(p):
    return "A - abordar primeiro" if p >= 62 else \
           "B - abordar depois"   if p >= 50 else \
           "C - baixa aderencia"  if p >= 30 else "D - fora do ICP"

def main():
    r = [x for x in csv.DictReader(open(ENTRADA, encoding="utf-8"))
         if x["Cidade_Sede"] in FOCO]
    for x in r:
        x["Score_ICP"], x["Score_Motivo"], x["Gerencia_Obra"] = pontua(x)
        chave = re.sub(r"[^a-z0-9]", "", sa(x["Empresa"]))
        x["Cliente_BM"] = next((v for k, v in CLIENTES_BM.items() if k in chave), "")
        if x["Cliente_BM"]:
            x["Status_Prospeccao"] = "JA E CLIENTE - nao prospectar"
    r.sort(key=lambda x: (-x["Score_ICP"], x["Cidade_Sede"], x["Empresa"]))
    for i, x in enumerate(r, 1):
        x["Rank"] = i; x["Faixa_ICP"] = faixa(x["Score_ICP"])

    COLS = ["Rank","Cliente_BM","Empresa","Categoria","Gerencia_Obra","Cidade_Sede","Dist_Louveira_km",
            "Telefone","Site","Avaliacao","Qtd_Avaliacoes","Score_ICP","Faixa_ICP",
            "Score_Motivo","Endereco","Google_Maps","Nome_Decisor","Email",
            "Status_Prospeccao","Observacoes"]
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(r)

    print(f"{len(r)} empresas nas 5 cidades -> {SAIDA}")
    print("faixa:", dict(Counter(x["Faixa_ICP"] for x in r)))
    print("gerencia obra:", dict(Counter(x["Gerencia_Obra"] for x in r)))
    print(f"com telefone: {sum(1 for x in r if x['Telefone'])} | com site: {sum(1 for x in r if x['Site'])}")
    print("\ntop 12:")
    for x in r[:12]:
        print(f"  {x['Score_ICP']:3d}  {x['Empresa'][:38]:40s} {x['Categoria'][:11]:12s} {x['Cidade_Sede']:9s} {x['Site'][:24]}")

main()
