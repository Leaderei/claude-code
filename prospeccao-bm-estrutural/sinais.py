# -*- coding: utf-8 -*-
"""
Extracao de sinais do site — o que decide se o lead presta.

Separado do raspador para poder ser testado sem rede.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Tipologia de obra — o sinal que nenhum filtro de CNAE entrega
# ---------------------------------------------------------------------------
# Peso positivo = obra compativel com laje trelicada (casa, pequeno porte).
# Peso negativo = obra que a BM nao atende bem (predio alto, galpao, infra).

TIPOLOGIA = {
    "casa_terrea": (
        3, ["casa terrea", "casas terreas", "residencia unifamiliar", "casa de campo"]),
    "sobrado": (
        3, ["sobrado", "sobrados", "dois pavimentos", "2 pavimentos"]),
    "condominio_residencial": (
        3, ["condominio residencial", "condominio fechado", "loteamento",
            "casa em condominio", "alto padrao"]),
    "predio_ate_4": (
        2, ["predio residencial", "edificio residencial", "tres pavimentos",
            "3 pavimentos", "quatro pavimentos", "4 pavimentos", "sobreloja"]),
    "reforma": (
        2, ["reforma", "reformas", "ampliacao", "retrofit"]),
    "predio_alto": (
        -3, ["torre residencial", "incorporacao imobiliaria", "empreendimento imobiliario",
             "andares", "torres", "multipavimentos", "edificio comercial de alto padrao"]),
    "industrial": (
        -3, ["galpao", "galpoes", "barracao", "industrial", "logistico",
             "centro de distribuicao", "pre-moldado de grande porte"]),
    "infraestrutura": (
        -3, ["pavimentacao asfaltica", "saneamento", "rodovia", "ponte",
             "obra de arte especial", "terraplenagem de grande porte"]),
    "institucional": (
        -1, ["hospital", "shopping", "aeroporto", "estadio", "presidio"]),
}

# Termos que indicam afinidade direta com o produto da BM Estrutural.
PRODUTO = ["laje trelicada", "lajes trelicadas", "laje pre-moldada", "vigota",
           "trelicada", "laje h", "alvenaria estrutural", "laje nervurada"]

# Paginas que valem a pena buscar, em ordem de prioridade.
CAMINHOS = ["/contato", "/contatos", "/fale-conosco", "/sobre", "/sobre-nos",
            "/quem-somos", "/empresa", "/projetos", "/obras", "/portfolio",
            "/servicos", "/nossos-projetos", "/realizacoes"]

# DDDs brasileiros validos — sem isso o numero do CREA vira "telefone".
DDDS = {11,12,13,14,15,16,17,18,19,21,22,24,27,28,31,32,33,34,35,37,38,
        41,42,43,44,45,46,47,48,49,51,53,54,55,61,62,63,64,65,66,67,68,69,
        71,73,74,75,77,79,81,82,83,84,85,86,87,88,89,
        91,92,93,94,95,96,97,98,99}

RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
RE_TEL = re.compile(r"\(?\b(\d{2})\)?[\s.-]?(9?\d{4})[\s.-]?(\d{4})\b")
RE_CREA = re.compile(r"\b(CREA|CAU)[\s/-]*([A-Z]{2})?[\s:.-]*([\d.\-/]{4,15})", re.I)
RE_INSTA = re.compile(r"(?:instagram\.com/)([A-Za-z0-9_.]{2,30})", re.I)
RE_LINKEDIN = re.compile(r"(?:linkedin\.com/(?:company|in)/)([A-Za-z0-9_.\-]{2,50})", re.I)
RE_WHATS = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\d{10,15})", re.I)

# E-mails de fornecedor de site, nunca do cliente.
EMAIL_LIXO = ("wixpress.com", "sentry.io", "example.com", "godaddy", "squarespace",
              "wordpress.com", "cloudflare", "gstatic", "schema.org", "w3.org")


def normalizar(texto):
    """Minuscula, sem acento — para casar palavra-chave de forma estavel."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t.lower())


def classificar_tipologia(texto):
    """Devolve (tipologia, pontuacao, evidencias). Pontuacao > 0 = compativel."""
    t = normalizar(texto)
    pontos, achados = {}, []
    for nome, (peso, termos) in TIPOLOGIA.items():
        n = sum(t.count(termo) for termo in termos)
        if n:
            pontos[nome] = peso * min(n, 4)
            achados.append(f"{nome}:{n}")
    if not pontos:
        return "Nao identificado", 0, ""
    total = sum(pontos.values())
    # Com saldo positivo o rotulo e a obra compativel de maior peso.
    # Com saldo negativo o rotulo precisa ser o que DESQUALIFICA — dizer
    # "condominio residencial" para uma incorporadora de torres engana a SDR.
    candidatos = {k: v for k, v in pontos.items()
                  if (v > 0 if total > 0 else v < 0)} or pontos
    escolhida = max(candidatos, key=lambda k: abs(candidatos[k]))
    rotulos = {
        "casa_terrea": "Casa terrea", "sobrado": "Sobrado",
        "condominio_residencial": "Condominio residencial",
        "predio_ate_4": "Predio ate 4 pav", "reforma": "Casa terrea",
        "predio_alto": "Predio alto", "industrial": "Industrial",
        "infraestrutura": "Industrial", "institucional": "Comercial",
    }
    return rotulos.get(escolhida, "Nao identificado"), total, " ".join(achados[:6])


def extrair_contatos(texto, html=""):
    """E-mails, telefones, WhatsApp, redes e registro CREA/CAU."""
    emails = []
    for e in RE_EMAIL.findall(texto + " " + html):
        e = e.lower().strip(".")
        if any(x in e for x in EMAIL_LIXO) or e.endswith((".png", ".jpg", ".svg")):
            continue
        if e not in emails:
            emails.append(e)

    crea = ""
    m = RE_CREA.search(texto)
    if m:
        crea = " ".join(p for p in m.groups() if p).strip(" .,;:-/")

    # O registro CREA/CAU e uma sequencia longa de digitos que a regex de
    # telefone casa por acidente. Remove antes de procurar telefone.
    texto_tel = RE_CREA.sub(" ", texto)
    telefones = []
    for ddd, a, b in RE_TEL.findall(texto_tel):
        if int(ddd) not in DDDS:
            continue
        num = f"({ddd}) {a}-{b}"
        if a.startswith("0") or num in telefones:
            continue
        telefones.append(num)

    insta = RE_INSTA.findall(html)
    lkin = RE_LINKEDIN.findall(html)
    whats = RE_WHATS.findall(html)

    return {
        "email_site": emails[0] if emails else "",
        "emails_todos": " | ".join(emails[:4]),
        "telefone_site": telefones[0] if telefones else "",
        "telefones_todos": " | ".join(telefones[:4]),
        "whatsapp": f"+{whats[0]}" if whats else "",
        "instagram": f"https://instagram.com/{insta[0]}" if insta else "",
        "linkedin": f"https://linkedin.com/company/{lkin[0]}" if lkin else "",
        "crea_cau": crea,
    }


def afinidade_produto(texto):
    """Quantas mencoes a laje/pre-moldado o site faz."""
    t = normalizar(texto)
    return sum(t.count(termo) for termo in PRODUTO)


def score_final(score_receita, tipo_pontos, produto, contatos, tem_conteudo):
    """
    Recalcula o score somando o que so o site revela.
    O score da Receita entra com peso 0.5 — cadastro nao prova adequacao.
    """
    s = score_receita * 0.5
    s += max(-25, min(25, tipo_pontos * 5))     # tipologia domina
    s += min(10, produto * 5)                   # cita laje = afinidade direta
    if contatos.get("crea_cau"):
        s += 8                                  # engenharia real, com registro
    if contatos.get("email_site"):
        s += 6
    if contatos.get("whatsapp"):
        s += 6
    if contatos.get("instagram"):
        s += 3
    if not tem_conteudo:
        s -= 10                                 # site vazio ou fora do ar
    return max(0, min(100, round(s)))
