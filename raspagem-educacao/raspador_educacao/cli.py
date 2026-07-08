"""Interface de linha de comando.

Exemplos:
    # Um município por nome/UF, últimos 18 meses
    python -m raspador_educacao --municipio "Sorocaba/SP" --desde 2025-01-01

    # Vários municípios a partir de um arquivo (um por linha)
    python -m raspador_educacao --lista municipios.txt --saida resultados/

    # Por código IBGE, sem restringir ao contexto de educação (mais recall)
    python -m raspador_educacao --municipio 3550308 --sem-filtro-contexto
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import os

from .api import ClienteQueridoDiario
from .exportar import salvar_csv_contatos, salvar_csv_prospeccao, salvar_json
from .pipeline import raspar_municipio
from .qedu import ClienteQEdu, ErroQEdu


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="raspador_educacao",
        description="Raspa contatos das Secretarias Municipais de Educação via API do Querido Diário.",
    )
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--municipio",
        action="append",
        default=[],
        help='Município: "Nome/UF", "Nome" ou código IBGE. Pode repetir.',
    )
    grupo.add_argument(
        "--lista",
        type=Path,
        help="Arquivo texto com um município por linha.",
    )
    p.add_argument("--desde", dest="desde", help="Data inicial YYYY-MM-DD (published_since).")
    p.add_argument("--ate", dest="ate", help="Data final YYYY-MM-DD (published_until).")
    p.add_argument(
        "--max-diarios",
        type=int,
        default=60,
        help="Máximo de diários analisados por município (padrão: 60).",
    )
    p.add_argument(
        "--sem-filtro-contexto",
        action="store_true",
        help="Extrai contatos de todo o diário, não só perto de 'educação' (mais recall, menos precisão).",
    )
    p.add_argument(
        "--saida",
        type=Path,
        default=Path("resultados"),
        help="Diretório de saída (padrão: ./resultados).",
    )
    # Enriquecimento com dados do Censo Escolar via QEdu
    p.add_argument(
        "--qedu-token",
        default=os.environ.get("QEDU_API_TOKEN"),
        help="Token da API do QEdu (ou variável de ambiente QEDU_API_TOKEN). "
        "Habilita nº de escolas municipais e matrículas por município.",
    )
    p.add_argument(
        "--qedu-ano",
        type=int,
        default=None,
        help="Ano do Censo Escolar a consultar no QEdu (padrão: mais recente).",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Log detalhado.")
    return p.parse_args(argv)


def _carregar_municipios(args: argparse.Namespace) -> list[str]:
    if args.lista:
        linhas = args.lista.read_text(encoding="utf-8").splitlines()
        return [l.strip() for l in linhas if l.strip() and not l.startswith("#")]
    return args.municipio


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    municipios = _carregar_municipios(args)
    if not municipios:
        print("Nenhum município informado.", file=sys.stderr)
        return 2

    cliente = ClienteQueridoDiario()

    qedu_cliente = None
    if args.qedu_token:
        try:
            qedu_cliente = ClienteQEdu(token=args.qedu_token, ano=args.qedu_ano)
            print("QEdu habilitado: enriquecendo com escolas/matrículas.", file=sys.stderr)
        except ErroQEdu as exc:
            print(f"QEdu desabilitado: {exc}", file=sys.stderr)
    else:
        print(
            "Sem token do QEdu (--qedu-token / QEDU_API_TOKEN): "
            "seguindo apenas com os contatos do Querido Diário.",
            file=sys.stderr,
        )

    resultados = []
    for ident in municipios:
        print(f"→ Processando: {ident}", file=sys.stderr)
        try:
            r = raspar_municipio(
                cliente,
                ident,
                published_since=args.desde,
                published_until=args.ate,
                max_diarios=args.max_diarios,
                apenas_contexto_educacao=not args.sem_filtro_contexto,
                qedu_cliente=qedu_cliente,
            )
        except Exception as exc:  # não deixa um município derrubar o lote
            logging.exception("Falha ao processar %s", ident)
            print(f"  ! erro: {exc}", file=sys.stderr)
            continue
        resultados.append(r)
        n_email = len(r.emails())
        n_tel = len(r.telefones())
        extra = ""
        if r.secretario is not None:
            extra += f", secretário(a): {r.secretario.nome} ({r.secretario.confianca})"
        if r.inep is not None:
            mat = r.inep.num_matriculas_municipais
            extra = (
                f", {r.inep.num_escolas_municipais} escolas municipais"
                + (f", {mat} matrículas" if mat is not None else "")
            )
        print(
            f"  {r.municipio.territory_name}/{r.municipio.state_code}: "
            f"{r.diarios_analisados} diários, {n_email} e-mails, {n_tel} telefones"
            + extra
            + (f" — {r.aviso}" if r.aviso else ""),
            file=sys.stderr,
        )

    if not resultados:
        print("Nenhum resultado gerado.", file=sys.stderr)
        return 1

    saida = args.saida
    salvar_json(resultados, saida / "contatos.json")
    salvar_csv_contatos(resultados, saida / "contatos.csv")
    salvar_csv_prospeccao(resultados, saida / "prospeccao.csv")
    print(
        f"\nArquivos gerados em {saida}/:\n"
        f"  - contatos.json      (dados completos + evidências)\n"
        f"  - contatos.csv       (uma linha por contato)\n"
        f"  - prospeccao.csv     (uma linha por município, pronto p/ CRM)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
