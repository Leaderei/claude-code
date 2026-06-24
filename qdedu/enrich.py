"""Enriquecimento de contatos a partir de fontes externas (pluggável).

O Querido Diário fornece texto de diários, não contatos atualizados. Este
módulo define a interface para complementar com fontes mais confiáveis
(site oficial da prefeitura, portal da transparência, etc.). As implementações
concretas ficam de fora do MVP, mas a interface deixa o ponto de extensão
explícito e testável.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .api import Municipality
from .storage import ContactRow


@dataclass
class EnrichmentResult:
    contacts: list[ContactRow]
    notes: str = ""


class Enricher(Protocol):
    """Implemente para adicionar uma fonte de contatos atualizada."""

    name: str

    def enrich(self, muni: Municipality) -> EnrichmentResult: ...


class NullEnricher:
    """Enricher padrão (no-op). Substitua por implementações reais."""

    name = "null"

    def enrich(self, muni: Municipality) -> EnrichmentResult:  # noqa: ARG002
        return EnrichmentResult(contacts=[], notes="sem enriquecimento")


# Exemplo de esqueleto para uma fonte real. Deixe comentado até implementar:
#
# class PrefeituraSiteEnricher:
#     name = "site_prefeitura"
#     def __init__(self, http): self.http = http
#     def enrich(self, muni):
#         # 1. descobrir o domínio oficial (ex.: busca / base de domínios .gov.br)
#         # 2. baixar a página de contato da Secretaria de Educação
#         # 3. extrair e-mail/telefone com qdedu.extract
#         # 4. retornar EnrichmentResult com source="site_prefeitura"
#         ...
