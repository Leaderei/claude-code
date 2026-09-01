@echo off
REM Gera a base completa e a planilha do Google Sheets em um comando.
REM Uso: clique duas vezes neste arquivo.
setlocal
cd /d "%~dp0"

where py >nul 2>&1 && (set PY=py) || (set PY=python)
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python nao encontrado.
  echo Instale em https://python.org e marque "Add Python to PATH".
  pause
  exit /b 1
)

echo == 1/3 Instalando dependencias ==
%PY% -m pip install --quiet --upgrade pip
%PY% -m pip install --quiet -r requirements.txt

echo.
echo == 2/3 Baixando e filtrando a Receita Federal ==
echo    Sao ~6 GB. Leva de 1h30 a 3h. Pode deixar rodando.
echo    Se cair, rode de novo: o download continua de onde parou.
echo.
%PY% gerar_base.py --manter-zips --indice-amplo
if errorlevel 1 (echo ERRO na geracao da base. & pause & exit /b 1)

echo.
echo == 3/3 Montando a planilha do Google Sheets ==
for /f "delims=" %%F in ('dir /b /o-d saida\base_bm_estrutural_*.csv 2^>nul') do (
  set CSV=saida\%%F
  goto :achou
)
echo ERRO: nenhum CSV gerado. Revise ANEIS e CNAES em config.py.
pause
exit /b 1

:achou
%PY% montar_sheets.py "%CSV%"

echo.
echo =======================================================
echo  PRONTO
echo    Base .......: %CSV%
echo    Planilha ...: saida\base_bm_estrutural.xlsx
echo.
echo  Agora arraste o .xlsx para o Google Drive e abra
echo  como Google Sheets.
echo =======================================================
pause
