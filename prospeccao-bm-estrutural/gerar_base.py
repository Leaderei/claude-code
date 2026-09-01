#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a base de prospeccao da BM Estrutural a partir dos Dados Abertos do CNPJ.

Estrategia: baixa um arquivo por vez, filtra em streaming e APAGA antes de
baixar o proximo. O dump completo tem ~6 GB zipado / ~50 GB em CSV, mas o
pico de disco aqui fica em ~1,5 GB.

Uso:
    pip install -r requirements.txt
    python gerar_base.py                 # roda tudo
    python gerar_base.py --mes 2026-08   # forca uma competencia
    python gerar_base.py --manter-zips   # nao apaga (util para re-rodar filtros)

Saida: saida/base_bm_estrutural_AAAA-MM.csv
"""

import argparse
import csv
import io
import os
import re
import sys
import time
import zipfile
from collections import defaultdict
from datetime import date

import requests

import config as C

DIR = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(DIR, "tmp")
OUT = os.path.join(DIR, "saida")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0 (compatible; base-prospeccao/1.0)"


# ---------------------------------------------------------------------------
# Infraestrutura
# ---------------------------------------------------------------------------

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def descobrir_mes():
    """Encontra a competencia mais recente publicada pela Receita."""
    r = SESSION.get(C.BASE_URL + "/", timeout=60)
    r.raise_for_status()
    meses = sorted(set(re.findall(r"(20\d{2}-\d{2})/", r.text)))
    if not meses:
        raise RuntimeError("Nao consegui listar as competencias em " + C.BASE_URL)
    return meses[-1]


def baixar(url, destino, tentativas=5):
    """Download com retomada e backoff exponencial (2s, 4s, 8s, 16s)."""
    for n in range(tentativas):
        ja = os.path.getsize(destino) if os.path.exists(destino) else 0
        headers = {"Range": f"bytes={ja}-"} if ja else {}
        try:
            with SESSION.get(url, headers=headers, stream=True, timeout=120) as r:
                if r.status_code == 416:      # ja completo
                    return
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0)) + ja
                modo = "ab" if ja and r.status_code == 206 else "wb"
                if modo == "wb":
                    ja = 0
                with open(destino, modo) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        ja += len(chunk)
                        if total:
                            pct = 100 * ja / total
                            print(f"\r    {os.path.basename(destino)}: "
                                  f"{pct:5.1f}%  ({ja/1e6:,.0f} MB)", end="", flush=True)
                print()
                return
        except Exception as e:
            espera = 2 ** (n + 1)
            log(f"  falha ({e}); nova tentativa em {espera}s")
            time.sleep(espera)
    raise RuntimeError(f"Download falhou apos {tentativas} tentativas: {url}")


def linhas_do_zip(caminho):
    """Itera linhas do CSV dentro do zip, sem extrair para disco."""
    with zipfile.ZipFile(caminho) as z:
        nome = z.namelist()[0]
        with z.open(nome) as bruto:
            # A Receita publica em ISO-8859-1; algumas competencias vieram UTF-8.
            amostra = bruto.read(65536)
            try:
                amostra.decode("utf-8")
                enc = "utf-8"
            except UnicodeDecodeError:
                enc = "latin-1"
        with z.open(nome) as bruto:
            fluxo = io.TextIOWrapper(bruto, encoding=enc, errors="replace", newline="")
            for linha in csv.reader(fluxo, delimiter=";", quotechar='"'):
                yield linha


def processar(nome_arquivo, mes, funcao, manter_zips):
    """Baixa -> filtra -> apaga. Mantem o pico de disco baixo."""
    url = f"{C.BASE_URL}/{mes}/{nome_arquivo}"
    caminho = os.path.join(TMP, nome_arquivo)
    if not os.path.exists(caminho):
        log(f"  baixando {nome_arquivo}")
        baixar(url, caminho)
    lidas = 0
    for linha in linhas_do_zip(caminho):
        lidas += 1
        funcao(linha)
    if not manter_zips:
        os.remove(caminho)
    return lidas


# ---------------------------------------------------------------------------
# Helpers de dominio
# ---------------------------------------------------------------------------

def sem_acento(s):
    tabela = str.maketrans("ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ", "AAAAAEEEEIIIIOOOOOUUUUCN")
    return s.upper().translate(tabela).strip()


def meses_desde(aaaammdd):
    """Idade da empresa em meses a partir de AAAAMMDD."""
    if not aaaammdd or len(aaaammdd) != 8 or not aaaammdd.isdigit():
        return None
    ano, mes = int(aaaammdd[:4]), int(aaaammdd[4:6])
    if not 1 <= mes <= 12 or ano < 1900:
        return None
    hoje = date.today()
    return (hoje.year - ano) * 12 + (hoje.month - mes)


def cnaes_da_linha(principal, secundarios):
    """Conjunto de CNAEs do estabelecimento (principal + secundarios)."""
    todos = {principal.strip()}
    if secundarios:
        todos.update(c.strip() for c in secundarios.split(","))
    return {c for c in todos if c}


def dominio_do_email(email):
    """Extrai dominio proprio do e-mail da Receita. Retorna None se generico."""
    email = (email or "").strip().lower()
    if "@" not in email or " " in email:
        return None
    dom = email.rsplit("@", 1)[1].strip().strip(".")
    if not dom or "." not in dom or dom in C.DOMINIOS_GENERICOS:
        return None
    if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", dom):
        return None
    return dom


def formatar_cnpj(basico, ordem, dv):
    n = f"{basico:0>8}{ordem:0>4}{dv:0>2}"
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def formatar_telefone(ddd, numero):
    ddd, numero = (ddd or "").strip(), (numero or "").strip()
    if not ddd or not numero or not numero.isdigit() or len(numero) < 8:
        return ""
    return f"({ddd}) {numero}"


# ---------------------------------------------------------------------------
# Lead score preliminar (antes do scraping)
# ---------------------------------------------------------------------------

def calcular_score(reg):
    """Score 0-100 com o que a Receita entrega. O scraping refina depois."""
    s = 0
    s += {1: 25, 2: 15, 3: 5}.get(reg["anel"], 0)
    s += max((C.CNAES[c]["peso"] for c in reg["_cnaes"] if c in C.CNAES), default=0)
    cap = reg["_capital"]
    if 50_000 <= cap <= 2_000_000:
        s += 15
    elif cap > 0:
        s += 8
    if reg["dominio"]:
        s += 15          # site proprio = alvo do scraping
    if reg["email"]:
        s += 5
    if reg["telefone_1"]:
        s += 10
    idade = reg["_idade_meses"]
    if idade and idade >= 60:
        s += 10
    elif idade and idade >= 24:
        s += 5
    return min(s, 100)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", help="competencia AAAA-MM (padrao: mais recente)")
    ap.add_argument("--manter-zips", action="store_true",
                    help="nao apagar os zips (permite re-rodar filtros offline)")
    ap.add_argument("--indice-amplo", action="store_true",
                    help="tambem gerar indice regional sem filtro de CNAE/capital "
                         "(necessario para calibrar_icp.py)")
    args = ap.parse_args()

    os.makedirs(TMP, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    mes = args.mes or descobrir_mes()
    log(f"Competencia: {mes}")

    # --- municipios-alvo -----------------------------------------------------
    alvo_nomes = {}
    # Com --indice-amplo varremos todos os aneis: o objetivo e descobrir se os
    # clientes atuais caem FORA do recorte, entao o recorte nao pode limitar.
    teto = 99 if args.indice_amplo else C.ANEL_MAXIMO
    for anel in sorted(C.ANEIS):
        if anel > teto:
            continue
        for nome in C.ANEIS[anel]:
            alvo_nomes.setdefault(sem_acento(nome), anel)   # menor anel vence

    log(f"Municipios-alvo: {len(alvo_nomes)} (ate o anel {teto if teto < 99 else 3})")

    codigo_para_anel, codigo_para_nome = {}, {}

    def ler_municipio(l):
        if len(l) < 2:
            return
        nome = sem_acento(l[1])
        if nome in alvo_nomes:
            codigo_para_anel[l[0].strip()] = alvo_nomes[nome]
            codigo_para_nome[l[0].strip()] = l[1].strip()

    log("Etapa 1/5 — tabela de municipios")
    processar("Municipios.zip", mes, ler_municipio, args.manter_zips)

    faltando = set(alvo_nomes) - {sem_acento(v) for v in codigo_para_nome.values()}
    if faltando:
        log(f"  AVISO: nao encontrados na tabela da Receita: {sorted(faltando)}")
    log(f"  {len(codigo_para_anel)} codigos de municipio resolvidos")

    # --- CNAEs de interesse --------------------------------------------------
    cnaes_alvo = {c for c, m in C.CNAES.items()
                  if m["nucleo"] or not C.SOMENTE_NUCLEO}
    log(f"  {len(cnaes_alvo)} CNAEs no filtro: {sorted(cnaes_alvo)}")

    # --- Etapa 2: estabelecimentos ------------------------------------------
    estabelecimentos = []
    basicos = set()
    indice = []          # indice regional amplo (todos os CNAEs)
    stats = defaultdict(int)

    def ler_estabelecimento(l):
        if len(l) < 30:
            return
        stats["lidos"] += 1
        if l[19].strip() != C.UF:
            return
        anel = codigo_para_anel.get(l[20].strip())
        if anel is None:
            return
        stats["na_regiao"] += 1
        if l[5].strip() != C.SITUACAO_ATIVA:
            stats["inativa"] += 1
            return
        basico = l[0].strip()
        if args.indice_amplo:
            # Sem filtro de CNAE nem de capital: e o universo contra o qual a
            # lista de clientes do Ricardo sera casada.
            basicos.add(basico)
            indice.append({
                "_basico": basico,
                "cnpj": formatar_cnpj(basico, l[1].strip(), l[2].strip()),
                "nome_fantasia": l[4].strip(),
                "cnae_principal": l[11].strip(),
                "cnaes_secundarios": l[12].strip(),
                "municipio": codigo_para_nome.get(l[20].strip(), ""),
                "anel": anel,
                "data_inicio": l[10].strip(),
                "telefone_1": formatar_telefone(l[21], l[22]),
                "email": l[27].strip().lower(),
            })
        # O indice amplo varre ate o anel 3; a base filtrada respeita ANEL_MAXIMO.
        if anel > C.ANEL_MAXIMO:
            return
        cn = cnaes_da_linha(l[11], l[12])
        se_encaixa = cn & cnaes_alvo
        if not se_encaixa:
            return
        stats["cnae_ok"] += 1
        idade = meses_desde(l[10].strip())
        if idade is not None and idade < C.IDADE_MINIMA_MESES:
            stats["nova_demais"] += 1
            return
        basicos.add(basico)
        estabelecimentos.append({
            "_basico": basico,
            "cnpj": formatar_cnpj(basico, l[1].strip(), l[2].strip()),
            "matriz": "Matriz" if l[3].strip() == "1" else "Filial",
            "nome_fantasia": l[4].strip(),
            "cnae_principal": l[11].strip(),
            "segmento": C.CNAES.get(l[11].strip(), {}).get(
                "segmento",
                C.CNAES[sorted(se_encaixa)[0]]["segmento"]),
            "endereco": " ".join(x.strip() for x in (l[13], l[14], l[15]) if x.strip()),
            "bairro": l[17].strip(),
            "cep": l[18].strip(),
            "municipio": codigo_para_nome.get(l[20].strip(), ""),
            "anel": anel,
            "telefone_1": formatar_telefone(l[21], l[22]),
            "telefone_2": formatar_telefone(l[23], l[24]),
            "email": l[27].strip().lower(),
            "dominio": dominio_do_email(l[27]),
            "_idade_meses": idade,
            "_cnaes": cn,
        })

    log("Etapa 2/5 — estabelecimentos (10 arquivos, ~4 GB)")
    for i in range(10):
        processar(f"Estabelecimentos{i}.zip", mes, ler_estabelecimento, args.manter_zips)
        log(f"  parte {i}: {len(estabelecimentos):,} candidatos acumulados")

    if not estabelecimentos:
        log("Nenhum estabelecimento encontrado. Revise ANEIS/CNAES em config.py.")
        return

    # --- Etapa 3: empresas (razao social, capital, porte) --------------------
    empresas = {}

    def ler_empresa(l):
        if len(l) < 6 or l[0].strip() not in basicos:
            return
        try:
            capital = float(l[4].strip().replace(",", ".") or 0)
        except ValueError:
            capital = 0.0
        empresas[l[0].strip()] = {
            "razao_social": l[1].strip(),
            "natureza": l[2].strip(),
            "capital": capital,
            "porte": {"01": "ME", "03": "EPP", "05": "Demais"}.get(l[5].strip(), ""),
        }

    log("Etapa 3/5 — empresas (10 arquivos, ~1,5 GB)")
    for i in range(10):
        processar(f"Empresas{i}.zip", mes, ler_empresa, args.manter_zips)
    log(f"  {len(empresas):,} empresas casadas")

    # --- Etapa 4: Simples/MEI ------------------------------------------------
    mei = set()

    def ler_simples(l):
        if len(l) >= 5 and l[0].strip() in basicos and l[4].strip() == "S":
            mei.add(l[0].strip())

    if C.EXCLUIR_MEI:
        log("Etapa 4/5 — Simples/MEI")
        processar("Simples.zip", mes, ler_simples, args.manter_zips)
        log(f"  {len(mei):,} MEIs identificados para exclusao")
    else:
        log("Etapa 4/5 — pulada (EXCLUIR_MEI=False)")

    # --- Etapa 5: join, filtros finais, score, saida -------------------------
    log("Etapa 5/5 — consolidando")
    final = []
    for reg in estabelecimentos:
        emp = empresas.get(reg["_basico"])
        if not emp:
            stats["sem_empresa"] += 1
            continue
        if emp["natureza"][:1] in C.PREFIXOS_NATUREZA_EXCLUIDOS:
            stats["natureza_excluida"] += 1
            continue
        if C.EXCLUIR_MEI and reg["_basico"] in mei:
            stats["mei"] += 1
            continue
        cap = emp["capital"]
        if cap == 0 and not C.MANTER_CAPITAL_ZERO:
            stats["capital_zero"] += 1
            continue
        if cap > 0 and not (C.CAPITAL_SOCIAL_MIN <= cap <= C.CAPITAL_SOCIAL_MAX):
            stats["capital_fora"] += 1
            continue
        reg.update(emp)
        reg["_capital"] = cap
        reg["capital_social"] = f"{cap:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
        reg["score"] = calcular_score(reg)
        reg["prioridade"] = ("A" if reg["score"] >= 60
                             else "B" if reg["score"] >= 40 else "C")
        final.append(reg)

    # matriz primeiro; dentro do mesmo CNPJ basico mantem so o melhor registro
    final.sort(key=lambda r: (r["_basico"], r["matriz"] != "Matriz", -r["score"]))
    unicos, visto = [], set()
    for r in final:
        if r["_basico"] in visto:
            continue
        visto.add(r["_basico"])
        unicos.append(r)
    unicos.sort(key=lambda r: (-r["score"], r["anel"], r["razao_social"]))

    colunas = ["cnpj", "razao_social", "nome_fantasia", "segmento", "prioridade",
               "score", "anel", "municipio", "bairro", "endereco", "cep",
               "telefone_1", "telefone_2", "email", "dominio", "site",
               "capital_social", "porte", "matriz", "cnae_principal",
               "instagram", "responsavel", "tipologia_obra", "status_sdr", "obs"]

    destino = os.path.join(OUT, f"base_bm_estrutural_{mes}.csv")
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for r in unicos:
            r["site"] = f"https://{r['dominio']}" if r["dominio"] else ""
            for vazia in ("instagram", "responsavel", "tipologia_obra",
                          "status_sdr", "obs"):
                r[vazia] = ""
            w.writerow(r)

    # --- indice regional amplo ----------------------------------------------
    if args.indice_amplo:
        cols_idx = ["cnpj", "razao_social", "nome_fantasia", "municipio", "anel",
                    "cnae_principal", "cnaes_secundarios", "capital_social",
                    "porte", "data_inicio", "telefone_1", "email"]
        caminho_idx = os.path.join(OUT, f"indice_regional_{mes}.csv")
        with open(caminho_idx, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols_idx, extrasaction="ignore")
            w.writeheader()
            gravadas = 0
            for r in indice:
                emp = empresas.get(r["_basico"])
                if not emp:
                    continue
                r["razao_social"] = emp["razao_social"]
                r["porte"] = emp["porte"]
                r["capital_social"] = f"{emp['capital']:.2f}"
                w.writerow(r)
                gravadas += 1
        log(f"Indice regional: {caminho_idx} ({gravadas:,} estabelecimentos)")

    # --- relatorio -----------------------------------------------------------
    com_dominio = sum(1 for r in unicos if r["dominio"])
    com_tel = sum(1 for r in unicos if r["telefone_1"])
    print()
    log("=" * 62)
    log(f"BASE GERADA: {destino}")
    log("=" * 62)
    log(f"  Empresas unicas             : {len(unicos):,}")
    log(f"  Com site (dominio proprio)  : {com_dominio:,} "
        f"({100*com_dominio/max(len(unicos),1):.1f}%)")
    log(f"  Com telefone                : {com_tel:,} "
        f"({100*com_tel/max(len(unicos),1):.1f}%)")
    print()
    log("  Por prioridade:")
    for p in "ABC":
        n = sum(1 for r in unicos if r["prioridade"] == p)
        log(f"    {p}: {n:,}")
    log("  Por segmento:")
    for seg, n in sorted(defaultdict(
            int, {s: sum(1 for r in unicos if r["segmento"] == s)
                  for s in {r["segmento"] for r in unicos}}).items(),
            key=lambda kv: -kv[1]):
        log(f"    {seg:<18}: {n:,}")
    log("  Por anel:")
    for a in sorted({r["anel"] for r in unicos}):
        n = sum(1 for r in unicos if r["anel"] == a)
        log(f"    Anel {a}: {n:,}")
    print()
    log("  Descartes:")
    for k in ("na_regiao", "inativa", "cnae_ok", "nova_demais", "mei",
              "capital_fora", "natureza_excluida", "sem_empresa"):
        if stats[k]:
            log(f"    {k:<18}: {stats[k]:,}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrompido. Rode de novo — os downloads sao retomados.")
