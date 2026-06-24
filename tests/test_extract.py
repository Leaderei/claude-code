"""Testes offline da extração (regex de e-mail/telefone/secretário)."""
from qdedu.extract import (
    extract_all,
    extract_emails,
    extract_phones,
    extract_secretary,
    normalize_phone,
)

DIARIO = """
PREFEITURA MUNICIPAL DE EXEMPLÓPOLIS
SECRETARIA MUNICIPAL DE EDUCAÇÃO
Endereço: Rua das Flores, 100 - Centro
Contato: educacao@exemplopolis.sp.gov.br / gabinete.educacao@exemplopolis.sp.gov.br
Telefones: (11) 4002-8922 e (11) 99876-5432 - Ouvidoria 0800 123 4567
PORTARIA Nº 45/2024 - Nomeia Maria da Silva Souza, Secretária Municipal de
Educação, para o biênio 2024/2025.
Banner promocional: logo@2x.png deve ser ignorado.
"""


def test_extract_emails_dedup_and_noise():
    emails = extract_emails(DIARIO)
    assert "educacao@exemplopolis.sp.gov.br" in emails
    assert "gabinete.educacao@exemplopolis.sp.gov.br" in emails
    # imagem @2x.png não vira e-mail
    assert all("png" not in e for e in emails)
    assert len(emails) == 2


def test_extract_phones_formats():
    phones = set(extract_phones(DIARIO))
    assert "1140028922" in phones      # fixo com DDD
    assert "11998765432" in phones     # móvel com DDD
    assert "08001234567" in phones     # 0800


def test_normalize_phone():
    assert normalize_phone("+55 (11) 4002-8922") == "1140028922"
    assert normalize_phone("99876-5432") == "998765432"
    assert normalize_phone("123") is None


def test_extract_secretary_name():
    secs = extract_secretary(DIARIO)
    names = {s.name for s in secs}
    assert any("Maria da Silva Souza" == n for n in names)
    # cargo capturado
    assert any("educa" in s.title.lower() for s in secs)


def test_secretary_rejects_institution_as_name():
    txt = "SECRETARIA MUNICIPAL DE EDUCAÇÃO publica edital."
    secs = extract_secretary(txt)
    assert all("secretari" not in s.name.lower() for s in secs)


def test_extract_all_shape():
    ex = extract_all(DIARIO)
    assert ex.emails and ex.phones and ex.secretaries
