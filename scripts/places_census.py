#!/usr/bin/env python3
"""
Censo de construtoras, engenharias e arquiteturas via Google Places API (New).

Uso:
  python3 scripts/places_census.py coleta    --key SUA_CHAVE [--tier 1|2|3] [--grid]
  python3 scripts/places_census.py enriquece --key SUA_CHAVE [--prioridade A,B] [--limite N]
  python3 scripts/places_census.py consolida

coleta    -> varre a API com field mask enxuto (SKU Pro, 5.000 gratis/mes)
             e grava dados/raw_places.jsonl (resumivel)
enriquece -> busca telefone/site/nota via Place Details (SKU Enterprise,
             1.000 gratis/mes) so para o subconjunto que interessa
consolida -> mescla, deduplica e gera o CSV no schema da base
"""
import argparse, csv, json, os, re, sys, time, unicodedata
import urllib.request, urllib.error

RAW = "dados/raw_places.jsonl"
OUT = "dados/censo_construcao_macro_louveira.csv"
ENDPOINT_TEXT = "https://places.googleapis.com/v1/places:searchText"
ENDPOINT_NEAR = "https://places.googleapis.com/v1/places:searchNearby"

# O SKU cobrado e o mais caro entre os campos pedidos. Telefone, site, rating e
# userRatingCount disparam o SKU Enterprise. Por isso a varredura usa mask enxuto
# (SKU Pro) e o contato vem depois, via Place Details, so para quem interessa.
FIELDS_DESCOBERTA = ",".join("places." + f for f in [
    "id", "displayName", "formattedAddress", "addressComponents",
    "location", "types", "primaryType", "primaryTypeDisplayName",
    "googleMapsUri", "businessStatus",
]) + ",nextPageToken"

FIELDS_DETALHE = ",".join([
    "id", "displayName", "nationalPhoneNumber", "internationalPhoneNumber",
    "websiteUri", "rating", "userRatingCount", "businessStatus",
])

# searchNearby nao aceita nextPageToken no field mask (retorna HTTP 400)
FIELDS_GRADE = FIELDS_DESCOBERTA.replace(",nextPageToken", "")

ENDPOINT_DETALHE = "https://places.googleapis.com/v1/places/"

# (municipio, lat, lon, raio_m, tier) - tier 1 = nucleo <=25km de Louveira
MUNICIPIOS = [
    ("Louveira",             -23.0872, -46.9508,  8000, 0),
    ("Vinhedo",              -23.0299, -46.9750,  9000, 0),
    ("Valinhos",             -22.9707, -46.9958, 11000, 0),
    ("Jundiai",              -23.1857, -46.8978, 16000, 0),
    ("Itupeva",              -23.1528, -47.0578, 11000, 0),
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
    # 2a passada - termos adicionados apos medir 21% de resultados ineditos
    "engenheiro civil", "empresa de construcao", "construtora residencial",
    "reforma predial", "estruturas metalicas", "steel frame",
    "alvenaria estrutural", "impermeabilizacao de obras", "obras comerciais",
    "projeto hidraulico predial",
]

TIPOS_GRID = ["general_contractor", "roofing_contractor", "electrician", "plumber"]


def _chama(req):
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


def post(url, body, key, mask):
    return _chama(urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                 "X-Goog-FieldMask": mask}))


def get(url, key, mask):
    return _chama(urllib.request.Request(
        url, method="GET",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": mask}))


def coleta(key, tier, usar_grid=False):
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
                resp = post(ENDPOINT_TEXT, corpo, key, FIELDS_DESCOBERTA)
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

    saida.close()
    print(f"\nfim: {len(vistos)} lugares unicos em {chamadas} chamadas de API")


# Bounding box do nucleo <=22 km (Louveira, Vinhedo, Valinhos, Jundiai, Itupeva)
CAIXA_NUCLEO = dict(lat_min=-23.24, lat_max=-22.92, lon_min=-47.11, lon_max=-46.83)
# Itatiba entrou nas cidades de foco depois da 1a grade e fica fora da caixa acima
CAIXA_ITATIBA = dict(lat_min=-23.10, lat_max=-22.91, lon_min=-46.92, lon_max=-46.73)
CAIXAS = {"nucleo": CAIXA_NUCLEO, "itatiba": CAIXA_ITATIBA}
PASSO = 0.03           # ~3,3 km por celula
TERMOS_GRADE = ["construtora", "engenharia civil", "escritorio de arquitetura"]


def grade(key, caixa=None, passo=PASSO):
    """Varre a regiao em retangulos pequenos. searchText aceita
    locationRestriction.rectangle - e assim nenhuma consulta chega no teto de
    60 resultados, que era o que truncava a busca por cidade inteira."""
    caixa = caixa or CAIXA_NUCLEO
    os.makedirs("dados", exist_ok=True)
    vistos, feitas = set(), set()
    if os.path.exists(RAW):
        for linha in open(RAW, encoding="utf-8"):
            try:
                r = json.loads(linha); vistos.add(r["id"]); feitas.add(r.get("_consulta", ""))
            except Exception:
                pass
    print(f"base atual: {len(vistos)} lugares")

    lats, lons = [], []
    v = caixa["lat_min"]
    while v < caixa["lat_max"]:
        lats.append(v); v = round(v + passo, 4)
    v = caixa["lon_min"]
    while v < caixa["lon_max"]:
        lons.append(v); v = round(v + passo, 4)
    celulas = [(a, b) for a in lats for b in lons]
    print(f"grade: {len(lats)}x{len(lons)} = {len(celulas)} celulas x {len(TERMOS_GRADE)} termos")

    saida = open(RAW, "a", encoding="utf-8")
    chamadas = novos_total = 0
    for n, (la, lo) in enumerate(celulas, 1):
        for termo in TERMOS_GRADE:
            consulta = f"grade|{la:.3f}|{lo:.3f}|{termo}"
            if consulta in feitas:
                continue
            token, pagina, novos = None, 0, 0
            while pagina < 3:
                corpo = {"textQuery": termo, "languageCode": "pt-BR", "regionCode": "BR",
                         "pageSize": 20,
                         "locationRestriction": {"rectangle": {
                             "low": {"latitude": la, "longitude": lo},
                             "high": {"latitude": round(la + passo, 4),
                                      "longitude": round(lo + passo, 4)}}}}
                if token:
                    corpo["pageToken"] = token
                resp = post(ENDPOINT_TEXT, corpo, key, FIELDS_DESCOBERTA)
                chamadas += 1
                if not resp:
                    break
                for pl in resp.get("places") or []:
                    if pl.get("id") in vistos:
                        continue
                    vistos.add(pl["id"])
                    pl["_consulta"], pl["_municipio_busca"] = consulta, "grade"
                    saida.write(json.dumps(pl, ensure_ascii=False) + "\n")
                    novos += 1
                token = resp.get("nextPageToken")
                pagina += 1
                if not token:
                    break
                time.sleep(0.3)
            saida.flush()
            novos_total += novos
        if n % 10 == 0 or n == len(celulas):
            print(f"  celula {n}/{len(celulas)}  {chamadas} chamadas  +{novos_total} novos  (total {len(vistos)})")
    saida.close()
    print(f"\nfim: +{novos_total} novos em {chamadas} chamadas | base = {len(vistos)}")


DETALHES = "dados/raw_detalhes.jsonl"


def enriquece(key, limite, so_prioridade, so_cidades=None):
    """Busca telefone/site/nota (SKU Enterprise) apenas para o subconjunto escolhido."""
    if not os.path.exists(RAW):
        sys.exit(f"nao encontrei {RAW} - rode 'coleta' primeiro")

    alvos, vistos = [], set()
    with open(RAW, encoding="utf-8") as f:
        for linha in f:
            p_ = json.loads(linha)
            if p_["id"] in vistos:
                continue
            vistos.add(p_["id"])
            nome = (p_.get("displayName") or {}).get("text", "")
            cat = classifica(nome, p_.get("types"))
            if cat == "Servicos correlatos":
                continue
            cid = sem_acento(cidade_de(p_)).title()
            d = DIST.get(cid, 999)
            prio = "A" if d <= 22 else ("B" if d <= 45 else "C")
            if so_cidades:
                if sem_acento(cid) not in so_cidades:
                    continue
            elif so_prioridade and prio not in so_prioridade:
                continue
            alvos.append((p_["id"], nome, prio))

    feitos = set()
    if os.path.exists(DETALHES):
        with open(DETALHES, encoding="utf-8") as f:
            for linha in f:
                try:
                    feitos.add(json.loads(linha)["id"])
                except Exception:
                    pass
    alvos = [a for a in alvos if a[0] not in feitos]
    alvos.sort(key=lambda a: a[2])
    if limite:
        alvos = alvos[:limite]

    custo_1k = 25.0  # USD/1000 - PREMISSA: confirmar o valor do SKU no console
    print(f"{len(alvos)} a enriquecer | {len(feitos)} ja feitos")
    print(f"estimativa: ~US$ {max(0, len(alvos) - 1000) * custo_1k / 1000:.2f} "
          f"(assumindo 1.000 gratuitos/mes no SKU Enterprise)")

    saida = open(DETALHES, "a", encoding="utf-8")
    for i, (pid, nome, prio) in enumerate(alvos, 1):
        resp = get(ENDPOINT_DETALHE + pid, key, FIELDS_DETALHE)
        if resp:
            saida.write(json.dumps(resp, ensure_ascii=False) + "\n")
            saida.flush()
        if i % 25 == 0 or i == len(alvos):
            print(f"  {i}/{len(alvos)}  [{prio}] {nome[:45]}")
        time.sleep(0.05)
    saida.close()
    print(f"fim: detalhes em {DETALHES}")


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

    det = {}
    if os.path.exists(DETALHES):
        with open(DETALHES, encoding="utf-8") as f:
            for linha in f:
                try:
                    d_ = json.loads(linha)
                    det[d_["id"]] = d_
                except Exception:
                    pass
        print(f"mesclando {len(det)} registros enriquecidos")

    linhas = []
    for p in registros:
        p.update({k: v for k, v in det.get(p["id"], {}).items() if k != "displayName"})
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
            "Confianca_do_Dado": "Alta",
            "Fonte": "Google Places API" + (" + Details" if p["id"] in det else ""),
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
    c.add_argument("--tier", type=int, default=2, choices=[0, 1, 2, 3])
    c.add_argument("--grid", action="store_true")
    g = sub.add_parser("grade")
    g.add_argument("--key", required=True)
    g.add_argument("--passo", type=float, default=PASSO)
    g.add_argument("--caixa", default="nucleo", choices=list(CAIXAS))
    e = sub.add_parser("enriquece")
    e.add_argument("--key", required=True)
    e.add_argument("--limite", type=int, default=0, help="teto de chamadas (0 = sem teto)")
    e.add_argument("--prioridade", default="A,B", help="ex: A ou A,B ou A,B,C")
    e.add_argument("--cidades", default="", help="ex: Louveira,Vinhedo (ignora --prioridade)")
    sub.add_parser("consolida")
    a = ap.parse_args()
    if a.cmd == "coleta":
        coleta(a.key, a.tier, a.grid)
    elif a.cmd == "grade":
        grade(a.key, caixa=CAIXAS[a.caixa], passo=a.passo)
    elif a.cmd == "enriquece":
        enriquece(a.key, a.limite, set(a.prioridade.split(",")),
                  {sem_acento(c) for c in a.cidades.split(",") if c.strip()} or None)
    else:
        consolida()
