"""Cliente da API do QEdu — enriquece cada município com dados do Censo Escolar.

Fonte: https://api.qedu.org.br (API mantida pela Iede/QEdu, que republica os
microdados do Censo Escolar do INEP). Requer um token de acesso gratuito,
obtido no portal do QEdu. Envie-o via variável de ambiente `QEDU_API_TOKEN`.

Chave de junção com o Querido Diário: o `municipio_id` do QEdu é o
**código IBGE de 7 dígitos** — o mesmo `territory_id` usado na busca de diários.

------------------------------------------------------------------------------
IMPORTANTE (contrato da API)
------------------------------------------------------------------------------
O ambiente de desenvolvimento onde este código foi escrito bloqueia o host do
QEdu por política de rede, então o contrato NÃO pôde ser validado ao vivo.
Os nomes de endpoint, parâmetros e campos de resposta estão centralizados nas
constantes abaixo e o parsing é tolerante a variações. Se algum nome divergir
da documentação oficial (api.qedu.org.br), ajuste apenas estas constantes.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Iterator, Optional

import requests

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Configuração do contrato (ajuste aqui se a doc oficial divergir)
# --------------------------------------------------------------------------- #
BASE_PADRAO = os.environ.get("QEDU_API_BASE", "https://api.qedu.org.br")
ENDPOINT_ESCOLAS = "/v1/escolas"

# Nome do parâmetro de município e da rede/dependência na querystring.
PARAM_MUNICIPIO = "municipio_id"      # código IBGE de 7 dígitos
PARAM_DEPENDENCIA = "dependencia"     # rede administrativa
PARAM_ANO = "ano"
PARAM_PAGE = "page"
PARAM_PER_PAGE = "per_page"

# Códigos de dependência administrativa (padrão INEP): 3 = Municipal.
DEPENDENCIA_MUNICIPAL = 3

# Campos possíveis na resposta (parsing tolerante).
CAMPOS_ID_ESCOLA = ("cod_inep", "codigo_inep", "co_entidade", "id", "escola_id")
CAMPOS_NOME_ESCOLA = ("nome", "no_entidade", "nome_escola", "escola")
CAMPOS_MATRICULAS = (
    "matriculas",
    "num_matriculas",
    "total_matriculas",
    "qt_mat_bas",
    "qtd_matriculas",
)


class ErroQEdu(RuntimeError):
    pass


def _primeiro_campo(d: dict, chaves: tuple[str, ...]):
    for k in chaves:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


@dataclass
class EscolaINEP:
    codigo: str
    nome: str
    matriculas: Optional[int]

    @classmethod
    def de_json(cls, item: dict) -> "EscolaINEP":
        mat = _primeiro_campo(item, CAMPOS_MATRICULAS)
        try:
            mat_int = int(mat) if mat is not None else None
        except (TypeError, ValueError):
            mat_int = None
        return cls(
            codigo=str(_primeiro_campo(item, CAMPOS_ID_ESCOLA) or ""),
            nome=str(_primeiro_campo(item, CAMPOS_NOME_ESCOLA) or ""),
            matriculas=mat_int,
        )


@dataclass
class ResumoINEP:
    """Resumo da rede municipal para um município (chave = código IBGE)."""

    codigo_ibge: str
    ano: Optional[int]
    num_escolas_municipais: int
    num_matriculas_municipais: Optional[int]
    matriculas_disponivel: bool = True
    escolas: list[EscolaINEP] = field(default_factory=list)
    aviso: Optional[str] = None

    def para_dict(self) -> dict:
        return {
            "ano_censo": self.ano,
            "num_escolas_municipais": self.num_escolas_municipais,
            "num_matriculas_municipais": self.num_matriculas_municipais,
            "matriculas_disponivel": self.matriculas_disponivel,
            "aviso_inep": self.aviso,
        }


class ClienteQEdu:
    """Wrapper fino sobre a API do QEdu, com auth Bearer, retry e rate limit."""

    def __init__(
        self,
        token: Optional[str] = None,
        base: str = BASE_PADRAO,
        ano: Optional[int] = None,
        timeout: float = 30.0,
        intervalo_min: float = 0.6,
        max_tentativas: int = 4,
        per_page: int = 100,
        max_paginas: int = 20,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.token = token or os.environ.get("QEDU_API_TOKEN")
        if not self.token:
            raise ErroQEdu(
                "Token do QEdu ausente. Defina a variável de ambiente "
                "QEDU_API_TOKEN ou passe token=... (obtenha em api.qedu.org.br)."
            )
        self.base = base.rstrip("/")
        self.ano = ano
        self.timeout = timeout
        self.intervalo_min = intervalo_min
        self.max_tentativas = max_tentativas
        self.per_page = per_page
        self.max_paginas = max_paginas
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": "raspador-educacao/0.1",
            }
        )
        self._ultimo_request = 0.0

    def _throttle(self) -> None:
        decorrido = time.monotonic() - self._ultimo_request
        if decorrido < self.intervalo_min:
            time.sleep(self.intervalo_min - decorrido)
        self._ultimo_request = time.monotonic()

    def _get(self, path: str, params: dict) -> dict:
        url = self.base + path
        for tentativa in range(1, self.max_tentativas + 1):
            self._throttle()
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                if tentativa == self.max_tentativas:
                    raise ErroQEdu(f"Falha de rede em {url}: {exc}") from exc
                time.sleep(min(2 ** tentativa, 16))
                continue
            if resp.status_code == 401:
                raise ErroQEdu("HTTP 401: token do QEdu inválido ou expirado.")
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(min(2 ** tentativa, 16))
                continue
            if resp.status_code >= 400:
                raise ErroQEdu(f"HTTP {resp.status_code} em {url}: {resp.text[:300]}")
            try:
                return resp.json()
            except ValueError as exc:
                raise ErroQEdu(f"Resposta não-JSON de {url}") from exc
        raise ErroQEdu(f"Esgotadas as tentativas em {url}")

    @staticmethod
    def _itens(payload: dict) -> list[dict]:
        # Aceita tanto paginação estilo Laravel ({data: [...], meta: {...}})
        # quanto lista simples ({escolas: [...]}) ou lista pura.
        if isinstance(payload, list):
            return payload
        for chave in ("data", "escolas", "results", "items"):
            if isinstance(payload.get(chave), list):
                return payload[chave]
        return []

    @staticmethod
    def _ultima_pagina(payload: dict) -> Optional[int]:
        meta = payload.get("meta") if isinstance(payload, dict) else None
        if isinstance(meta, dict):
            for chave in ("last_page", "total_pages", "num_pages"):
                if chave in meta:
                    try:
                        return int(meta[chave])
                    except (TypeError, ValueError):
                        return None
        return None

    def iterar_escolas(
        self, codigo_ibge: str, dependencia: int = DEPENDENCIA_MUNICIPAL
    ) -> Iterator[EscolaINEP]:
        """Itera pelas escolas de um município (paginação automática)."""
        pagina = 1
        while pagina <= self.max_paginas:
            params = {
                PARAM_MUNICIPIO: codigo_ibge,
                PARAM_DEPENDENCIA: dependencia,
                PARAM_PAGE: pagina,
                PARAM_PER_PAGE: self.per_page,
            }
            if self.ano:
                params[PARAM_ANO] = self.ano
            payload = self._get(ENDPOINT_ESCOLAS, params)
            itens = self._itens(payload)
            if not itens:
                break
            for item in itens:
                yield EscolaINEP.de_json(item)
            ultima = self._ultima_pagina(payload)
            if ultima is not None:
                if pagina >= ultima:
                    break
            elif len(itens) < self.per_page:
                break
            pagina += 1

    def resumo_municipio(self, codigo_ibge: str) -> ResumoINEP:
        """Nº de escolas municipais e total de matrículas da rede municipal."""
        escolas = list(self.iterar_escolas(codigo_ibge, DEPENDENCIA_MUNICIPAL))
        num_escolas = len(escolas)
        matriculas_vals = [e.matriculas for e in escolas if e.matriculas is not None]
        matriculas_disponivel = bool(matriculas_vals)
        total_matriculas = sum(matriculas_vals) if matriculas_disponivel else None
        aviso = None
        if num_escolas == 0:
            aviso = "Nenhuma escola municipal retornada pelo QEdu para este município."
        elif not matriculas_disponivel:
            aviso = (
                "Escolas encontradas, mas sem campo de matrículas na resposta "
                "(ajuste CAMPOS_MATRICULAS conforme a doc do QEdu)."
            )
        return ResumoINEP(
            codigo_ibge=codigo_ibge,
            ano=self.ano,
            num_escolas_municipais=num_escolas,
            num_matriculas_municipais=total_matriculas,
            matriculas_disponivel=matriculas_disponivel,
            escolas=escolas,
            aviso=aviso,
        )
