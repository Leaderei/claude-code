# Instalador para Windows (PowerShell).
#
# Como rodar, no PowerShell, dentro da pasta claude-code:
#     powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# Equivalente ao install.sh, que so roda em Linux/Mac.

param([switch]$DryRun)

$ErrorActionPreference = 'Stop'

$Aqui      = Split-Path -Parent $MyInvocation.MyCommand.Definition
$DirClaude = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
$Settings  = Join-Path $DirClaude 'settings.json'
$DirClasp  = Join-Path $DirClaude 'clasp'
$Origem    = Join-Path $Aqui 'config\permissions.json'

function Titulo($t) { Write-Host ""; Write-Host $t -ForegroundColor White }
function Diga($t)   { Write-Host "  $t" }
function Bom($t)    { Write-Host "  OK    $t" -ForegroundColor Green }
function Alerta($t) { Write-Host "  AVISO $t" -ForegroundColor Yellow }
function Ruim($t)   { Write-Host "  FALHA $t" -ForegroundColor Red }

function Tem-Prop($obj, $nome) {
    return ($null -ne $obj) -and ($obj.PSObject.Properties.Name -contains $nome)
}

function Set-Prop($obj, $nome, $valor) {
    if (Tem-Prop $obj $nome) { $obj.$nome = $valor }
    else { $obj | Add-Member -NotePropertyName $nome -NotePropertyValue $valor }
}

function Grava-Json($caminho, $obj) {
    $texto = $obj | ConvertTo-Json -Depth 100
    # UTF-8 SEM BOM. O -Encoding UTF8 do PowerShell 5.1 grava BOM, e o BOM
    # quebra o parser de JSON do Claude Code -- o settings.json inteiro seria
    # ignorado, silenciosamente.
    $utf8SemBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($caminho, $texto, $utf8SemBom)
}

# ---------------------------------------------------------------- 0. Checagens
Titulo "0. Verificacoes"

if (-not (Test-Path $Origem)) {
    Ruim "nao achei $Origem"
    Ruim "rode este script de dentro da pasta claude-code"
    exit 1
}
Bom "arquivos do repositorio encontrados"

$Python = $null
foreach ($cand in @('python', 'python3', 'py')) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $v = & $cand --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$v" -match '3\.') { $Python = $cand; break }
        } catch { }
    }
}
if ($Python) {
    Bom "Python encontrado: $Python"
} else {
    Alerta "Python 3 nao encontrado."
    Alerta "As permissoes serao instaladas mesmo assim, mas o auto-refresh"
    Alerta "do clasp precisa de Python. Instale em https://python.org e rode de novo."
}

# ------------------------------------------------------------------ 1. Backup
Titulo "1. Backup"
if (-not (Test-Path $DirClaude)) {
    if (-not $DryRun) { New-Item -ItemType Directory -Path $DirClaude -Force | Out-Null }
}

if (Test-Path $Settings) {
    $carimbo = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup  = "$Settings.bak.$carimbo"
    if ($DryRun) { Diga "[dry-run] copiaria settings.json para $backup" }
    else {
        Copy-Item $Settings $backup
        Bom "settings.json salvo em $backup"
    }
} else {
    Diga "nao existe settings.json ainda; sera criado"
}

# -------------------------------------------------------------- 2. Permissoes
Titulo "2. Permissoes"

$cfg = [PSCustomObject]@{}
if (Test-Path $Settings) {
    $bruto = (Get-Content $Settings -Raw)
    if ($bruto -and $bruto.Trim().Length -gt 0) {
        try { $cfg = $bruto | ConvertFrom-Json }
        catch {
            Ruim "seu settings.json atual tem JSON invalido; abortando para nao piorar"
            Ruim $_.Exception.Message
            exit 1
        }
    }
}

$novo = (Get-Content $Origem -Raw | ConvertFrom-Json).permissions

if (-not (Tem-Prop $cfg 'permissions')) {
    Set-Prop $cfg 'permissions' ([PSCustomObject]@{})
}
$perms = $cfg.permissions

# defaultMode: nao sobrescreve uma escolha explicita que nao seja o padrao.
$anterior = if (Tem-Prop $perms 'defaultMode') { $perms.defaultMode } else { $null }
if ($null -eq $anterior -or $anterior -eq 'default' -or $anterior -eq 'manual') {
    Set-Prop $perms 'defaultMode' $novo.defaultMode
    $de = if ($anterior) { $anterior } else { '(nenhum)' }
    Diga "defaultMode: $de -> $($novo.defaultMode)"
} else {
    Diga "defaultMode: mantido em '$anterior' (ja estava configurado)"
}

# allow / ask / deny: uniao, preservando o que ja existia e a ordem.
foreach ($chave in @('allow', 'ask', 'deny')) {
    $existentes = @()
    if ((Tem-Prop $perms $chave) -and ($null -ne $perms.$chave)) { $existentes = @($perms.$chave) }

    $adicionados = @()
    foreach ($regra in @($novo.$chave)) {
        if ($existentes -notcontains $regra) { $adicionados += $regra }
    }

    Set-Prop $perms $chave (@($existentes) + @($adicionados))
    Diga "$chave`: $($existentes.Count) existentes + $($adicionados.Count) novas = $($perms.$chave.Count)"
}

if (-not $DryRun) { Grava-Json $Settings $cfg }
else { Diga "[dry-run] nada gravado" }

# ------------------------------------------------------- 3. Scripts do clasp
Titulo "3. Auto-refresh do clasp"
if ($DryRun) {
    Diga "[dry-run] copiaria clasp-refresh.py para $DirClasp"
} else {
    New-Item -ItemType Directory -Path $DirClasp -Force | Out-Null
    Copy-Item (Join-Path $Aqui 'bin\clasp-refresh.py') (Join-Path $DirClasp 'clasp-refresh.py') -Force
    Bom "script instalado em $DirClasp"
}

# ---------------------------------------------------------- 4. Hook de sessao
Titulo "4. Hook SessionStart (renova o token a cada sessao)"
if (-not $Python) {
    Alerta "sem Python: pulei o hook. Instale o Python e rode este script de novo."
} elseif ($DryRun) {
    Diga "[dry-run] adicionaria o hook SessionStart"
} else {
    # Caminho absoluto com barras normais: evita problemas de escape e de
    # expansao de variavel, que difere entre cmd.exe e PowerShell.
    $alvo   = (Join-Path $DirClasp 'clasp-refresh.py') -replace '\\', '/'
    $comando = "$Python `"$alvo`" --quiet"

    if (-not (Tem-Prop $cfg 'hooks'))              { Set-Prop $cfg 'hooks' ([PSCustomObject]@{}) }
    if (-not (Tem-Prop $cfg.hooks 'SessionStart')) { Set-Prop $cfg.hooks 'SessionStart' @() }

    $sessao = @($cfg.hooks.SessionStart)
    $jaTem = $false
    foreach ($grupo in $sessao) {
        foreach ($h in @($grupo.hooks)) {
            if ($h.command -eq $comando) { $jaTem = $true }
        }
    }

    if ($jaTem) {
        Diga "hook ja estava instalado; nada a fazer"
    } else {
        $entrada = [PSCustomObject]@{
            hooks = @([PSCustomObject]@{ type = 'command'; command = $comando })
        }
        Set-Prop $cfg.hooks 'SessionStart' (@($sessao) + @($entrada))
        Grava-Json $Settings $cfg
        Bom "hook adicionado"
    }
}

# ------------------------------------------------------------ 5. Verificacao
Titulo "5. Verificacao"
if ($DryRun) {
    Diga "[dry-run] nada foi alterado"
} else {
    try {
        Get-Content $Settings -Raw | ConvertFrom-Json | Out-Null
        Bom "settings.json continua sendo JSON valido"
    } catch {
        Ruim "settings.json ficou invalido! Restaure o backup .bak mais recente."
        exit 1
    }
    Diga "pronto. Abra o Claude Code e confira com /status"
}

Write-Host ""
