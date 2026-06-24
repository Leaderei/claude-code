"""Enriquecimento de contatos a partir de fontes externas (pluggável).

O Querido Diário fornece texto de diários, não contatos atualizados. Este
módulo complementa com o **site oficial da prefeitura**: descobre o domínio do
município, baixa páginas de contato/educação e extrai e-mail/telefone
institucionais — preferindo dados ligados à Secretaria de Educação.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urljoin, urlparse

from .api import CitiesClient, Municipality
from .extract import context_around, extract_emails, extract_phones, normalize_phone
from .http import HttpClient
from .storage import ContactRow

log = logging.getLogger("qdedu.enrich")


@dataclass
class EnrichmentResult:
    contacts: list[ContactRow]
    notes: str = ""


class Enricher(Protocol):
    """Implemente para adicionar uma fonte de contatos atualizada."""

    name: str

    def enrich(self, muni: Municipality) -> EnrichmentResult: ...


class NullEnricher:
    """Enricher padrão (no-op)."""

    name = "null"

    def enrich(self, muni: Municipality) -> EnrichmentResult:  # noqa: ARG002
        return EnrichmentResult(contacts=[], notes="sem enriquecimento")


# ---------------------------------------------------------------------------
# Utilidades de HTML
# ---------------------------------------------------------------------------
class _TextExtractor(HTMLParser):
    """Converte HTML em texto e coleta hrefs de mailto:/tel: (mais confiáveis)."""

    _SKIP = {"script", "style", "noscript", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self.mailtos: list[str] = []
        self.tels: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            low = href.lower()
            if low.startswith("mailto:"):
                self.mailtos.append(href[7:].split("?")[0].strip())
            elif low.startswith("tel:"):
                self.tels.append(href[4:].strip())

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self.chunks.append(data)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.chunks).split())


def html_to_text(html: str) -> _TextExtractor:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:  # HTML malformado não deve quebrar o pipeline
        pass
    return p


# ---------------------------------------------------------------------------
# Enricher de site da prefeitura
# ---------------------------------------------------------------------------
# Caminhos comuns onde prefeituras publicam contato da Secretaria de Educação.
DEFAULT_PATHS = (
    "",
    "/contato",
    "/fale-conosco",
    "/educacao",
    "/secretaria-de-educacao",
    "/secretaria-municipal-de-educacao",
    "/secretarias/educacao",
)

_EDU_HINT = re.compile(r"educa[cç][aã]o", re.IGNORECASE)
_PLATFORM_NOISE = ("diariomunicipal", "dom.", "imprensaoficial", "doe.", "jusbrasil")


@dataclass
class SitePrefeituraEnricher:
    """Extrai contatos da Secretaria de Educação no site oficial do município.

    Descoberta do domínio (em ordem):
      1. `domain_map[territory_id]` (mapa curado, mais confiável);
      2. `publication_urls` do Querido Diário (`/cities/{id}`), filtrando
         plataformas de terceiros.
    Depois baixa `DEFAULT_PATHS` em cada domínio e extrai e-mails/telefones,
    priorizando os ligados a "educação".
    """

    http: HttpClient
    cities: CitiesClient | None = None
    domain_map: dict[str, str] = field(default_factory=dict)
    paths: tuple[str, ...] = DEFAULT_PATHS
    max_pages: int = 6
    name: str = "site_prefeitura"

    def _candidate_bases(self, muni: Municipality) -> list[str]:
        bases: list[str] = []
        mapped = self.domain_map.get(muni.territory_id)
        if mapped:
            bases.append(mapped.rstrip("/"))
        if self.cities is not None:
            try:
                city = self.cities.get(muni.territory_id)
            except Exception as exc:  # /cities pode falhar isoladamente
                log.debug("/cities falhou p/ %s: %s", muni.territory_id, exc)
                city = None
            for url in (city.publication_urls if city else []):
                host = urlparse(url if "://" in url else f"http://{url}").netloc
                if not host or any(n in host.lower() for n in _PLATFORM_NOISE):
                    continue
                base = f"https://{host}"
                if base not in bases:
                    bases.append(base)
        return bases

    def enrich(self, muni: Municipality) -> EnrichmentResult:
        bases = self._candidate_bases(muni)
        if not bases:
            return EnrichmentResult(contacts=[], notes="domínio não descoberto")

        rows: list[ContactRow] = []
        seen: set[tuple[str, str]] = set()
        fetched = 0
        for base in bases:
            for path in self.paths:
                if fetched >= self.max_pages:
                    break
                url = urljoin(base + "/", path.lstrip("/"))
                try:
                    html = self.http.get_text(url)
                except Exception as exc:
                    log.debug("GET %s falhou: %s", url, exc)
                    continue
                fetched += 1
                rows.extend(self._extract_page(muni, url, html, seen))
        notes = f"{fetched} páginas, {len(rows)} contatos" if rows else "nada encontrado"
        return EnrichmentResult(contacts=rows, notes=notes)

    def _extract_page(self, muni, url, html, seen) -> list[ContactRow]:
        parsed = html_to_text(html)
        text = parsed.text
        page_is_edu = bool(_EDU_HINT.search(url) or _EDU_HINT.search(text))
        rows: list[ContactRow] = []

        # e-mails: dos hrefs mailto: (confiáveis) + varredura do texto
        emails = list(dict.fromkeys(parsed.mailtos + extract_emails(text)))
        for email in emails:
            email = email.lower().strip()
            if not email or ("email", email) in seen:
                continue
            seen.add(("email", email))
            # prioriza e-mail institucional/educacional
            edu = "educ" in email.split("@")[0] or page_is_edu
            rows.append(
                ContactRow(
                    territory_id=muni.territory_id,
                    kind="email",
                    value=email,
                    title="educação" if edu else None,
                    context=context_around(text, email) or url,
                    source_url=url,
                    source=self.name,
                )
            )

        # telefones: dos hrefs tel: + varredura do texto
        phones = [p for p in (normalize_phone(t) for t in parsed.tels) if p]
        phones = list(dict.fromkeys(phones + extract_phones(text)))
        for phone in phones:
            if ("phone", phone) in seen:
                continue
            seen.add(("phone", phone))
            rows.append(
                ContactRow(
                    territory_id=muni.territory_id,
                    kind="phone",
                    value=phone,
                    title="educação" if page_is_edu else None,
                    context=context_around(text, phone) or url,
                    source_url=url,
                    source=self.name,
                )
            )
        return rows
