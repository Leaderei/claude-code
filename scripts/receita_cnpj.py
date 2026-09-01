#!/usr/bin/env python3
"""
Filtra os dados abertos de CNPJ da Receita Federal por municipio + CNAE,
sem descompactar os arquivos (le direto de dentro dos .zip, linha a linha).

Uso:
  1) python3 scripts/receita_cnpj.py inspecionar --dir ~/receita
  2) python3 scripts/receita_cnpj.py extrair     --dir ~/receita --saida dados/receita_filtrado.csv

Requer apenas Python 3 (biblioteca padrao). Nao carrega tudo na memoria:
processa em streaming, entao roda em qualquer notebook.
"""
import argparse, csv, io, os, re, sys, unicodedata, zipfile
from collections import Counter, defaultdict

# --- o que queremos -------------------------------------------------------
MUNICIPIOS_ALVO = [
    "LOUVEIRA", "VINHEDO", "VALINHOS", "JUNDIAI", "ITUPEVA", "ITATIBA",
    "JARINU", "CAMPINAS", "CABREUVA", "VARZEA PAULISTA", "CAMPO LIMPO PAULISTA",
    "MORUNGABA", "INDAIATUBA", "ATIBAIA", "HORTOLANDIA", "SUMARE", "PAULINIA",
    "MONTE MOR", "SALTO", "AMERICANA",
]

# Prefixos de CNAE. 41=construcao de edificios, 42=infraestrutura,
# 43=servicos especializados, 7111=arquitetura, 7112=engenharia,
# 7119=topografia/desenho tecnico/pericia
CNAE_PREFIXOS = ("41", "42", "43", "7111", "7112", "7119")

UF_ALVO = "SP"
SO_ATIVAS = True          # situacao cadastral 02 = ativa
SO_MATRIZ = False         # True descarta filiais

# --- layout (posicoes das colunas nos CSV sem cabecalho) ------------------
# ATENCAO: a Receita mudou o layout em jan/2026. Rode 'inspecionar' antes de
# 'extrair' e confira se as posicoes abaixo batem com o que aparece na tela.
EST = dict(cnpj_basico=0, cnpj_ordem=1, cnpj_dv=2, matriz_filial=3, nome_fantasia=4,
           situacao=5, data_situacao=6, data_inicio=10, cnae_principal=11,
           cnae_secundaria=12, tipo_logradouro=13, logradouro=14, numero=15,
           complemento=16, bairro=17, cep=18, uf=19, municipio=20,
           ddd1=21, tel1=22, ddd2=23, tel2=24, email=27)
EMP = dict(cnpj_basico=0, razao_social=1, natureza=2, capital_social=4, porte=5)
SOC = dict(cnpj_basico=0, nome=2, qualificacao=4)
MUN = dict(codigo=0, nome=1)

PORTE = {"01": "Micro (ME)", "03": "Pequeno (EPP)", "05": "Demais"}


def sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").upper().strip()


def zips(d, prefixo):
    """Arquivos .zip cujo nome contem o prefixo (Estabelecimentos, Empresas...)."""
    achados = [os.path.join(d, f) for f in sorted(os.listdir(d))
               if f.lower().endswith(".zip") and prefixo.lower() in f.lower()]
    if not achados:
        sys.exit(f"nenhum zip de '{prefixo}' em {d}\n"
                 f"  encontrados: {sorted(os.listdir(d))[:12]}")
    return achados


def linhas(caminho_zip):
    """Gera as linhas de todos os CSV dentro do zip, ja separadas por ';'."""
    with zipfile.ZipFile(caminho_zip) as z:
        for nome in z.namelist():
            with z.open(nome) as bruto:
                texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
                for campos in csv.reader(texto, delimiter=";", quotechar='"'):
                    yield campos


def carrega_municipios(d):
    """Mapeia codigo da Receita -> nome, e devolve os codigos dos alvos."""
    alvo = {sa(m) for m in MUNICIPIOS_ALVO}
    cod2nome, codigos = {}, set()
    for z in zips(d, "Municipio"):
        for c in linhas(z):
            if len(c) <= MUN["nome"]:
                continue
            cod, nome = c[MUN["codigo"]].strip(), c[MUN["nome"]].strip()
            cod2nome[cod] = nome
            if sa(nome) in alvo:
                codigos.add(cod)
    faltando = alvo - {sa(cod2nome[c]) for c in codigos}
    if faltando:
        print(f"  ! nao encontrei no cadastro: {sorted(faltando)}", file=sys.stderr)
    return cod2nome, codigos


def inspecionar(d):
    """Mostra uma linha de exemplo de cada arquivo para conferir o layout."""
    for prefixo in ("Municipio", "Estabelecimento", "Empresa", "Socio"):
        try:
            z = zips(d, prefixo)[0]
        except SystemExit:
            print(f"\n=== {prefixo}: NAO ENCONTRADO ==="); continue
        print(f"\n=== {prefixo} ({os.path.basename(z)}) ===")
        for i, c in enumerate(linhas(z)):
            for j, v in enumerate(c):
                print(f"  [{j:2d}] {v[:60]}")
            break
    print("\nConfira se as posicoes acima batem com o dicionario EST/EMP no topo "
          "do script. A Receita mudou o layout em jan/2026.")


def extrair(d, saida):
    print("1/4 lendo municipios...")
    cod2nome, codigos = carrega_municipios(d)
    print(f"    {len(codigos)} municipios-alvo localizados")

    print("2/4 varrendo estabelecimentos (a parte demorada)...")
    achados, lidas, motivos = {}, 0, Counter()
    for z in zips(d, "Estabelecimento"):
        print(f"    {os.path.basename(z)}")
        for c in linhas(z):
            lidas += 1
            if lidas % 5_000_000 == 0:
                print(f"      {lidas//1_000_000}M linhas | {len(achados)} achados")
            if len(c) <= EST["email"]:
                continue
            if c[EST["uf"]].strip() != UF_ALVO:
                continue
            if c[EST["municipio"]].strip() not in codigos:
                continue
            cnae = c[EST["cnae_principal"]].strip()
            if not cnae.startswith(CNAE_PREFIXOS):
                motivos["cnae fora"] += 1; continue
            if SO_ATIVAS and c[EST["situacao"]].strip() != "02":
                motivos["nao ativa"] += 1; continue
            if SO_MATRIZ and c[EST["matriz_filial"]].strip() != "1":
                motivos["filial"] += 1; continue

            b = c[EST["cnpj_basico"]].strip()
            ddd, tel = c[EST["ddd1"]].strip(), c[EST["tel1"]].strip()
            achados[b + c[EST["cnpj_ordem"]] + c[EST["cnpj_dv"]]] = {
                "CNPJ": f"{b}/{c[EST['cnpj_ordem']]}-{c[EST['cnpj_dv']]}",
                "CNPJ_Basico": b,
                "Nome_Fantasia": c[EST["nome_fantasia"]].strip(),
                "CNAE_Principal": cnae,
                "Data_Abertura": c[EST["data_inicio"]].strip(),
                "Matriz_Filial": "Matriz" if c[EST["matriz_filial"]].strip() == "1" else "Filial",
                "Municipio": cod2nome.get(c[EST["municipio"]].strip(), ""),
                "Bairro": c[EST["bairro"]].strip(),
                "Logradouro": f"{c[EST['tipo_logradouro']]} {c[EST['logradouro']]}, {c[EST['numero']]}".strip(),
                "CEP": c[EST["cep"]].strip(),
                "Telefone": f"({ddd}) {tel}" if ddd and tel else "",
                "Email": c[EST["email"]].strip().lower(),
            }
    print(f"    {lidas:,} linhas lidas -> {len(achados)} estabelecimentos")
    for k, v in motivos.most_common():
        print(f"      descartados por {k}: {v:,}")

    print("3/4 cruzando com empresas (razao social, capital, porte)...")
    basicos = {r["CNPJ_Basico"] for r in achados.values()}
    emp = {}
    for z in zips(d, "Empresa"):
        for c in linhas(z):
            if len(c) <= EMP["porte"]:
                continue
            b = c[EMP["cnpj_basico"]].strip()
            if b in basicos:
                emp[b] = (c[EMP["razao_social"]].strip(),
                          c[EMP["capital_social"]].strip().replace(",", "."),
                          PORTE.get(c[EMP["porte"]].strip(), c[EMP["porte"]].strip()))
    print(f"    {len(emp)} empresas cruzadas")

    print("4/4 cruzando com socios...")
    soc = defaultdict(list)
    try:
        for z in zips(d, "Socio"):
            for c in linhas(z):
                if len(c) <= SOC["qualificacao"]:
                    continue
                b = c[SOC["cnpj_basico"]].strip()
                if b in basicos:
                    soc[b].append(c[SOC["nome"]].strip())
    except SystemExit:
        print("    (arquivo de socios ausente - seguindo sem ele)")

    COLS = ["CNPJ", "Razao_Social", "Nome_Fantasia", "CNAE_Principal", "Municipio",
            "Bairro", "Logradouro", "CEP", "Telefone", "Email", "Data_Abertura",
            "Capital_Social", "Porte", "Matriz_Filial", "Socios"]
    os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(achados.values(), key=lambda x: (x["Municipio"], x["Nome_Fantasia"])):
            rs, cap, porte = emp.get(r["CNPJ_Basico"], ("", "", ""))
            r.update({"Razao_Social": rs, "Capital_Social": cap, "Porte": porte,
                      "Socios": " | ".join(soc.get(r["CNPJ_Basico"], [])[:5])})
            w.writerow(r)

    print(f"\npronto: {len(achados)} empresas -> {saida}")
    print("com e-mail:", sum(1 for r in achados.values() if r["Email"]))
    print("com telefone:", sum(1 for r in achados.values() if r["Telefone"]))
    print("por municipio:", dict(Counter(r["Municipio"] for r in achados.values()).most_common()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="cmd", required=True)
    i = s.add_parser("inspecionar"); i.add_argument("--dir", required=True)
    e = s.add_parser("extrair")
    e.add_argument("--dir", required=True)
    e.add_argument("--saida", default="dados/receita_filtrado.csv")
    a = ap.parse_args()
    inspecionar(a.dir) if a.cmd == "inspecionar" else extrair(a.dir, a.saida)
