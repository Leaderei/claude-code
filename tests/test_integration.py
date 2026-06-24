"""Validação ponta-a-ponta do pipeline com as APIs simuladas (respx).

Prova o caminho completo — IBGE → Querido Diário → download de txt → extração
→ SQLite → CSV — contra payloads no formato real das APIs, sem rede.
"""
import csv

import respx
from httpx import Response

from qdedu.http import HttpClient
from qdedu.scraper import scrape_uf
from qdedu.storage import Store

IBGE = "https://servicodados.ibge.gov.br/api/v1"
QD = "https://api.queridodiario.ok.org.br"

# Resposta no formato da API de localidades do IBGE.
IBGE_MUNICIPIOS = [
    {"id": 3550308, "nome": "São Paulo"},
    {"id": 3509502, "nome": "Campinas"},
]

# Texto bruto de um diário (txt_url), como o Querido Diário serve.
DIARIO_TXT = """
PREFEITURA DE SÃO PAULO - SECRETARIA MUNICIPAL DE EDUCAÇÃO
Contato: smed@prefeitura.sp.gov.br - Tel: (11) 3396-0500
PORTARIA Nº 12/2024: Nomeia João Carlos Pereira, Secretário Municipal de
Educação, a partir desta data.
"""

# Resposta no formato de GET /gazettes do Querido Diário.
QD_GAZETTES = {
    "total_gazettes": 1,
    "gazettes": [
        {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "state_code": "SP",
            "date": "2024-03-10",
            "edition": "1234",
            "is_extra_edition": False,
            "url": "https://querido-diario.example/sp/2024-03-10",
            "txt_url": f"{QD}/files/sp/3550308-2024-03-10.txt",
            "excerpts": ["...secretaria municipal de educação..."],
        }
    ],
}
QD_EMPTY = {"total_gazettes": 0, "gazettes": []}


@respx.mock
def test_pipeline_end_to_end(tmp_path):
    # IBGE: lista de municípios da UF
    respx.get(f"{IBGE}/localidades/estados/SP/municipios").mock(
        return_value=Response(200, json=IBGE_MUNICIPIOS)
    )
    # Querido Diário: São Paulo tem 1 diário; Campinas tem 0
    def gazettes_router(request):
        tids = request.url.params.get_list("territory_ids")
        if "3550308" in tids:
            return Response(200, json=QD_GAZETTES)
        return Response(200, json=QD_EMPTY)

    respx.get(f"{QD}/gazettes").mock(side_effect=gazettes_router)
    # download do txt do diário
    respx.get(f"{QD}/files/sp/3550308-2024-03-10.txt").mock(
        return_value=Response(200, text=DIARIO_TXT)
    )

    db = str(tmp_path / "e2e.sqlite")
    store = Store(db)
    http = HttpClient(rate_rps=0)  # sem sleep no teste

    stats = scrape_uf(uf="SP", store=store, http=http, fetch_full_text=True)

    assert stats["cities"] == 2          # 2 municípios processados
    assert stats["gazettes"] == 1        # 1 diário encontrado (SP)
    assert stats["errors"] == 0
    assert stats["contacts"] >= 3        # email + telefone + secretário

    # contatos esperados no banco
    kinds = {
        r["kind"]: r["value"]
        for r in store.conn.execute(
            "SELECT kind, value FROM contacts WHERE territory_id='3550308'"
        )
    }
    assert kinds.get("email") == "smed@prefeitura.sp.gov.br"
    assert kinds.get("phone") == "1133960500"
    assert "João Carlos Pereira" in kinds.get("secretary", "")

    # exportação CSV
    out = tmp_path / "sp.csv"
    n = store.export_csv("SP", str(out))
    assert n >= 3
    with open(out, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert all(r["municipio"] == "São Paulo" for r in rows)
    assert {"email", "phone", "secretary"} <= {r["tipo"] for r in rows}

    store.close()


@respx.mock
def test_resume_skips_done_cities(tmp_path):
    respx.get(f"{IBGE}/localidades/estados/SP/municipios").mock(
        return_value=Response(200, json=IBGE_MUNICIPIOS)
    )
    respx.get(f"{QD}/gazettes").mock(return_value=Response(200, json=QD_EMPTY))

    store = Store(str(tmp_path / "r.sqlite"))
    http = HttpClient(rate_rps=0)
    # primeira passada processa tudo
    s1 = scrape_uf(uf="SP", store=store, http=http)
    assert s1["cities"] == 2 and s1["skipped"] == 0
    # segunda passada pula as cidades já concluídas
    s2 = scrape_uf(uf="SP", store=store, http=http)
    assert s2["cities"] == 0 and s2["skipped"] == 2
    store.close()
