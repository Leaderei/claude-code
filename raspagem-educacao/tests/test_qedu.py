"""Testes do cliente QEdu — offline, com sessão HTTP simulada (sem rede)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from raspador_educacao.qedu import ClienteQEdu, EscolaINEP, ResumoINEP  # noqa: E402


class FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    """Simula a paginação estilo Laravel do QEdu."""

    def __init__(self, paginas):
        self.paginas = paginas  # lista de payloads por página
        self.headers = {}
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append(params)
        page = int(params.get("page", 1))
        idx = page - 1
        if idx < len(self.paginas):
            return FakeResp(self.paginas[idx])
        return FakeResp({"data": [], "meta": {"last_page": len(self.paginas)}})


def _cliente(paginas):
    return ClienteQEdu(
        token="fake",
        session=FakeSession(paginas),
        intervalo_min=0.0,  # sem espera nos testes
        per_page=2,
    )


def test_parsing_tolerante_de_campos():
    e = EscolaINEP.de_json(
        {"co_entidade": 35000, "no_entidade": "EMEF X", "qt_mat_bas": "120"}
    )
    assert e.codigo == "35000"
    assert e.nome == "EMEF X"
    assert e.matriculas == 120


def test_resumo_soma_matriculas_e_conta_escolas():
    paginas = [
        {
            "data": [
                {"cod_inep": 1, "nome": "EMEF A", "matriculas": 100},
                {"cod_inep": 2, "nome": "EMEF B", "matriculas": 250},
            ],
            "meta": {"last_page": 2, "per_page": 2},
        },
        {
            "data": [{"cod_inep": 3, "nome": "EMEI C", "matriculas": 50}],
            "meta": {"last_page": 2, "per_page": 2},
        },
    ]
    resumo = _cliente(paginas).resumo_municipio("3550308")
    assert resumo.num_escolas_municipais == 3
    assert resumo.num_matriculas_municipais == 400
    assert resumo.matriculas_disponivel is True
    assert resumo.aviso is None


def test_dependencia_municipal_enviada():
    paginas = [{"data": [], "meta": {"last_page": 1}}]
    cli = _cliente(paginas)
    cli.resumo_municipio("3550308")
    primeira = cli.session.chamadas[0]
    assert primeira["municipio_id"] == "3550308"
    assert primeira["dependencia"] == 3  # rede municipal


def test_sem_matriculas_gera_aviso():
    paginas = [{"data": [{"cod_inep": 1, "nome": "EMEF A"}], "meta": {"last_page": 1}}]
    resumo = _cliente(paginas).resumo_municipio("3550308")
    assert resumo.num_escolas_municipais == 1
    assert resumo.num_matriculas_municipais is None
    assert resumo.matriculas_disponivel is False
    assert "matrículas" in (resumo.aviso or "")


def test_municipio_sem_escolas():
    paginas = [{"data": [], "meta": {"last_page": 1}}]
    resumo = _cliente(paginas).resumo_municipio("0000000")
    assert resumo.num_escolas_municipais == 0
    assert "Nenhuma escola" in (resumo.aviso or "")


def test_token_obrigatorio():
    import os

    old = os.environ.pop("QEDU_API_TOKEN", None)
    try:
        erro = False
        try:
            ClienteQEdu(token=None)
        except Exception:
            erro = True
        assert erro
    finally:
        if old:
            os.environ["QEDU_API_TOKEN"] = old


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
