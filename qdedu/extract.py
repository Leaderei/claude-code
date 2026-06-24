"""Extração de e-mails, telefones e prováveis nomes do secretário de educação.

Tudo opera sobre o texto bruto dos diários. É heurístico por natureza — o texto
de diário oficial é ruidoso — então cada item carrega um trecho de contexto
para permitir revisão manual antes da prospecção.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# E-mails
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

# Domínios genéricos que raramente são o contato real da prefeitura.
_EMAIL_NOISE = ("example.", "sentry.", "@2x", "wixpress", "godaddy")


def extract_emails(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for m in EMAIL_RE.finditer(text):
        email = m.group(0).strip(".").lower()
        if any(n in email for n in _EMAIL_NOISE):
            continue
        if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            continue
        seen.setdefault(email, None)
    return list(seen)


# ---------------------------------------------------------------------------
# Telefones (formatos brasileiros)
# ---------------------------------------------------------------------------
# Aceita: (11) 1234-5678, 11 91234-5678, +55 11 1234 5678, 0800 123 4567
PHONE_RE = re.compile(
    r"""
    (?<![\d/])                              # não no meio de número/data
    (?:\+?55[\s.\-]?)?                       # DDI opcional
    (?:
        (?:\(?0?(?P<ddd>[1-9][0-9])\)?[\s.\-]?)?  # DDD opcional
        (?P<num>9?\d{4}[\s.\-]?\d{4})              # 8 ou 9 dígitos
        |
        0800[\s.\-]?\d{3}[\s.\-]?\d{4}             # 0800
    )
    (?![\d/])
    """,
    re.VERBOSE,
)


def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def normalize_phone(raw: str) -> str | None:
    """Normaliza para dígitos; descarta o que claramente não é telefone."""
    d = _only_digits(raw)
    if d.startswith("55") and len(d) > 11:
        d = d[2:]
    if d.startswith("0800"):
        return d if len(d) == 11 else None
    # fixo (10) ou móvel (11) com DDD; ou 8/9 dígitos sem DDD
    if len(d) in (10, 11):
        return d
    if len(d) in (8, 9):
        return d
    return None


def extract_phones(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for m in PHONE_RE.finditer(text):
        norm = normalize_phone(m.group(0))
        if norm:
            seen.setdefault(norm, None)
    return list(seen)


# ---------------------------------------------------------------------------
# Nome / cargo do(a) secretário(a) de educação
# ---------------------------------------------------------------------------
def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


# "Fulano de Tal, Secretário Municipal de Educação" ou
# "Secretária Municipal de Educação, Fulana de Tal"
_NAME = r"[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ý][a-zà-ÿ]+){1,4}"
_TITLE = r"secretári[oa]\s+(?:municipal\s+)?(?:d[ae]\s+)?educa[cç][aã]o"

NAME_BEFORE_RE = re.compile(
    rf"(?P<name>{_NAME})\s*[,\-–—]?\s*(?P<title>{_TITLE})", re.IGNORECASE
)
NAME_AFTER_RE = re.compile(
    rf"(?P<title>{_TITLE})\s*[,\-–—:]?\s*(?P<name>{_NAME})", re.IGNORECASE
)


# Palavras que frequentemente antecedem o nome em portarias/diários e que o
# regex de nome captura por engano. São removidas do início do nome.
_LEADING_NOISE = {
    "nomeia", "nomear", "nomeio", "designa", "designar", "exonera", "exonerar",
    "senhora", "senhor", "sra", "sr", "prof", "professor", "professora",
    "dr", "dra", "ilustrissimo", "ilustrissima", "excelentissimo",
}


def _trim_leading_noise(name: str) -> str:
    parts = name.split()
    while parts and _strip_accents(parts[0]).lower().strip(".") in _LEADING_NOISE:
        parts.pop(0)
    return " ".join(parts)


@dataclass
class SecretaryMention:
    name: str
    title: str
    context: str


def extract_secretary(text: str, context_chars: int = 120) -> list[SecretaryMention]:
    out: list[SecretaryMention] = []
    seen: set[str] = set()
    for rx in (NAME_BEFORE_RE, NAME_AFTER_RE):
        for m in rx.finditer(text):
            name = _trim_leading_noise(" ".join(m.group("name").split()))
            # filtra falsos positivos óbvios (ex.: "Secretaria De Educacao")
            if not name or _strip_accents(name).lower().startswith(
                ("secretari", "municip")
            ):
                continue
            key = _strip_accents(name).lower()
            if key in seen:
                continue
            seen.add(key)
            start = max(0, m.start() - context_chars)
            end = min(len(text), m.end() + context_chars)
            out.append(
                SecretaryMention(
                    name=name,
                    title=" ".join(m.group("title").split()),
                    context=" ".join(text[start:end].split()),
                )
            )
    return out


# ---------------------------------------------------------------------------
# Snippet de contexto em torno de um e-mail/telefone (para revisão)
# ---------------------------------------------------------------------------
def context_around(text: str, needle: str, width: int = 80) -> str:
    idx = text.find(needle)
    if idx < 0:
        # telefones são normalizados; tenta achar pelos primeiros dígitos
        digits = _only_digits(needle)[:4]
        if digits:
            idx = text.find(digits)
    if idx < 0:
        return ""
    start = max(0, idx - width)
    end = min(len(text), idx + len(needle) + width)
    return " ".join(text[start:end].split())


@dataclass
class Extraction:
    emails: list[str]
    phones: list[str]
    secretaries: list[SecretaryMention]


def extract_all(text: str) -> Extraction:
    return Extraction(
        emails=extract_emails(text),
        phones=extract_phones(text),
        secretaries=extract_secretary(text),
    )
