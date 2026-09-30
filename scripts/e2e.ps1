<#
.SYNOPSIS
Runner único E2E: mata porta 8000, sobe Django com e2e_settings, roda Cypress e encerra o servidor.
.EXAMPLE
.\scripts\e2e.ps1
.\scripts\e2e.ps1 --spec cypress/e2e/login.cy.js
#>
Set-StrictMode -Off
$ErrorActionPreference = 'Continue'

# --- localiza Python do venv --------------------------------------------------
$scriptDir  = Split-Path $MyInvocation.MyCommand.Path
$projectDir = (Resolve-Path (Join-Path $scriptDir '..')).Path

$pythonCandidates = @(
    (Join-Path $projectDir '.venv\Scripts\python.exe'),
    (Join-Path $projectDir 'venv\Scripts\python.exe')
)
$python = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $python) {
    Write-Error "Nenhum venv encontrado em .venv ou venv. Crie o ambiente virtual antes de continuar."
    exit 1
}

# --- localiza Node.js (node.exe) e adiciona ao PATH se necessário -----------
$nodeExe = (Get-Command node.exe -ErrorAction SilentlyContinue)
if (-not $nodeExe) {
    # Busca em locais comuns: AppData\Local\Programs, Downloads, C:\Program Files
    $nodeCandidates = @(
        "$env:LOCALAPPDATA\Programs\nodejs\node.exe",
        "$env:LOCALAPPDATA\Programs\node\node.exe",
        "C:\Program Files\nodejs\node.exe",
        "C:\Program Files (x86)\nodejs\node.exe"
    )
    # Também varre Downloads do usuário
    $downloadsNode = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "node.exe" -Recurse -Depth 4 -ErrorAction SilentlyContinue |
                     Select-Object -First 1 -ExpandProperty FullName
    if ($downloadsNode) { $nodeCandidates += $downloadsNode }

    $foundNode = $nodeCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if ($foundNode) {
        $nodeDir = Split-Path $foundNode
        $env:PATH = "$nodeDir;$env:PATH"
        Write-Host "[e2e] Node encontrado em: $nodeDir"
    } else {
        Write-Error "node.exe não encontrado. Instale Node.js ou adicione-o ao PATH."
        exit 1
    }
}

# --- localiza cypress (prefere node_modules local, depois npx) ---------------
$cypressCmd = Join-Path $projectDir 'node_modules\.bin\cypress.cmd'
if (-not (Test-Path $cypressCmd)) {
    $npxCmd = Get-Command npx.cmd -ErrorAction SilentlyContinue
    if (-not $npxCmd) {
        Write-Error "cypress não encontrado em node_modules e npx.cmd não está no PATH."
        exit 1
    }
    $cypressRunner = { & npx.cmd cypress run @args }
} else {
    $cypressRunner = $null  # sinaliza: usar $cypressCmd diretamente
}

# --- mata processo na porta 8000 ----------------------------------------------
Write-Host "[e2e] Liberando porta 8000..."
$linhas = netstat -ano 2>$null | Select-String '0\.0\.0\.0:8000\s|127\.0\.0\.1:8000\s'
$procIds = $linhas | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
foreach ($procId in $procIds) {
    if ($procId -match '^\d+$' -and $procId -ne '0') {
        try { Stop-Process -Id ([int]$procId) -Force -ErrorAction SilentlyContinue } catch {}
    }
}
Start-Sleep -Milliseconds 800

# --- seed ---------------------------------------------------------------------
Write-Host "[e2e] Rodando seed_e2e..."
Set-Location $projectDir
& $python manage.py seed_e2e --settings=config.e2e_settings
if ($LASTEXITCODE -ne 0) { Write-Error "seed_e2e falhou (exit $LASTEXITCODE)."; exit 1 }

# --- sobe runserver em background ---------------------------------------------
Write-Host "[e2e] Subindo runserver (e2e_settings)..."
$serverJob = Start-Job -ScriptBlock {
    param($py, $proj)
    Set-Location $proj
    & $py manage.py runserver --settings=config.e2e_settings --noreload 2>&1
} -ArgumentList $python, $projectDir

# --- aguarda /accounts/login/ responder 200 (timeout 60s) --------------------
Write-Host "[e2e] Aguardando Django ficar pronto..."
$loginUrl = 'http://127.0.0.1:8000/accounts/login/'
$deadline = (Get-Date).AddSeconds(60)
$pronto   = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri $loginUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($r -and $r.StatusCode -eq 200) { $pronto = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $pronto) {
    Stop-Job $serverJob -PassThru | Remove-Job -Force
    Write-Error "Timeout: Django não respondeu em 60s."
    exit 1
}
Write-Host "[e2e] Django pronto. Iniciando Cypress..."

# --- roda Cypress -------------------------------------------------------------
$cypressExitCode = 0
try {
    if ($null -eq $cypressRunner) {
        & $cypressCmd run @args
    } else {
        & npx.cmd cypress run @args
    }
    $cypressExitCode = $LASTEXITCODE
} finally {
    Write-Host "[e2e] Encerrando runserver..."
    try { Stop-Job $serverJob -PassThru | Remove-Job -Force } catch {}
    $residual = netstat -ano 2>$null | Select-String '0\.0\.0\.0:8000\s|127\.0\.0\.1:8000\s'
    $residualIds = $residual | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
    foreach ($rId in $residualIds) {
        if ($rId -match '^\d+$' -and $rId -ne '0') {
            try { Stop-Process -Id ([int]$rId) -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    Write-Host "[e2e] Feito. Exit code Cypress: $cypressExitCode"
}

exit $cypressExitCode
