$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $frontendRoot 'node_modules\vite\bin\vite.js'
$logRoot = Join-Path $projectRoot '.local'

foreach ($requiredPath in @($pythonPath, $vitePath, (Join-Path $projectRoot '.env'))) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Dependencia local ausente: $requiredPath. Siga a preparacao do README.md."
    }
}
$nodePath = (Get-Command node -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Test-LocalPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $connection = $client.ConnectAsync('127.0.0.1', $Port)
        return ($connection.Wait(500) -and $client.Connected)
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

# Processos independentes do terminal, limitados ao loopback da maquina.
if (-not (Test-LocalPort 8000)) {
    Start-Process -FilePath $pythonPath -WorkingDirectory $projectRoot -WindowStyle Hidden `
        -ArgumentList @('backend/manage.py', 'runserver', '127.0.0.1:8000', '--noreload') `
        -RedirectStandardOutput (Join-Path $logRoot 'backend.out.log') `
        -RedirectStandardError (Join-Path $logRoot 'backend.err.log') | Out-Null
}
if (-not (Test-LocalPort 5173)) {
    Start-Process -FilePath $nodePath -WorkingDirectory $frontendRoot -WindowStyle Hidden `
        -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort') `
        -RedirectStandardOutput (Join-Path $logRoot 'frontend.out.log') `
        -RedirectStandardError (Join-Path $logRoot 'frontend.err.log') | Out-Null
}

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $page = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 2
        $csrf = Invoke-RestMethod -Uri 'http://127.0.0.1:5173/api/auth/csrf/' -TimeoutSec 2
        if ($page.Content -match 'MOVI\+' -and ($csrf.csrfToken -or $csrf.csrf_token)) {
            $ready = $true
            break
        }
    } catch {
        # Aguarda inicializacao e disponibilidade do proxy frontend/API.
    }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    throw "MOVI+ nao respondeu. Verifique PostgreSQL, conflitos nas portas 5173/8000 e logs em $logRoot."
}
Write-Output 'MOVI+ disponivel em http://127.0.0.1:5173/'
Write-Output "Servidores em segundo plano. Logs: $logRoot"
