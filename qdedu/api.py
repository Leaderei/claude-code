"""Clientes das APIs externas: Querido Diário e IBGE (localidades)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from .config import settings
from .http import HttpClient

log = logging.getLogger("qdedu.api")


@dataclass
class Municipality:
    territory_id: str  # código IBGE de 7 dígitos
    name: str
    uf: str


@dataclass
class Gazette:
    """Um diário oficial retornado pelo Querido Diário.

    A API teve variações de nomes de campos ao longo do tempo; o parser abaixo
    é tolerante e normaliza para estes atributos.
    """

    territory_id: str
    territory_name: str
    state_code: str
    date: str
    edition: str | None
    is_extra_edition: bool
    url: str | None  # página HTML do diário
    txt_url: str | None  # texto bruto extraído (quando disponível)
    excerpts: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, d: dict) -> "Gazette":
        return cls(
            territory_id=str(d.get("territory_id", "")),
            territory_name=d.get("territory_name", "") or "",
            state_code=d.get("state_code", "") or "",
            date=d.get("date", "") or "",
            edition=(str(d["edition"]) if d.get("edition") is not None else None),
            is_extra_edition=bool(d.get("is_extra_edition", False)),
            url=d.get("url"),
            # campo de texto bruto variou entre 'txt_url' e 'file_raw_txt'
            txt_url=d.get("txt_url") or d.get("file_raw_txt"),
            excerpts=list(d.get("excerpts") or []),
        )


class IBGEClient:
    """Enumeração de municípios por UF via API de localidades do IBGE."""

    def __init__(self, http: HttpClient, base: str | None = None) -> None:
        self._http = http
        self._base = (base or settings.ibge_api_base).rstrip("/")

    def municipalities(self, uf: str) -> list[Municipality]:
        uf = uf.strip().upper()
        url = f"{self._base}/localidades/estados/{uf}/municipios"
        resp = self._http.get(url)
        resp.raise_for_status()
        out: list[Municipality] = []
        for m in resp.json():
            out.append(
                Municipality(territory_id=str(m["id"]), name=m["nome"], uf=uf)
            )
        log.info("IBGE: %d municípios em %s", len(out), uf)
        return out


class QueridoDiarioClient:
    """Cliente do endpoint de busca de diários do Querido Diário."""

    def __init__(self, http: HttpClient, base: str | None = None) -> None:
        self._http = http
        self._base = (base or settings.qd_api_base).rstrip("/")

    def search(
        self,
        *,
        territory_ids: Iterable[str] | None = None,
        querystring: str | None = None,
        published_since: str | None = None,
        published_until: str | None = None,
        size: int = 10,
        offset: int = 0,
        sort_by: str = "descending_date",
        number_of_excerpts: int = 3,
        excerpt_size: int = 500,
    ) -> tuple[int, list[Gazette]]:
        """Uma página de resultados. Retorna (total, gazettes)."""
        params: dict[str, object] = {
            "size": size,
            "offset": offset,
            "sort_by": sort_by,
            "number_of_excerpts": number_of_excerpts,
            "excerpt_size": excerpt_size,
        }
        if querystring:
            params["querystring"] = querystring
        if territory_ids:
            params["territory_ids"] = list(territory_ids)
        if published_since:
            params["published_since"] = published_since
        if published_until:
            params["published_until"] = published_until

        resp = self._http.get(f"{self._base}/gazettes", params=params)
        resp.raise_for_status()
        data = resp.json()
        total = int(data.get("total_gazettes", 0))
        gazettes = [Gazette.from_api(g) for g in data.get("gazettes", [])]
        return total, gazettes

    def iter_search(
        self,
        *,
        territory_ids: Iterable[str] | None = None,
        querystring: str | None = None,
        published_since: str | None = None,
        published_until: str | None = None,
        page_size: int = 50,
        max_results: int | None = None,
        **kwargs,
    ) -> Iterator[Gazette]:
        """Itera resultados paginando automaticamente até max_results."""
        territory_ids = list(territory_ids) if territory_ids else None
        offset = 0
        yielded = 0
        while True:
            total, page = self.search(
                territory_ids=territory_ids,
                querystring=querystring,
                published_since=published_since,
                published_until=published_until,
                size=page_size,
                offset=offset,
                **kwargs,
            )
            if not page:
                break
            for g in page:
                yield g
                yielded += 1
                if max_results is not None and yielded >= max_results:
                    return
            offset += len(page)
            if offset >= total:
                break
