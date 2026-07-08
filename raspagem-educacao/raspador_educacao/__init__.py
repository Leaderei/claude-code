"""Raspador de contatos das Secretarias Municipais de Educação.

Usa a API pública do Querido Diário (https://api.queridodiario.ok.org.br)
para localizar diários oficiais que mencionam a Secretaria de Educação de um
município e extrair e-mails e telefones atualizados para prospecção.
"""

__version__ = "0.1.0"

from .api import ClienteQueridoDiario, ErroAPI
from .extracao import extrair_contatos, Contato
from .pipeline import raspar_municipio, ResultadoMunicipio
from .qedu import ClienteQEdu, ErroQEdu, ResumoINEP
from .secretarios import Secretario, extrair_atos, consolidar_secretario

__all__ = [
    "ClienteQueridoDiario",
    "ErroAPI",
    "extrair_contatos",
    "Contato",
    "raspar_municipio",
    "ResultadoMunicipio",
    "ClienteQEdu",
    "ErroQEdu",
    "ResumoINEP",
    "Secretario",
    "extrair_atos",
    "consolidar_secretario",
]
