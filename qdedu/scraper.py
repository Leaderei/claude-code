"""Orquestração: enumera municípios da UF e raspa os diários de educação."""
from __future__ import annotations

import logging

from .api import IBGEClient, Municipality, QueridoDiarioClient
from .config import DEFAULT_EDU_QUERY
from .enrich import Enricher, NullEnricher
from .extract import context_around, extract_all
from .http import HttpClient
from .storage import ContactRow, Store

log = logging.getLogger("qdedu.scraper")


def load_cities(store: Store, http: HttpClient, uf: str) -> list[Municipality]:
    """Enumera municípios da UF via IBGE e cacheia no banco."""
    cities = IBGEClient(http).municipalities(uf)
    store.upsert_municipalities([(c.territory_id, c.name, c.uf) for c in cities])
    return cities


def _gazette_to_contacts(g, text: str, muni: Municipality) -> list[ContactRow]:
    """Converte uma extração de um diário em linhas de contato."""
    ex = extract_all(text)
    rows: list[ContactRow] = []
    src = g.txt_url or g.url
    for email in ex.emails:
        rows.append(
            ContactRow(
                territory_id=muni.territory_id,
                kind="email",
                value=email,
                context=context_around(text, email),
                source_url=src,
                gazette_date=g.date,
            )
        )
    for phone in ex.phones:
        rows.append(
            ContactRow(
                territory_id=muni.territory_id,
                kind="phone",
                value=phone,
                context=context_around(text, phone),
                source_url=src,
                gazette_date=g.date,
            )
        )
    for sec in ex.secretaries:
        rows.append(
            ContactRow(
                territory_id=muni.territory_id,
                kind="secretary",
                value=sec.name,
                title=sec.title,
                context=sec.context,
                source_url=src,
                gazette_date=g.date,
            )
        )
    return rows


def scrape_municipality(
    *,
    store: Store,
    http: HttpClient,
    qd: QueridoDiarioClient,
    muni: Municipality,
    querystring: str,
    since: str | None,
    until: str | None,
    max_gazettes: int,
    fetch_full_text: bool,
) -> tuple[int, int]:
    """Raspa um município. Retorna (contatos novos, diários vistos)."""
    new_contacts = 0
    seen = 0
    for g in qd.iter_search(
        territory_ids=[muni.territory_id],
        querystring=querystring,
        published_since=since,
        published_until=until,
        max_results=max_gazettes,
    ):
        seen += 1
        store.add_gazette(g)
        # Texto: usa txt_url (completo) quando possível; senão, os excerpts.
        text = ""
        if fetch_full_text and g.txt_url:
            try:
                text = http.get_text(g.txt_url)
            except Exception as exc:  # diário pode ter txt indisponível
                log.debug("txt indisponível p/ %s: %s", g.txt_url, exc)
        if not text:
            text = "\n".join(g.excerpts)
        if text:
            new_contacts += store.add_contacts(_gazette_to_contacts(g, text, muni))
    store.conn.commit()
    return new_contacts, seen


def scrape_uf(
    *,
    uf: str,
    since: str | None = None,
    until: str | None = None,
    querystring: str = DEFAULT_EDU_QUERY,
    max_gazettes_per_city: int = 20,
    limit_cities: int | None = None,
    fetch_full_text: bool = True,
    resume: bool = True,
    enricher: Enricher | None = None,
    store: Store | None = None,
    http: HttpClient | None = None,
) -> dict:
    """Pipeline principal. Idempotente/resumível por município."""
    owns_store = store is None
    owns_http = http is None
    store = store or Store()
    http = http or HttpClient()
    enricher = enricher or NullEnricher()
    qd = QueridoDiarioClient(http)

    stats = {"cities": 0, "skipped": 0, "gazettes": 0, "contacts": 0, "errors": 0}
    try:
        cities = store.municipalities(uf)
        if not cities:
            load_cities(store, http, uf)
            cities = store.municipalities(uf)
        munis = [Municipality(r["territory_id"], r["name"], r["uf"]) for r in cities]
        if limit_cities:
            munis = munis[:limit_cities]

        for i, muni in enumerate(munis, 1):
            if resume and store.is_done(muni.territory_id):
                stats["skipped"] += 1
                continue
            try:
                contacts, seen = scrape_municipality(
                    store=store,
                    http=http,
                    qd=qd,
                    muni=muni,
                    querystring=querystring,
                    since=since,
                    until=until,
                    max_gazettes=max_gazettes_per_city,
                    fetch_full_text=fetch_full_text,
                )
                # enriquecimento opcional (no-op por padrão)
                er = enricher.enrich(muni)
                if er.contacts:
                    contacts += store.add_contacts(er.contacts)

                store.mark_progress(muni.territory_id, uf, "done", seen)
                stats["cities"] += 1
                stats["gazettes"] += seen
                stats["contacts"] += contacts
                log.info(
                    "[%d/%d] %s/%s: %d diários, +%d contatos",
                    i, len(munis), muni.name, uf, seen, contacts,
                )
            except Exception as exc:  # não derruba a UF inteira por 1 cidade
                stats["errors"] += 1
                store.mark_progress(muni.territory_id, uf, "error", detail=str(exc))
                log.error("Erro em %s/%s: %s", muni.name, uf, exc)
        return stats
    finally:
        if owns_http:
            http.close()
        if owns_store:
            store.close()
