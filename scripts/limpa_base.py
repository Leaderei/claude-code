#!/usr/bin/env python3
"""Remove ruido e duplicatas do censo bruto do Places."""
import csv, re, sys, unicodedata
from collections import Counter, defaultdict

ENTRADA = "dados/censo_construcao_macro_louveira.csv"
SAIDA = "dados/censo_limpo.csv"

def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()

# Nao sao empresas de construcao/engenharia/arquitetura -> descarta
DESCARTA = re.compile(r"|".join([
    r"materiais? (para |de )?constru", r"deposito", r"\bcimento\b", r"ferro e aco",
    r"\blajes\b", r"\bblocos\b", r"concreto usinado", r"\bgesso\b", r"\btintas?\b",
    r"madeireir", r"vidracar", r"marmorar", r"serralher", r"\btelhas\b", r"pedreira",
    r"areia.*brita|brita.*areia", r"casa do construtor", r"locacao|locacoes|aluguel de equip",
    r"cacamb", r"entulho", r"andaime", r"\bdecor\b|decoracao", r"paisagism|garden center",
    r"\bmoveis\b", r"ar condicionado|climatizacao", r"marido de aluguel",
    r"imobiliaria|negocios imobiliarios|corretor", r"plantao( de vendas)?",
    r"^condominio", r"^residencial ", r"solucoes visuais", r"mao.?de.?obra temporaria",
    r"dedetiza|jardinagem|^limpeza|piscina", r"\bbau\b|baus", r"guiadeassinantes",
]))

# Sao construcao, mas merecem categoria propria
TERRA = re.compile(r"terraplan|terraplen|escavac|demoli|pavimenta|sondagem|fundac[oa]|estaca|perfurac")

def lixo(nome, cidade):
    n = sa(nome).strip()
    if len(n) < 5: return True
    if n == sa(cidade): return True
    if re.match(r"^(r\.|rua|av\.|avenida|estr\.|rod\.)\s", n): return True
    if n in ("obra", "galpao", "galpoes", "construcao civil", "engenharia", "arquitetura"): return True
    return False

def main():
    r = list(csv.DictReader(open(ENTRADA, encoding="utf-8")))
    antes = len(r)
    passo = Counter()

    mantidos = []
    for x in r:
        nome, cid = x["Empresa"], x["Cidade_Sede"]
        if x["Categoria"] == "Servicos correlatos":
            passo["correlatos"] += 1; continue
        if lixo(nome, cid):
            passo["lixo"] += 1; continue
        if DESCARTA.search(sa(nome)):
            passo["fora do escopo"] += 1; continue
        if TERRA.search(sa(nome)) and x["Categoria"] in ("Construtora", "Engenharia"):
            x["Categoria"] = "Terraplenagem/Infra"
        mantidos.append(x)

    # dedupe: mesmo nome normalizado + cidade, ou mesmo telefone
    def chave_nome(x): return (re.sub(r"[^a-z0-9]", "", sa(x["Empresa"]))[:28], sa(x["Cidade_Sede"]))
    def riqueza(x): return (bool(x["Telefone"]), bool(x["Site"]), bool(x["Avaliacao"]),
                            int(x["Qtd_Avaliacoes"] or 0))
    grupos = defaultdict(list)
    for x in mantidos: grupos[chave_nome(x)].append(x)
    dedup = [max(g, key=riqueza) for g in grupos.values()]
    passo["dup nome"] = len(mantidos) - len(dedup)

    por_tel = defaultdict(list)
    sem_tel = []
    for x in dedup:
        (por_tel[re.sub(r"\D", "", x["Telefone"])] if x["Telefone"] else sem_tel).append(x) \
            if x["Telefone"] else sem_tel.append(x)
    final = sem_tel + [max(g, key=riqueza) for g in por_tel.values()]
    passo["dup telefone"] = len(dedup) - len(final)

    final.sort(key=lambda x: (x["Prioridade_ICP"], x["Cidade_Sede"], x["Categoria"], x["Empresa"]))
    for i, x in enumerate(final, 1): x["ID"] = f"{i:04d}"
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(r[0].keys())); w.writeheader(); w.writerows(final)

    print(f"{antes} -> {len(final)} empresas  (removidos {antes-len(final)})")
    for k, v in passo.most_common(): print(f"  {k:16s} {v:5d}")
    print("categoria:", dict(Counter(x["Categoria"] for x in final)))
    print("prioridade:", dict(Counter(x["Prioridade_ICP"] for x in final)))
    print("A com telefone:", sum(1 for x in final if x["Prioridade_ICP"]=="A" and x["Telefone"]))

main()
