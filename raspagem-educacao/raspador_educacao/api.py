"""Cliente HTTP para a API pública do Querido Diário.

Documentação: https://api.queridodiario.ok.org.br/docs
Endpoints usados:
    GET /cities            -> resolve nome do município em código IBGE (territory_id)
    GET /cities/{id}       -> detalhes de um município
    GET /gazettes          -> busca em texto completo nos diários oficiais

A API não exige autenticação. Ela é mantida pela Open Knowledge Brasil; use
com parcimônia (respeite o rate limit configurado abaixo).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

import requests

logger = logging.getLogger(__name__)

# A API responde nos dois hosts; o segundo é usado como fallback automático.
BASES_PADRAO = (
    "https://queridodiario.ok.org.br/api",
    "https://api.queridodiario.ok.org.br",
)

USER_AGENT = (
    "raspador-educacao/0.1 (+prospeccao secretarias municipais; contato via operador)"
)


class ErroAPI(RuntimeError):
    """Erro ao consultar a API do Querido Diário."""


@dataclass
class Diario:
    """Um diário oficial retornado pela busca."""

    territory_id: str
    territory_name: str
    state_code: str
    date: str
    url: str
    txt_url: Optional[str]
    edition: Optional[str]
    is_extra_edition: bool
    excerpts: list[str] = field(default_factory=list)

    @classmethod
    def de_json(cls, item: dict) -> "Diario":
        # A API já expôs `txt_url` em versões recentes; quando ausente,
        # derivamos a partir da URL do arquivo original (.pdf -> .txt).
        txt_url = item.get("txt_url")
        url = item.get("url", "")
        if not txt_url and url.lower().endswith(".pdf"):
            txt_url = url[:-4] + ".txt"
        return cls(
            territory_id=str(item.get("territory_id", "")),
            territory_name=item.get("territory_name", ""),
            state_code=item.get("state_code", ""),
            date=item.get("date", ""),
            url=url,
            txt_url=txt_url,
            edition=item.get("edition"),
            is_extra_edition=bool(item.get("is_extra_edition", False)),
            excerpts=list(item.get("excerpts") or item.get("highlight_texts") or []),
        )


@dataclass
class Municipio:
    territory_id: str
    territory_name: str
    state_code: str

    @classmethod
    def de_json(cls, item: dict) -> "Municipio":
        return cls(
            territory_id=str(item.get("territory_id", "")),
            territory_name=item.get("territory_name", item.get("name", "")),
            state_code=item.get("state_code", item.get("uf", "")),
        )


class ClienteQueridoDiario:
    """Wrapper fino sobre a API, com retry, rate limit e paginação."""

    def __init__(
        self,
        bases: Iterable[str] = BASES_PADRAO,
        timeout: float = 30.0,
        intervalo_min: float = 0.6,
        max_tentativas: int = 4,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.bases = list(bases)
        self.timeout = timeout
        self.intervalo_min = intervalo_min
        self.max_tentativas = max_tentativas
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self._ultimo_request = 0.0

    # ------------------------------------------------------------------ #
    # Infra
    # ------------------------------------------------------------------ #
    def _throttle(self) -> None:
        decorrido = time.monotonic() - self._ultimo_request
        if decorrido < self.intervalo_min:
            time.sleep(self.intervalo_min - decorrido)
        self._ultimo_request = time.monotonic()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        ultimo_erro: Optional[Exception] = None
        for base in self.bases:
            url = base.rstrip("/") + path
            for tentativa in range(1, self.max_tentativas + 1):
                self._throttle()
                try:
                    resp = self.session.get(url, params=params, timeout=self.timeout)
                except requests.RequestException as exc:  # rede
                    ultimo_erro = exc
                    espera = min(2 ** tentativa, 16)
                    logger.warning("Falha de rede em %s (tentativa %d): %s", url, tentativa, exc)
                    time.sleep(espera)
                    continue

                if resp.status_code == 429 or resp.status_code >= 500:
                    espera = min(2 ** tentativa, 16)
                    logger.warning(
                        "HTTP %s em %s; aguardando %ds", resp.status_code, url, espera
                    )
                    time.sleep(espera)
                    ultimo_erro = ErroAPI(f"HTTP {resp.status_code} em {url}")
                    continue

                if resp.status_code >= 400:
                    raise ErroAPI(f"HTTP {resp.status_code} em {url}: {resp.text[:300]}")

                try:
                    return resp.json()
                except ValueError as exc:
                    raise ErroAPI(f"Resposta não-JSON de {url}") from exc

            logger.warning("Base %s esgotou tentativas; tentando próxima base.", base)

        raise ErroAPI(f"Todas as bases falharam em {path}") from ultimo_erro

    def baixar_texto(self, txt_url: str) -> str:
        """Baixa o texto plano de um diário. Retorna string vazia em falha."""
        for tentativa in range(1, self.max_tentativas + 1):
            self._throttle()
            try:
                resp = self.session.get(txt_url, timeout=self.timeout)
                if resp.status_code == 200:
                    resp.encoding = resp.encoding or "utf-8"
                    return resp.text
                if resp.status_code == 404:
                    return ""
                time.sleep(min(2 ** tentativa, 16))
            except requests.RequestException as exc:
                logger.warning("Falha ao baixar %s: %s", txt_url, exc)
                time.sleep(min(2 ** tentativa, 16))
        return ""

    # ------------------------------------------------------------------ #
    # Endpoints
    # ------------------------------------------------------------------ #
    def buscar_municipios(self, nome: str) -> list[Municipio]:
        """GET /cities?city_name=... — resolve nome em código IBGE."""
        dados = self._get("/cities", params={"city_name": nome})
        itens = dados.get("cities") or dados.get("territories") or []
        return [Municipio.de_json(i) for i in itens]

    def detalhar_municipio(self, territory_id: str) -> Optional[Municipio]:
        try:
            dados = self._get(f"/cities/{territory_id}")
        except ErroAPI:
            return None
        item = dados.get("city") or dados.get("territory") or dados
        if not item:
            return None
        return Municipio.de_json(item)

    def buscar_diarios(
        self,
        territory_ids: Iterable[str],
        querystring: Optional[str] = None,
        published_since: Optional[str] = None,
        published_until: Optional[str] = None,
        size: int = 50,
        max_resultados: int = 300,
        sort_by: str = "descending_date",
        excerpt_size: int = 500,
        number_of_excerpts: int = 3,
    ) -> Iterator[Diario]:
        """GET /gazettes — itera pelos diários (paginação automática via offset).

        `querystring` aceita frases entre aspas, ex.: '"secretaria municipal de educação"'.
        `sort_by` ∈ {relevance, descending_date, ascending_date}.
        """
        offset = 0
        emitidos = 0
        while emitidos < max_resultados:
            params: dict = {
                "size": min(size, max_resultados - emitidos),
                "offset": offset,
                "sort_by": sort_by,
                "excerpt_size": excerpt_size,
                "number_of_excerpts": number_of_excerpts,
            }
            # `territory_ids` é repetível; requests serializa listas nesse formato.
            params["territory_ids"] = list(territory_ids)
            if querystring:
                params["querystring"] = querystring
            if published_since:
                params["published_since"] = published_since
            if published_until:
                params["published_until"] = published_until

            dados = self._get("/gazettes", params=params)
            itens = dados.get("gazettes") or []
            if not itens:
                break
            for item in itens:
                yield Diario.de_json(item)
                emitidos += 1
                if emitidos >= max_resultados:
                    break

            total = int(dados.get("total_gazettes", 0))
            offset += len(itens)
            if offset >= total or len(itens) < params["size"]:
                break
