#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspa os sites da base e extrai o que a Receita nao tem:
contato direto, registro CREA/CAU e — o que importa — tipologia de obra.

Uso:
    python raspar_sites.py saida/base_bm_estrutural_2026-08.csv
    python raspar_sites.py base.csv --limite 50        # piloto
    python raspar_sites.py base.csv --concorrencia 8   # padrao: 6

Educado por padrao: respeita robots.txt, 1 requisicao por segundo por
dominio, User-Agent identificado e no maximo 4 paginas por site.
Retomavel — relê o parcial e pula o que ja foi raspado.
"""

import argparse
import asyncio
import csv
import os
import re
import sys
import time
import urllib.parse as up
import urllib.robotparser as rp

import httpx
from selectolax.parser import HTMLParser

import sinais as S

UA = ("Mozilla/5.0 (compatible; LeadereiBot/1.0; prospeccao B2B; "
      "contato: nico@leaderei.com.br)")
MAX_PAGINAS = 4
TIMEOUT = 20.0
POR_DOMINIO = 1.0          # segundos entre requisicoes no mesmo dominio


class Educado:
    """Rate limit por dominio + cache de robots.txt."""

    def __init__(self):
        self.ultimo = {}
        self.robots = {}
        self.trava = asyncio.Lock()

    async def esperar(self, dominio):
        async with self.trava:
            agora = time.monotonic()
            falta = self.ultimo.get(dominio, 0) + POR_DOMINIO - agora
            self.ultimo[dominio] = agora + max(0, falta)
        if falta > 0:
            await asyncio.sleep(falta)

    async def permitido(self, cliente, url):
        base = f"{up.urlsplit(url).scheme}://{up.urlsplit(url).netloc}"
        if base not in self.robots:
            leitor = rp.RobotFileParser()
            try:
                r = await cliente.get(base + "/robots.txt", timeout=8.0)
                leitor.parse(r.text.splitlines() if r.status_code == 200 else [])
            except Exception:
                leitor.parse([])          # sem robots.txt = liberado
            self.robots[base] = leitor
        try:
            return self.robots[base].can_fetch(UA, url)
        except Exception:
            return True


def texto_visivel(html):
    """Texto da pagina sem script/style/nav."""
    try:
        arvore = HTMLParser(html)
    except Exception:
        return "", None
    for tag in ("script", "style", "noscript", "svg"):
        for no in arvore.css(tag):
            no.decompose()
    corpo = arvore.body or arvore.root
    return (corpo.text(separator=" ", strip=True) if corpo else ""), arvore


def links_internos(arvore, base):
    """Links do mesmo dominio que valem visita, em ordem de prioridade."""
    if arvore is None:
        return []
    host = up.urlsplit(base).netloc.lower().replace("www.", "")
    achados, vistos = [], set()
    for a in arvore.css("a[href]"):
        href = (a.attributes.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = up.urljoin(base, href)
        partes = up.urlsplit(url)
        if partes.scheme not in ("http", "https"):
            continue
        if partes.netloc.lower().replace("www.", "") != host:
            continue
        limpa = up.urlunsplit((partes.scheme, partes.netloc,
                               partes.path.rstrip("/") or "/", "", ""))
        if limpa in vistos:
            continue
        vistos.add(limpa)
        # Sites reais usam /contato, /contato.html, /contato.php, /contato/.
        # Sem tirar a extensao, nenhum deles casa.
        caminho = re.sub(r"\.(html?|php|aspx?|jsp)$", "",
                         partes.path.lower().rstrip("/"))
        prioridade = next((i for i, c in enumerate(S.CAMINHOS)
                           if caminho.endswith(c)), 99)
        if prioridade == 99:
            # Fallback: o texto do link, para URLs opacas (/p/12, /pagina?id=3)
            rotulo = S.normalizar(a.text(strip=True) or "")
            prioridade = next((50 + i for i, c in enumerate(S.CAMINHOS)
                               if c.strip("/").replace("-", " ") in rotulo), 99)
        achados.append((prioridade, limpa))
    achados.sort()
    return [u for p, u in achados if p < 99][:MAX_PAGINAS - 1]


async def raspar_um(cliente, educado, reg, sem):
    """Raspa um site e devolve o registro enriquecido."""
    site = (reg.get("site") or "").strip()
    saida = dict(reg)
    saida.update({"site_status": "", "paginas_lidas": "0", "evidencia": ""})

    if not site:
        saida["site_status"] = "sem site"
        saida["score_final"] = S.score_final(
            int(reg.get("score") or 0), 0, 0, {}, False)
        return saida

    if not site.startswith("http"):
        site = "https://" + site

    async with sem:
        dominio = up.urlsplit(site).netloc
        textos, htmls, lidas = [], [], 0
        try:
            if not await educado.permitido(cliente, site):
                saida["site_status"] = "bloqueado por robots.txt"
                saida["score_final"] = S.score_final(
                    int(reg.get("score") or 0), 0, 0, {}, False)
                return saida

            await educado.esperar(dominio)
            r = await cliente.get(site)
            if r.status_code >= 400:
                saida["site_status"] = f"HTTP {r.status_code}"
                saida["score_final"] = S.score_final(
                    int(reg.get("score") or 0), 0, 0, {}, False)
                return saida

            txt, arvore = texto_visivel(r.text)
            textos.append(txt)
            htmls.append(r.text)
            lidas = 1

            for url in links_internos(arvore, str(r.url)):
                if not await educado.permitido(cliente, url):
                    continue
                await educado.esperar(dominio)
                try:
                    r2 = await cliente.get(url)
                    if r2.status_code < 400:
                        t2, _ = texto_visivel(r2.text)
                        textos.append(t2)
                        htmls.append(r2.text)
                        lidas += 1
                except Exception:
                    continue

            saida["site_status"] = "ok"
        except httpx.TimeoutException:
            saida["site_status"] = "timeout"
        except Exception as e:
            saida["site_status"] = type(e).__name__

    texto = " ".join(textos)
    html = " ".join(htmls)
    contatos = S.extrair_contatos(texto, html)
    tipo, pontos, evid = S.classificar_tipologia(texto)
    produto = S.afinidade_produto(texto)

    saida.update(contatos)
    saida["tipologia_obra"] = tipo
    saida["mencoes_laje"] = str(produto)
    saida["paginas_lidas"] = str(lidas)
    saida["evidencia"] = evid
    saida["score_final"] = S.score_final(
        int(reg.get("score") or 0), pontos, produto, contatos, bool(texto.strip()))
    # o e-mail do site e melhor que o da Receita quando existe
    if contatos["email_site"] and not saida.get("email"):
        saida["email"] = contatos["email_site"]
    if contatos["instagram"]:
        saida["instagram"] = contatos["instagram"]
    return saida


async def executar(regs, concorrencia):
    educado = Educado()
    sem = asyncio.Semaphore(concorrencia)
    limites = httpx.Limits(max_connections=concorrencia * 2,
                           max_keepalive_connections=concorrencia)
    async with httpx.AsyncClient(
            headers={"User-Agent": UA,
                     "Accept-Language": "pt-BR,pt;q=0.9"},
            timeout=TIMEOUT, follow_redirects=True, limits=limites,
            verify=True) as cliente:
        tarefas = [raspar_um(cliente, educado, r, sem) for r in regs]
        feitos = []
        for n, coro in enumerate(asyncio.as_completed(tarefas), 1):
            feitos.append(await coro)
            if n % 10 == 0 or n == len(tarefas):
                print(f"\r  {n}/{len(tarefas)} sites", end="", flush=True)
        print()
        return feitos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="base gerada por gerar_base.py")
    ap.add_argument("--limite", type=int, help="raspar so os N primeiros (piloto)")
    ap.add_argument("--concorrencia", type=int, default=6)
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        sys.exit(f"CSV nao encontrado: {args.csv}")
    regs = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))

    destino = args.csv.replace(".csv", "_raspado.csv")
    ja = {}
    if os.path.exists(destino):
        ja = {r["cnpj"]: r for r in
              csv.DictReader(open(destino, encoding="utf-8-sig"))}
        print(f"Retomando: {len(ja):,} ja raspados em {destino}")

    pendentes = [r for r in regs if r["cnpj"] not in ja]
    if args.limite:
        pendentes = pendentes[:args.limite]

    com_site = sum(1 for r in pendentes if (r.get("site") or "").strip())
    print(f"{len(pendentes):,} a raspar ({com_site:,} com site) | "
          f"concorrencia {args.concorrencia}")
    if not pendentes:
        print("Nada a fazer.")
        return

    inicio = time.time()
    feitos = asyncio.run(executar(pendentes, args.concorrencia))
    for r in feitos:
        ja[r["cnpj"]] = r

    linhas = list(ja.values())
    extras = ["site_status", "paginas_lidas", "email_site", "emails_todos",
              "telefone_site", "telefones_todos", "whatsapp", "linkedin",
              "crea_cau", "mencoes_laje", "score_final", "evidencia"]
    colunas = list(regs[0].keys()) + [c for c in extras if c not in regs[0]]
    linhas.sort(key=lambda r: -int(r.get("score_final") or 0))
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    ok = sum(1 for r in feitos if r.get("site_status") == "ok")
    ident = sum(1 for r in linhas if r.get("tipologia_obra")
                not in ("", "Nao identificado"))
    compat = sum(1 for r in linhas if r.get("tipologia_obra") in
                 ("Casa terrea", "Sobrado", "Condominio residencial",
                  "Predio ate 4 pav"))
    print(f"\n  Raspados com sucesso : {ok:,}/{len(feitos):,}")
    print(f"  Tipologia identificada: {ident:,}/{len(linhas):,}")
    print(f"  Compativeis com laje  : {compat:,}")
    print(f"  Tempo                 : {time.time()-inicio:.0f}s")
    print(f"\n  Saida: {destino}")


if __name__ == "__main__":
    main()
