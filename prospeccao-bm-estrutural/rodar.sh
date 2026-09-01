#!/usr/bin/env bash
# Gera a base completa e a planilha do Google Sheets em um comando.
# Uso:  ./rodar.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "ERRO: Python nao encontrado. Instale em https://python.org (marque 'Add to PATH')."
  exit 1
fi

echo "== 1/3 Instalando dependencias =="
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt

echo
echo "== 2/3 Baixando e filtrando a Receita Federal =="
echo "   Sao ~6 GB. Leva de 1h30 a 3h. Pode deixar rodando."
echo "   Se cair, rode de novo: o download continua de onde parou."
echo
"$PY" gerar_base.py --manter-zips --indice-amplo

CSV=$(ls -t saida/base_bm_estrutural_*.csv 2>/dev/null | head -1)
if [ -z "$CSV" ]; then
  echo "ERRO: nenhum CSV gerado. Revise ANEIS e CNAES em config.py."
  exit 1
fi

echo
echo "== 3/3 Montando a planilha do Google Sheets =="
"$PY" montar_sheets.py "$CSV"

echo
echo "======================================================="
echo " PRONTO"
echo "   Base .......: $CSV"
echo "   Planilha ...: saida/base_bm_estrutural.xlsx"
echo
echo " Agora arraste o .xlsx para o Google Drive e abra"
echo " como Google Sheets."
echo "======================================================="
