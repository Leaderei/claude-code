"""Testes do armazenamento SQLite e exportação CSV (offline)."""
import csv

from qdedu.storage import ContactRow, Store


def _store(tmp_path):
    return Store(str(tmp_path / "t.sqlite"))


def test_idempotent_contacts(tmp_path):
    st = _store(tmp_path)
    st.upsert_municipalities([("3550308", "São Paulo", "SP")])
    rows = [ContactRow("3550308", "email", "a@b.gov.br")]
    assert st.add_contacts(rows) == 1
    # inserir de novo não duplica
    assert st.add_contacts(rows) == 0
    st.close()


def test_progress_resume(tmp_path):
    st = _store(tmp_path)
    assert not st.is_done("3550308")
    st.mark_progress("3550308", "SP", "done", seen=5)
    assert st.is_done("3550308")
    st.close()


def test_export_csv(tmp_path):
    st = _store(tmp_path)
    st.upsert_municipalities([("3550308", "São Paulo", "SP")])
    st.add_contacts(
        [
            ContactRow("3550308", "email", "edu@sp.gov.br", gazette_date="2024-01-01"),
            ContactRow("3550308", "phone", "1140028922"),
        ]
    )
    out = tmp_path / "out.csv"
    n = st.export_csv("SP", str(out))
    assert n == 2
    with open(out, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["municipio"] == "São Paulo"
    assert {r["tipo"] for r in rows} == {"email", "phone"}
    st.close()


def test_export_csv_wide_prioritizes_site_and_education(tmp_path):
    st = _store(tmp_path)
    st.upsert_municipalities([("3550308", "São Paulo", "SP")])
    st.add_contacts(
        [
            # do diário (fonte fraca)
            ContactRow("3550308", "email", "geral@sp.gov.br", source="querido_diario"),
            # do site, marcado como educação (deve vir primeiro)
            ContactRow(
                "3550308", "email", "educacao@sp.gov.br",
                title="educação", source="site_prefeitura",
            ),
            ContactRow("3550308", "phone", "1140028922", source="site_prefeitura"),
            ContactRow("3550308", "secretary", "Maria Souza"),
        ]
    )
    out = tmp_path / "wide.csv"
    n = st.export_csv_wide("SP", str(out))
    assert n == 1  # uma linha por município
    with open(out, encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))
    assert row["municipio"] == "São Paulo"
    assert row["melhor_email"] == "educacao@sp.gov.br"  # site+educação priorizado
    assert "geral@sp.gov.br" in row["todos_emails"]
    assert row["melhor_telefone"] == "1140028922"
    assert row["secretario"] == "Maria Souza"
    assert "site_prefeitura" in row["fontes"] and "querido_diario" in row["fontes"]
    st.close()
