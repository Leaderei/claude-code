"""Orquestra a raspagem: resolve município, busca diários, extrai contatos."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from .api import ClienteQueridoDiario, Diario, Municipio
from .extracao import Contato, agregar_contatos, extrair_contatos
from .qedu import ClienteQEdu, ErroQEdu, ResumoINEP
from .secretarios import (
    AtoSecretario,
    Secretario,
    associar_contato,
    consolidar_secretario,
    extrair_atos,
)

logger = logging.getLogger(__name__)

# Consulta padrão: frases entre aspas fazem busca por expressão exata na API.
# Inclui o cargo no masculino/feminino para captar também os atos de nomeação.
QUERY_EDUCACAO = (
    '"secretaria municipal de educacao" OR "secretaria de educacao" '
    'OR "secretaria municipal da educacao" '
    'OR "secretario municipal de educacao" OR "secretaria municipal de educacao"'
)


@dataclass
class ResultadoMunicipio:
    municipio: Municipio
    total_diarios: int
    diarios_analisados: int
    contatos: list[Contato] = field(default_factory=list)
    aviso: Optional[str] = None
    inep: Optional[ResumoINEP] = None  # enriquecimento QEdu/Censo Escolar
    secretario: Optional[Secretario] = None  # titular atual do cargo

    def emails(self) -> list[Contato]:
        return [c for c in self.contatos if c.tipo == "email"]

    def telefones(self) -> list[Contato]:
        return [c for c in self.contatos if c.tipo == "telefone"]

    def para_dict(self) -> dict:
        d = {
            "territory_id": self.municipio.territory_id,
            "municipio": self.municipio.territory_name,
            "uf": self.municipio.state_code,
            "total_diarios": self.total_diarios,
            "diarios_analisados": self.diarios_analisados,
            "aviso": self.aviso,
            "emails": [c.para_dict() for c in self.emails()],
            "telefones": [c.para_dict() for c in self.telefones()],
        }
        if self.inep is not None:
            d["inep"] = self.inep.para_dict()
        if self.secretario is not None:
            d["secretario"] = self.secretario.para_dict()
        return d


def resolver_municipio(
    cliente: ClienteQueridoDiario,
    identificador: str,
) -> Optional[Municipio]:
    """Resolve `identificador` em um Municipio.

    Aceita:
      - código IBGE de 7 dígitos (ex.: "3550308")
      - "Nome/UF"          (ex.: "São Paulo/SP")  -> filtra pela UF
      - "Nome"             (ex.: "Sorocaba")      -> primeiro resultado
    """
    ident = identificador.strip()
    if ident.isdigit() and len(ident) == 7:
        m = cliente.detalhar_municipio(ident)
        return m or Municipio(ident, ident, "")

    uf = None
    nome = ident
    if "/" in ident:
        nome, uf = (p.strip() for p in ident.rsplit("/", 1))

    candidatos = cliente.buscar_municipios(nome)
    if not candidatos:
        return None
    if uf:
        filtrados = [c for c in candidatos if c.state_code.upper() == uf.upper()]
        if filtrados:
            candidatos = filtrados
    # prefere correspondência exata de nome (sem acento é feito na extração)
    exatos = [c for c in candidatos if c.territory_name.lower() == nome.lower()]
    return (exatos or candidatos)[0]


def _enriquecer_inep(
    qedu_cliente: "ClienteQEdu", territory_id: str
) -> Optional[ResumoINEP]:
    """Busca no QEdu o resumo da rede municipal; nunca derruba o fluxo."""
    if not territory_id:
        return None
    try:
        return qedu_cliente.resumo_municipio(territory_id)
    except ErroQEdu as exc:
        logger.warning("QEdu indisponível para %s: %s", territory_id, exc)
        return ResumoINEP(
            codigo_ibge=territory_id,
            ano=qedu_cliente.ano,
            num_escolas_municipais=0,
            num_matriculas_municipais=None,
            matriculas_disponivel=False,
            aviso=f"Falha ao consultar QEdu: {exc}",
        )


def raspar_municipio(
    cliente: ClienteQueridoDiario,
    identificador: str,
    published_since: Optional[str] = None,
    published_until: Optional[str] = None,
    max_diarios: int = 60,
    querystring: str = QUERY_EDUCACAO,
    apenas_contexto_educacao: bool = True,
    qedu_cliente: Optional["ClienteQEdu"] = None,
) -> ResultadoMunicipio:
    """Executa o fluxo completo para um município.

    Se `qedu_cliente` for informado, enriquece o resultado com dados do Censo
    Escolar (nº de escolas municipais e matrículas) via API do QEdu.
    """
    municipio = resolver_municipio(cliente, identificador)
    if municipio is None:
        vazio = Municipio("", identificador, "")
        return ResultadoMunicipio(vazio, 0, 0, aviso="Município não encontrado na API.")

    logger.info(
        "Raspando %s/%s (IBGE %s)",
        municipio.territory_name,
        municipio.state_code,
        municipio.territory_id,
    )

    diarios = list(
        cliente.buscar_diarios(
            territory_ids=[municipio.territory_id],
            querystring=querystring,
            published_since=published_since,
            published_until=published_until,
            max_resultados=max_diarios,
        )
    )

    listas_contatos = []
    atos: list[AtoSecretario] = []
    analisados = 0
    for d in diarios:
        if not d.txt_url:
            # Sem texto plano: aproveita ao menos os excerpts da busca.
            texto = "\n".join(d.excerpts)
        else:
            texto = cliente.baixar_texto(d.txt_url) or "\n".join(d.excerpts)
        if not texto:
            continue
        analisados += 1
        listas_contatos.append(
            extrair_contatos(
                texto,
                fonte_url=d.url,
                data=d.date,
                apenas_contexto_educacao=apenas_contexto_educacao,
            )
        )
        # Mesmo texto, sem custo de rede extra: procura atos de nomeação.
        atos.extend(extrair_atos(texto, fonte_url=d.url, data=d.date))

    contatos = agregar_contatos(listas_contatos)

    secretario = consolidar_secretario(atos)
    if secretario is not None:
        associar_contato(secretario, contatos)

    aviso = None
    if not contatos:
        aviso = (
            "Nenhum contato encontrado no contexto da Secretaria de Educação. "
            "Tente ampliar o período (--desde/--ate) ou usar --sem-filtro-contexto."
        )

    inep = _enriquecer_inep(qedu_cliente, municipio.territory_id) if qedu_cliente else None

    return ResultadoMunicipio(
        municipio=municipio,
        total_diarios=len(diarios),
        diarios_analisados=analisados,
        contatos=contatos,
        aviso=aviso,
        inep=inep,
        secretario=secretario,
    )
