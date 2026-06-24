"""Interface de linha de comando do qdedu."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys

from .api import CitiesClient
from .config import DEFAULT_EDU_QUERY, settings
from .enrich import NullEnricher, SitePrefeituraEnricher
from .http import HttpClient
from .scraper import load_cities, scrape_uf
from .storage import open_store


def _load_domain_map(path: str | None) -> dict[str, str]:
    """Lê um mapa territory_id->url (JSON {id:url} ou CSV id,url)."""
    if not path:
        return {}
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            return {str(k): v for k, v in json.load(fh).items()}
    out: dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) >= 2 and row[0].strip().isdigit():
                out[row[0].strip()] = row[1].strip()
    return out


def _build_enricher(args, http: HttpClient):
    if args.enrich == "site":
        return SitePrefeituraEnricher(
            http=http,
            cities=CitiesClient(http),
            domain_map=_load_domain_map(args.domain_map),
        )
    return NullEnricher()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_cities(args: argparse.Namespace) -> int:
    with open_store(args.db) as store, HttpClient() as http:
        cities = load_cities(store, http, args.uf)
    print(f"{len(cities)} municípios cacheados para {args.uf.upper()}.")
    return 0


def cmd_scrape(args: argparse.Namespace) -> int:
    with open_store(args.db) as store, HttpClient() as http:
        stats = scrape_uf(
            uf=args.uf,
            since=args.since,
            until=args.until,
            querystring=args.query,
            max_gazettes_per_city=args.max_gazettes,
            limit_cities=args.limit,
            fetch_full_text=not args.excerpts_only,
            resume=not args.no_resume,
            enricher=_build_enricher(args, http),
            store=store,
            http=http,
        )
    print(
        "Concluído: "
        f"{stats['cities']} cidades, {stats['skipped']} puladas, "
        f"{stats['gazettes']} diários, {stats['contacts']} contatos novos, "
        f"{stats['errors']} erros."
    )
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    with open_store(args.db) as store:
        n = store.export_csv(args.uf, args.out)
    print(f"{n} linhas exportadas para {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qdedu",
        description="Raspagem de Secretarias Municipais de Educação (Querido Diário).",
    )
    p.add_argument("--db", default=settings.db_path, help="Caminho do SQLite")
    p.add_argument("-v", "--verbose", action="store_true", help="Log detalhado")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("cities", help="Enumera/cacheia municípios da UF (via IBGE)")
    c.add_argument("--uf", required=True, help="Sigla da UF (ex.: SP)")
    c.set_defaults(func=cmd_cities)

    s = sub.add_parser("scrape", help="Raspa diários de educação da UF")
    s.add_argument("--uf", required=True, help="Sigla da UF (ex.: SP)")
    s.add_argument("--since", help="published_since (YYYY-MM-DD)")
    s.add_argument("--until", help="published_until (YYYY-MM-DD)")
    s.add_argument("--query", default=DEFAULT_EDU_QUERY, help="querystring de busca")
    s.add_argument(
        "--max-gazettes", type=int, default=20, dest="max_gazettes",
        help="Máx. de diários por município",
    )
    s.add_argument(
        "--limit", type=int, default=None, help="Limita nº de cidades (teste)"
    )
    s.add_argument(
        "--excerpts-only", action="store_true", dest="excerpts_only",
        help="Não baixa txt completo; usa só os excerpts (mais rápido)",
    )
    s.add_argument(
        "--no-resume", action="store_true", dest="no_resume",
        help="Reprocessa cidades já marcadas como concluídas",
    )
    s.add_argument(
        "--enrich", choices=("none", "site"), default="none",
        help="Fonte de enriquecimento de contatos (site = site da prefeitura)",
    )
    s.add_argument(
        "--domain-map", dest="domain_map", default=None,
        help="Arquivo id->url (JSON ou CSV) com domínios oficiais por município",
    )
    s.set_defaults(func=cmd_scrape)

    e = sub.add_parser("export", help="Exporta contatos da UF para CSV")
    e.add_argument("--uf", required=True, help="Sigla da UF (ex.: SP)")
    e.add_argument("--out", required=True, help="Arquivo CSV de saída")
    e.set_defaults(func=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(getattr(args, "verbose", False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
