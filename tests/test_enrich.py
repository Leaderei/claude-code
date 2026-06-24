"""Testes do enricher de site da prefeitura (HTML offline + respx)."""
import respx
from httpx import Response

from qdedu.api import CitiesClient, Municipality
from qdedu.enrich import SitePrefeituraEnricher, html_to_text
from qdedu.http import HttpClient

QD = "https://api.queridodiario.ok.org.br"

HOME_HTML = """
<html><head><style>.x{color:red}</style></head><body>
<h1>Prefeitura de Exemplópolis</h1>
<a href="mailto:gabinete@exemplopolis.sp.gov.br">Gabinete</a>
<script>var a='naovale@spam.com';</script>
</body></html>
"""

EDU_HTML = """
<html><body>
<h2>Secretaria Municipal de Educação</h2>
<p>Atendimento de segunda a sexta.</p>
<a href="mailto:educacao@exemplopolis.sp.gov.br">E-mail</a>
<a href="tel:+551140028922">Telefone</a>
<p>Outro contato: (11) 3333-4444</p>
</body></html>
"""


def test_html_to_text_and_links():
    p = html_to_text(HOME_HTML)
    assert "Prefeitura de Exemplópolis" in p.text
    # conteúdo de <script>/<style> é ignorado
    assert "naovale@spam.com" not in p.text
    assert "color:red" not in p.text
    assert p.mailtos == ["gabinete@exemplopolis.sp.gov.br"]


@respx.mock
def test_enricher_extracts_education_contacts():
    base = "https://exemplopolis.sp.gov.br"
    # /cities/{id} aponta o publication_url para o domínio oficial
    respx.get(f"{QD}/cities/3500000").mock(
        return_value=Response(
            200,
            json={
                "city": {
                    "territory_id": "3500000",
                    "territory_name": "Exemplópolis",
                    "state_code": "SP",
                    "publication_urls": [base],
                }
            },
        )
    )
    respx.get(f"{base}/").mock(return_value=Response(200, text=HOME_HTML))
    respx.get(f"{base}/secretaria-de-educacao").mock(
        return_value=Response(200, text=EDU_HTML)
    )
    # demais caminhos não existem
    respx.route(host="exemplopolis.sp.gov.br").mock(return_value=Response(404))

    http = HttpClient(rate_rps=0)
    enr = SitePrefeituraEnricher(http=http, cities=CitiesClient(http))
    res = enr.enrich(Municipality("3500000", "Exemplópolis", "SP"))

    by_kind = {}
    for c in res.contacts:
        by_kind.setdefault(c.kind, []).append(c)
    emails = {c.value for c in by_kind.get("email", [])}
    phones = {c.value for c in by_kind.get("phone", [])}

    assert "gabinete@exemplopolis.sp.gov.br" in emails
    assert "educacao@exemplopolis.sp.gov.br" in emails
    assert "1140028922" in phones      # do href tel:
    assert "1133334444" in phones      # do texto
    # e-mail educacao marcado como contato de educação
    edu = next(c for c in by_kind["email"] if c.value.startswith("educacao@"))
    assert edu.title == "educação"
    assert all(c.source == "site_prefeitura" for c in res.contacts)


def test_enricher_skips_thirdparty_platforms():
    # publication_url de plataforma de terceiros é descartado como domínio
    enr = SitePrefeituraEnricher(http=HttpClient(rate_rps=0), cities=None)
    enr.domain_map = {}
    bases = enr._candidate_bases(Municipality("3500000", "X", "SP"))
    assert bases == []  # sem cities e sem mapa -> nenhum candidato
