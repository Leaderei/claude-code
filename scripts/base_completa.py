#!/usr/bin/env python3
"""Gera dados/BASE_COMPLETA.csv a partir de censo_limpo.csv + raw_places/raw_detalhes.

Mantem a planilha unica sempre em sincronia com o que foi coletado, em vez de
montar o arquivo ad-hoc a cada rodada (foi assim que 5.553 linhas ficaram
desatualizadas na versao anterior).
"""
import csv, json, os, re, unicodedata
from collections import Counter

LIMPO = "dados/censo_limpo.csv"
RAW = "dados/raw_places.jsonl"
DET = "dados/raw_detalhes.jsonl"
SAIDA = "dados/BASE_COMPLETA.csv"

COLS = ["#","Empresa","Segmento","Cidade","UF","Regiao","Telefone","Site","Email",
        "Nota","Avals","Endereco","Google_Maps","Dist_Louveira_km","Enriquecido",
        "Nome_Decisor","Status_Prospeccao","Observacoes"]

FOCO = {"vinhedo","louveira","itatiba","jundiai","itupeva","valinhos",
        "campinas","barueri","sao paulo","cajamar"}

def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()

def main():
    det = {}
    if os.path.exists(DET):
        for l in open(DET, encoding="utf-8"):
            d = json.loads(l); det[d["id"]] = d
    uri2id = {}
    for l in open(RAW, encoding="utf-8"):
        p = json.loads(l); uri2id[p.get("googleMapsUri", "")] = p["id"]

    linhas = []
    for x in csv.DictReader(open(LIMPO, encoding="utf-8")):
        pid = uri2id.get(x["Google_Maps"], "")
        d = det.get(pid) or {}
        tel = d.get("nationalPhoneNumber") or x["Telefone"] or ""
        site = d.get("websiteUri") or x["Site"] or ""
        cid = x["Cidade_Sede"]
        linhas.append({
            "#": "", "Empresa": x["Empresa"], "Segmento": x["Categoria"],
            "Cidade": cid, "UF": x["UF"] or "SP",
            "Regiao": "Foco" if sa(cid) in FOCO else "Entorno",
            "Telefone": tel, "Site": site, "Email": x.get("Email", ""),
            "Nota": str(d.get("rating") or x.get("Avaliacao") or ""),
            "Avals": str(d.get("userRatingCount") or x.get("Qtd_Avaliacoes") or ""),
            "Endereco": x["Endereco"], "Google_Maps": x["Google_Maps"],
            "Dist_Louveira_km": x["Dist_Louveira_km"],
            "Enriquecido": "Sim" if pid in det else "Nao",
            "Nome_Decisor": x.get("Nome_Decisor", ""),
            "Status_Prospeccao": x.get("Status_Prospeccao", "") or "Nao contatado",
            "Observacoes": x.get("Observacoes", ""),
        })

    ORD = {"Construtora":0,"Engenharia":1,"Arquitetura":2,"Incorporadora":3,
           "Loteadora":4,"Empreiteira":5}
    linhas.sort(key=lambda r: (0 if r["Regiao"] == "Foco" else 1, r["Cidade"],
                               ORD.get(r["Segmento"], 9), sa(r["Empresa"])))
    for i, r in enumerate(linhas, 1): r["#"] = str(i)

    with open(SAIDA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(linhas)

    foco = [r for r in linhas if r["Regiao"] == "Foco"]
    print(f"{len(linhas)} empresas | foco {len(foco)} | entorno {len(linhas)-len(foco)}")
    print("segmento (foco):", dict(Counter(r["Segmento"] for r in foco).most_common()))
    print("enriquecidas:", sum(1 for r in linhas if r["Enriquecido"] == "Sim"))

main()
