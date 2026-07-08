"""Testes da identificação do(a) secretário(a) — offline, sem rede."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from raspador_educacao.extracao import Contato, Evidencia  # noqa: E402
from raspador_educacao.secretarios import (  # noqa: E402
    associar_contato,
    consolidar_secretario,
    extrair_atos,
)

NOMEACAO = (
    "DECRETO Nº 1.234, DE 2 DE JANEIRO DE 2025. "
    "NOMEAR MARIA DA SILVA SANTOS para exercer o cargo em comissão de "
    "Secretária Municipal de Educação, a partir desta data."
)

EXONERACAO = (
    "DECRETO Nº 2.001, DE 10 DE MARÇO DE 2025. Fica exonerada a Sra. "
    "MARIA DA SILVA SANTOS do cargo de Secretária Municipal de Educação."
)

NOMEACAO2 = (
    "DECRETO Nº 2.002, DE 10 DE MARÇO DE 2025. Fica nomeado o Sr. "
    "JOÃO PEREIRA DE SOUZA para o cargo de Secretário Municipal de Educação."
)

DESIGNACAO = (
    "PORTARIA 55/2025. Designar a servidora Ana Paula Rodrigues para "
    "responder pela Secretaria Municipal de Educação, interinamente."
)


def test_extrai_nomeacao():
    atos = extrair_atos(NOMEACAO, "http://do/1", "2025-01-02")
    assert len(atos) == 1
    assert atos[0].tipo == "nomeacao"
    assert "MARIA DA SILVA SANTOS" in atos[0].nome


def test_extrai_exoneracao():
    atos = extrair_atos(EXONERACAO, "http://do/2", "2025-03-10")
    assert atos and atos[0].tipo == "exoneracao"
    assert "MARIA" in atos[0].nome


def test_extrai_designacao_title_case():
    atos = extrair_atos(DESIGNACAO, "http://do/3", "2025-02-01")
    assert atos and atos[0].tipo == "designacao"
    assert "Ana Paula Rodrigues" in atos[0].nome


def test_nao_captura_cargo_como_nome():
    # não deve retornar "Secretária Municipal De Educação" como nome de pessoa
    atos = extrair_atos(NOMEACAO, "http://do/1", "2025-01-02")
    for a in atos:
        assert "educacao" not in a.nome.lower()
        assert "municipal" not in a.nome.lower()


def test_consolidacao_troca_de_titular():
    atos = []
    atos += extrair_atos(NOMEACAO, "http://do/1", "2025-01-02")
    atos += extrair_atos(EXONERACAO, "http://do/2", "2025-03-10")
    atos += extrair_atos(NOMEACAO2, "http://do/3", "2025-03-10")
    sec = consolidar_secretario(atos)
    assert sec is not None
    # Maria foi exonerada; titular atual deve ser João
    assert "JOÃO" in sec.nome or "JOAO" in sec.nome.upper()
    assert sec.situacao == "nomeacao"


def test_consolidacao_titular_unico():
    atos = extrair_atos(NOMEACAO, "http://do/1", "2025-01-02")
    sec = consolidar_secretario(atos)
    assert sec is not None
    assert "MARIA" in sec.nome
    assert sec.confianca == "alta"


def test_associa_email_pessoal():
    atos = extrair_atos(NOMEACAO, "http://do/1", "2025-01-02")
    sec = consolidar_secretario(atos)
    contatos = [
        Contato("email", "maria.santos@prefeitura.gov.br", "x", 10, 1,
                [Evidencia("u", "d", "t")]),
        Contato("email", "gabinete@prefeitura.gov.br", "x", 8, 1,
                [Evidencia("u", "d", "t")]),
        Contato("telefone", "(15) 3200-1000", "x", 5, 1, [Evidencia("u", "d", "t")]),
    ]
    associar_contato(sec, contatos)
    assert sec.email == "maria.santos@prefeitura.gov.br"
    assert "pessoal" in (sec.origem_contato or "")
    assert sec.telefone == "(15) 3200-1000"


def test_associa_email_institucional_quando_sem_match():
    atos = extrair_atos(NOMEACAO2, "http://do/3", "2025-03-10")
    sec = consolidar_secretario(atos)
    contatos = [
        Contato("email", "educacao@prefeitura.gov.br", "x", 8, 1,
                [Evidencia("u", "d", "t")]),
    ]
    associar_contato(sec, contatos)
    assert sec.email == "educacao@prefeitura.gov.br"
    assert "institucional" in (sec.origem_contato or "")


if __name__ == "__main__":
    import traceback

    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {nome}")
            except Exception:
                falhas += 1
                print(f"FAIL {nome}")
                traceback.print_exc()
    raise SystemExit(1 if falhas else 0)
