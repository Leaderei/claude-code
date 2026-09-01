#!/usr/bin/env python3
"""
Censo de construtoras, engenharias e arquiteturas via Google Places API (New).

Uso:
  python3 scripts/places_census.py coleta --key SUA_CHAVE [--tier 1|2|3] [--grid]
  python3 scripts/places_census.py consolida

Estagio 'coleta'  -> varre a API e grava dados/raw_places.jsonl (resumivel)
Estagio 'consolida' -> normaliza, deduplica e gera o CSV no schema da base
"""
import argparse, csv, json, os, re, sys, time, unicodedata
import urllib.request, urllib.error

RAW = "dados/raw_places.jsonl"
OUT = "dados/censo_construcao_macro_louveira.csv"
ENDPOINT_TEXT = "https://places.googleapis.com/v1/places:searchText"
ENDPOINT_NEAR = "https://places.googleapis.com/v1/places:searchNearby"

FIELDS = ",".join("places." + f for f in [
    "id", "displayName", "formattedAddress", "shortFormattedAddress", "addressComponents",
    "nationalPhoneNumber", "internationalPhoneNumber", "websiteUri", "googleMapsUri",
    "rating", "userRatingCount", "businessStatus", "types", "primaryType",
    "primaryTypeDisplayName", "location",
]) + ",nextPageToken"

# (municipio, lat, lon, raio_m, tier) - tier 1 = nucleo <=25km de Louveira
MUNICIPIOS = [
    ("Louveira",             -23.0872, -46.9508,  8000, 1),
    ("Vinhedo",              -23.0299, -46.9750,  9000, 1),
    ("Valinhos",             -22.9707, -46.9958, 11000, 1),
    ("Jundiai",              -23.1857, -46.8978, 16000, 1),
    ("Itupeva",              -23.1528, -47.0578, 11000, 1),
    ("Itatiba",              -23.0053, -46.8389, 12000, 1),
    ("Jarinu",               -23.1017, -46.7283, 11000, 2),
    ("Campinas",             -22.9099, -47.0626, 20000, 2),
    ("Cabreuva",             -23.3078, -47.1325, 12000, 2),
    ("Varzea Paulista",      -23.2119, -46.8283,  6000, 2),
    ("Campo Limpo Paulista", -23.2069, -46.7825,  7000, 2),
    ("Morungaba",            -22.8803, -46.7925,  8000, 2),
    ("Indaiatuba",           -23.0895, -47.2178, 14000, 2),
    ("Atibaia",              -23.1171, -46.5504, 14000, 3),
    ("Hortolandia",          -22.8583, -47.2200,  8000, 3),
    ("Sumare",               -22.8219, -47.2669, 11000, 3),
    ("Paulinia",             -22.7614, -47.1542, 10000, 3),
    ("Monte Mor",            -22.9469, -47.3153,  9000, 3),
    ("Salto",                -23.2008, -47.2872, 10000, 3),
    ("Americana",            -22.7397, -47.3313, 11000, 3),
]

TERMOS = [
    "construtora", "incorporadora", "construcao civil", "empreiteira de obras",
    "engenharia civil", "empresa de engenharia", "escritorio de arquitetura",
    "arquiteto", "arquitetura e interiores", "projetos de engenharia",
    "gerenciamento de obras", "reforma e construcao", "construcao de galpao industrial",
    "pre-moldados de concreto", "terraplenagem", "projeto estrutural",
]

TIPOS_GRID = ["general_contractor", "roofing_contractor", "electrician", "plumber"]


def post(url, body, key):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                 "X-Goog-FieldMask": FIELDS})
    for tentativa in range(5):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** tentativa)
                continue
            print(f"  ! HTTP {e.code}: {corpo}", file=sys.stderr)
            return None
        except Exception as e:
            time.sleep(2 ** tentativa)
    return None


def coleta(key, tier, usar_grid):
    os.makedirs("dados", exist_ok=True)
    vistos, feitas = set(), set()
    if os.path.exists(RAW):
        with open(RAW, encoding="utf-8") as f:
            for linha in f:
                try:
                    reg = json.loads(linha)
                    vistos.add(reg["id"])
                    feitas.add(reg.get("_consulta", ""))
                except Exception:
                    pass
        print(f"retomando: {len(vistos)} lugares, {len(feitas)} consultas ja feitas")

    alvos = [m for m in MUNICIPIOS if m[4] <= tier]
    chamadas = 0
    saida = open(RAW, "a", encoding="utf-8")

    def grava(places, consulta, municipio):
        novos = 0
        for p in places or []:
            if p.get("id") in vistos:
                continue
            vistos.add(p["id"])
            p["_consulta"], p["_municipio_busca"] = consulta, municipio
            saida.write(json.dumps(p, ensure_ascii=False) + "\n")
            novos += 1
        saida.flush()
        return novos

    for nome, lat, lon, raio, _ in alvos:
        for termo in TERMOS:
            consulta = f"text|{nome}|{termo}"
            if consulta in feitas:
                continue
            token, pagina, novos = None, 0, 0
            while pagina < 3:
                corpo = {"textQuery": f"{termo} em {nome}, SP",
                         "languageCode": "pt-BR", "regionCode": "BR", "pageSize": 20,
                         "locationBias": {"circle": {
                             "center": {"latitude": lat, "longitude": lon},
                             "radius": float(raio)}}}
                if token:
                    corpo["pageToken"] = token
                resp = post(ENDPOINT_TEXT, corpo, key)
                chamadas += 1
                if not resp:
                    break
                novos += grava(resp.get("places"), consulta, nome)
                token = resp.get("nextPageToken")
                pagina += 1
                if not token:
                    break
                time.sleep(0.4)
            print(f"[{chamadas:4d}] {nome:22s} {termo:32s} +{novos:3d}  (total {len(vistos)})")

    if usar_grid:
        print("\n--- varredura em grade (nearby) ---")
        for nome, lat, lon, raio, _ in alvos:
            passo = 0.025  # ~2.7 km
            n = max(1, int((raio / 111000) / passo))
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    plat, plon = lat + i * passo, lon + j * passo
                    consulta = f"grid|{plat:.4f}|{plon:.4f}"
                    if consulta in feitas:
                        continue
                    corpo = {"includedTypes": TIPOS_GRID, "maxResultCount": 20,
                             "languageCode": "pt-BR", "regionCode": "BR",
                             "locationRestriction": {"circle": {
                                 "center": {"latitude": plat, "longitude": plon},
                                 "radius": 2000.0}}}
                    resp = post(ENDPOINT_NEAR, corpo, key)
                    chamadas += 1
                    if resp:
                        novos = grava(resp.get("places"), consulta, nome)
                        if novos:
                            print(f"[grid {chamadas:4d}] {nome:18s} +{novos:3d} (total {len(vistos)})")

    saida.close()
    print(f"\nfim: {len(vistos)} lugares unicos em {chamadas} chamadas de API")


# ---------------- consolidacao ----------------

COLS = ["ID","Empresa","Razao_Social_CNPJ","Categoria","Especialidade","Cidade_Sede","UF",
        "Eixo_Regional","Dist_Louveira_km","Raio_de_Atuacao","Porte_Estimado","Fundacao","Site",
        "Telefone","Endereco","Social","Decisor_Alvo_Cargo","Nome_Decisor","Email",
        "Gatilho_Comercial","Prioridade_ICP","Confianca_do_Dado","Fonte","Status_Prospeccao",
        "Proxima_Acao","Observacoes","Google_Maps","Avaliacao","Qtd_Avaliacoes","Status_Negocio"]

DIST = {"Louveira":0,"Vinhedo":9,"Valinhos":17,"Jundiai":18,"Itupeva":22,"Itatiba":27,
        "Jarinu":30,"Campinas":30,"Varzea Paulista":30,"Campo Limpo Paulista":32,
        "Cabreuva":35,"Morungaba":38,"Indaiatuba":45,"Atibaia":45,"Hortolandia":40,
        "Sumare":45,"Paulinia":45,"Monte Mor":50,"Salto":50,"Americana":60}

EIXO = {"Louveira":"Eixo Louveira","Vinhedo":"Eixo Louveira","Valinhos":"Eixo Louveira",
        "Itupeva":"Eixo Louveira","Jundiai":"Eixo Jundiai","Jarinu":"Eixo Jundiai",
        "Cabreuva":"Eixo Jundiai","Varzea Paulista":"Eixo Jundiai",
        "Campo Limpo Paulista":"Eixo Jundiai","Itatiba":"Eixo Itatiba/Morungaba",
        "Morungaba":"Eixo Itatiba/Morungaba"}

DEC = {"Arquitetura":"Socio / Arquiteto titular",
       "Construtora":"Socio-Diretor / Diretor de Obras",
       "Incorporadora":"Diretor Comercial / Diretor de Incorporacao",
       "Engenharia":"Socio-Diretor / Engenheiro responsavel",
       "Empreiteira":"Proprietario / Encarregado geral",
       "Servicos correlatos":"Proprietario"}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def classifica(nome, tipos):
    n, t = sem_acento(nome), " ".join(tipos or [])
    if re.search(r"arquitet|interiores|design de interior", n):
        return "Arquitetura"
    if re.search(r"incorporad|empreendimentos imob|urbanismo|loteament", n):
        return "Incorporadora"
    if re.search(r"construtor|construcoes|construcao", n):
        return "Construtora"
    if re.search(r"engenharia|engenharia civil|projetos estrutur", n):
        return "Engenharia"
    if re.search(r"empreiteir|empreitad", n):
        return "Empreiteira"
    if "general_contractor" in t:
        return "Construtora"
    return "Servicos correlatos"


def cidade_de(p):
    for c in p.get("addressComponents") or []:
        if "administrative_area_level_2" in (c.get("types") or []) or "locality" in (c.get("types") or []):
            return c.get("longText") or ""
    m = re.search(r"-\s*([^-,]+),\s*SP", p.get("formattedAddress") or "")
    return m.group(1).strip() if m else (p.get("_municipio_busca") or "")


def consolida():
    if not os.path.exists(RAW):
        sys.exit(f"nao encontrei {RAW} - rode o estagio 'coleta' primeiro")
    registros, vistos = [], set()
    with open(RAW, encoding="utf-8") as f:
        for linha in f:
            p = json.loads(linha)
            if p["id"] in vistos:
                continue
            vistos.add(p["id"])
            registros.append(p)

    linhas = []
    for p in registros:
        nome = (p.get("displayName") or {}).get("text", "")
        cat = classifica(nome, p.get("types"))
        if cat == "Servicos correlatos" and not re.search(
                r"obra|reforma|predial|galpao|estrutur|terraplen|concret|alvenar",
                sem_acento(nome)):
            continue  # descarta ruido (imobiliaria, loja de material, etc.)
        cid = sem_acento(cidade_de(p)).title()
        d = DIST.get(cid, "")
        prio = "A" if d != "" and d <= 22 else ("B" if d != "" and d <= 45 else "C")
        linhas.append({
            "ID": "", "Empresa": nome, "Razao_Social_CNPJ": "", "Categoria": cat,
            "Especialidade": (p.get("primaryTypeDisplayName") or {}).get("text", ""),
            "Cidade_Sede": cid, "UF": "SP",
            "Eixo_Regional": EIXO.get(cid, "RMC / entorno"), "Dist_Louveira_km": d,
            "Raio_de_Atuacao": "", "Porte_Estimado": "", "Fundacao": "",
            "Site": p.get("websiteUri", ""),
            "Telefone": p.get("nationalPhoneNumber", ""),
            "Endereco": p.get("formattedAddress", ""), "Social": "",
            "Decisor_Alvo_Cargo": DEC.get(cat, ""), "Nome_Decisor": "", "Email": "",
            "Gatilho_Comercial": "", "Prioridade_ICP": prio,
            "Confianca_do_Dado": "Alta", "Fonte": "Google Places API",
            "Status_Prospeccao": "Nao iniciado",
            "Proxima_Acao": "Validar site e decisor",
            "Observacoes": "", "Google_Maps": p.get("googleMapsUri", ""),
            "Avaliacao": p.get("rating", ""), "Qtd_Avaliacoes": p.get("userRatingCount", ""),
            "Status_Negocio": p.get("businessStatus", ""),
        })

    linhas.sort(key=lambda r: (r["Prioridade_ICP"], r["Cidade_Sede"], r["Empresa"]))
    for i, r in enumerate(linhas, 1):
        r["ID"] = f"{i:04d}"
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(linhas)

    from collections import Counter
    print(f"{len(linhas)} empresas -> {OUT}")
    print("categoria:", dict(Counter(r["Categoria"] for r in linhas)))
    print("prioridade:", dict(Counter(r["Prioridade_ICP"] for r in linhas)))
    print("com site:", sum(1 for r in linhas if r["Site"]),
          "| com telefone:", sum(1 for r in linhas if r["Telefone"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("coleta")
    c.add_argument("--key", required=True)
    c.add_argument("--tier", type=int, default=2, choices=[1, 2, 3])
    c.add_argument("--grid", action="store_true")
    sub.add_parser("consolida")
    a = ap.parse_args()
    if a.cmd == "coleta":
        coleta(a.key, a.tier, a.grid)
    else:
        consolida()
