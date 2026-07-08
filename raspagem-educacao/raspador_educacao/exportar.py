"""Exportação dos resultados para JSON e CSV (formato pronto para prospecção)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .pipeline import ResultadoMunicipio


def salvar_json(resultados: Iterable[ResultadoMunicipio], caminho: str | Path) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = [r.para_dict() for r in resultados]
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def salvar_csv_contatos(
    resultados: Iterable[ResultadoMunicipio], caminho: str | Path
) -> None:
    """Uma linha por contato — ideal para importar em CRM/planilha."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "municipio",
        "uf",
        "territory_id",
        "tipo",
        "valor",
        "governamental",
        "score",
        "ocorrencias",
        "fonte_exemplo",
        "data_exemplo",
        "trecho_exemplo",
    ]
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in resultados:
            for c in r.contatos:
                ev = c.evidencias[0] if c.evidencias else None
                w.writerow(
                    {
                        "municipio": r.municipio.territory_name,
                        "uf": r.municipio.state_code,
                        "territory_id": r.municipio.territory_id,
                        "tipo": c.tipo,
                        "valor": c.valor,
                        "governamental": "sim" if c.governamental else "nao",
                        "score": round(c.score, 2),
                        "ocorrencias": c.ocorrencias,
                        "fonte_exemplo": ev.fonte_url if ev else "",
                        "data_exemplo": ev.data if ev else "",
                        "trecho_exemplo": ev.trecho if ev else "",
                    }
                )


def salvar_csv_prospeccao(
    resultados: Iterable[ResultadoMunicipio], caminho: str | Path
) -> None:
    """Uma linha por município, com o melhor e-mail e telefone — para prospecção.

    Colunas alinhadas a campos comuns de CRM (ex.: HubSpot: company, email, phone).
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "empresa",           # ex.: "Prefeitura de São Paulo - Sec. Educação"
        "municipio",
        "uf",
        "territory_id",
        "secretario_nome",       # titular do cargo (diário oficial)
        "secretario_situacao",   # nomeacao | designacao
        "secretario_desde",      # data do ato
        "secretario_confianca",  # alta | media | baixa
        "secretario_email",
        "secretario_telefone",
        "secretario_fonte",
        "email_principal",
        "emails_alternativos",
        "telefone_principal",
        "telefones_alternativos",
        "escolas_municipais",   # INEP/QEdu
        "matriculas_municipais",  # INEP/QEdu
        "ano_censo",
        "fonte",
        "data_fonte",
        "observacao",
    ]
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in resultados:
            emails = r.emails()
            tels = r.telefones()
            email_princ = emails[0] if emails else None
            tel_princ = tels[0] if tels else None
            fonte = ""
            data_fonte = ""
            for c in (email_princ, tel_princ):
                if c and c.evidencias:
                    fonte = c.evidencias[0].fonte_url
                    data_fonte = c.evidencias[0].data
                    break
            inep = r.inep
            sec = r.secretario
            w.writerow(
                {
                    "empresa": f"Prefeitura de {r.municipio.territory_name} - Secretaria de Educação",
                    "municipio": r.municipio.territory_name,
                    "uf": r.municipio.state_code,
                    "territory_id": r.municipio.territory_id,
                    "secretario_nome": sec.nome if sec else "",
                    "secretario_situacao": sec.situacao if sec else "",
                    "secretario_desde": sec.desde if sec else "",
                    "secretario_confianca": sec.confianca if sec else "",
                    "secretario_email": (sec.email or "") if sec else "",
                    "secretario_telefone": (sec.telefone or "") if sec else "",
                    "secretario_fonte": sec.fonte_url if sec else "",
                    "email_principal": email_princ.valor if email_princ else "",
                    "emails_alternativos": "; ".join(c.valor for c in emails[1:5]),
                    "telefone_principal": tel_princ.valor if tel_princ else "",
                    "telefones_alternativos": "; ".join(c.valor for c in tels[1:5]),
                    "escolas_municipais": inep.num_escolas_municipais if inep else "",
                    "matriculas_municipais": (
                        inep.num_matriculas_municipais
                        if inep and inep.num_matriculas_municipais is not None
                        else ""
                    ),
                    "ano_censo": inep.ano if inep and inep.ano else "",
                    "fonte": fonte,
                    "data_fonte": data_fonte,
                    "observacao": "; ".join(
                        x for x in [r.aviso, inep.aviso if inep else None] if x
                    ),
                }
            )
