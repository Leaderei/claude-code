"""Testes do extrator — rodam offline, sem acessar a API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from raspador_educacao.extracao import (  # noqa: E402
    _normalizar_telefone,
    _formatar_telefone,
    agregar_contatos,
    extrair_contatos,
)

TEXTO = """
Diário Oficial do Município. Edição 1234.

SECRETARIA MUNICIPAL DE EDUCAÇÃO
Chamamento público nº 05/2025. Informações pelo e-mail
educacao@prefeitura.exemplo.gov.br ou pelo telefone (15) 3200-1000.
Atendimento também no celular (15) 99876-5432.

SECRETARIA DE OBRAS
Contato: obras@fornecedorprivado.com.br, Tel: (11) 4002-8922.
"""


def test_normalizar_telefone():
    assert _normalizar_telefone("(15) 3200-1000") == "1532001000"
    assert _normalizar_telefone("+55 15 99876-5432") == "15998765432"
    assert _normalizar_telefone("99999") is None  # curto demais
    assert _normalizar_telefone("(15) 12345-6789") is None  # celular sem 9 inicial


def test_formatar_telefone():
    assert _formatar_telefone("1532001000") == "(15) 3200-1000"
    assert _formatar_telefone("15998765432") == "(15) 99876-5432"


def test_extrai_email_no_contexto_educacao():
    contatos = extrair_contatos(TEXTO, "http://d.o/1", "2025-03-01")
    emails = {c.valor for c in contatos if c.tipo == "email"}
    assert "educacao@prefeitura.exemplo.gov.br" in emails
    # e-mail de obras está fora da janela da educação -> não deve aparecer
    assert "obras@fornecedorprivado.com.br" not in emails


def test_email_governamental_pontua_mais():
    contatos = extrair_contatos(TEXTO, "http://d.o/1", "2025-03-01")
    gov = next(c for c in contatos if c.valor == "educacao@prefeitura.exemplo.gov.br")
    assert gov.governamental is True
    assert gov.score > 0


def test_extrai_telefones_do_contexto():
    contatos = extrair_contatos(TEXTO, "http://d.o/1", "2025-03-01")
    tels = {c.valor for c in contatos if c.tipo == "telefone"}
    assert "(15) 3200-1000" in tels
    assert "(15) 99876-5432" in tels


def test_agregacao_deduplica():
    l1 = extrair_contatos(TEXTO, "http://d.o/1", "2025-03-01")
    l2 = extrair_contatos(TEXTO, "http://d.o/2", "2025-04-01")
    agregados = agregar_contatos([l1, l2])
    chaves = [(c.tipo, c.valor) for c in agregados]
    assert len(chaves) == len(set(chaves))  # sem duplicatas
    email = next(c for c in agregados if c.valor == "educacao@prefeitura.exemplo.gov.br")
    assert email.ocorrencias >= 2


def test_sem_contexto_educacao_retorna_vazio():
    texto = "SECRETARIA DE SAÚDE. Contato: saude@x.gov.br Tel (11) 3000-0000."
    assert extrair_contatos(texto, "u", "2025-01-01") == []


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
