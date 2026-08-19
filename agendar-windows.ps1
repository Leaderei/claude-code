# Agenda a renovacao do token do clasp a cada 30 minutos, no Windows.
#
# Rodar:
#     powershell -ExecutionPolicy Bypass -File .\agendar-windows.ps1
#
# Para remover depois:
#     Unregister-ScheduledTask -TaskName "clasp-refresh" -Confirm:$false
#
# O hook do Claude Code ja renova o token a cada sessao. Isto aqui cobre o caso
# de usar o clasp direto no terminal, sem abrir o Claude Code.

$ErrorActionPreference = 'Stop'

$Nome    = 'clasp-refresh'
$DirClasp = Join-Path $env:USERPROFILE '.claude\clasp'
$Script   = Join-Path $DirClasp 'clasp-refresh.py'
$Log      = Join-Path $DirClasp 'refresh.log'

function Bom($t)  { Write-Host "  OK    $t" -ForegroundColor Green }
function Ruim($t) { Write-Host "  FALHA $t" -ForegroundColor Red }

Write-Host ""

if (-not (Test-Path $Script)) {
    Ruim "nao achei $Script"
    Ruim "rode o install.ps1 primeiro"
    exit 1
}
Bom "script encontrado"

# Descobre o Python do mesmo jeito que o install.ps1.
$Python = $null
foreach ($cand in @('python', 'python3', 'py')) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $v = & $cand --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$v" -match '3\.') { $Python = $cmd.Source; break }
        } catch { }
    }
}
if (-not $Python) {
    Ruim "Python 3 nao encontrado no PATH"
    exit 1
}
Bom "Python: $Python"

# Redireciona a saida para um log, senao a janela do console pisca a cada 30 min.
$argumentos = "`"$Script`" --quiet"
$acao = New-ScheduledTaskAction -Execute $Python -Argument $argumentos -WorkingDirectory $DirClasp

$gatilho = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 30)

# Sem -RunLevel Highest: roda como voce, sem pedir admin, e enxerga o seu
# %USERPROFILE% -- que e justamente onde mora o .clasprc.json.
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

try {
    Register-ScheduledTask -TaskName $Nome -Action $acao -Trigger $gatilho `
        -Settings $config -Description 'Renova o token do clasp (Google Apps Script)' `
        -Force | Out-Null
    Bom "tarefa '$Nome' agendada: a cada 30 minutos"
} catch {
    Ruim "nao consegui agendar: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "  Conferir:  Get-ScheduledTask -TaskName $Nome"
Write-Host "  Rodar ja:  Start-ScheduledTask -TaskName $Nome"
Write-Host "  Remover:   Unregister-ScheduledTask -TaskName $Nome -Confirm:`$false"
Write-Host ""
