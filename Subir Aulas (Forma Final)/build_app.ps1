# Script de Automacao de Build - Dona Francisca Automator

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "INICIANDO PROCESSO DE COMPILACAO DO ROBO" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Limpeza de builds antigas
Write-Host "[1/4] Limpando diretorios temporarios antigos..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force build }
if (Test-Path "dist") { Remove-Item -Recurse -Force dist }
if (Test-Path "installer") { Remove-Item -Recurse -Force installer }

# 2. Executando compilacao do executavel via PyInstaller
Write-Host "[2/4] Compilando executavel com PyInstaller..." -ForegroundColor Yellow

$PyInstallerCmd = 'pyinstaller --noconsole --onefile --name="Dona Francisca Automator" --icon="../Play Branco.ico" --add-data="../Escrava-isaura-_fundo_.wav;." --add-data="../Play Branco.ico;." -p "../refatoracao_cursoms/src" "Subir Aula - Modulos Varios.py"'

Invoke-Expression $PyInstallerCmd

if ($LASTEXITCODE -ne 0) {
    Write-Error "Erro na compilacao do PyInstaller. Processo abortado."
    Exit 1
}

# Verifica se o arquivo final do executavel existe
$ExePath = "dist\Dona Francisca Automator.exe"
if (-not (Test-Path $ExePath)) {
    Write-Error "O executavel compilado nao foi encontrado em $ExePath"
    Exit 1
}
Write-Host "Executavel compilado com sucesso: $ExePath" -ForegroundColor Green

# 3. Compilando o instalador via Inno Setup
Write-Host "[3/4] Compilando o instalador com Inno Setup..." -ForegroundColor Yellow

# Cria cópias temporárias para o build para evitar erro de arquivo bloqueado
Copy-Item "..\banco_frota.db" "banco_frota_build.db" -Force
Copy-Item "..\config_unificada.json" "config_unificada_build.json" -Force

$ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $ISCC)) {
    Write-Error "O compilador do Inno Setup (ISCC.exe) nao foi encontrado no caminho padrao!"
    Exit 1
}

& $ISCC "dist_script.iss"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Erro na compilacao do instalador via Inno Setup."
    Exit 1
}

# 4. Finalizacao
$InstallerPath = "installer\Instalador_Dona_Francisca_1.0.exe"
if (-not (Test-Path $InstallerPath)) {
    if (Test-Path "banco_frota_build.db") { Remove-Item -Force "banco_frota_build.db" }
    if (Test-Path "config_unificada_build.json") { Remove-Item -Force "config_unificada_build.json" }
    Write-Error "O instalador final nao foi gerado em $InstallerPath"
    Exit 1
}

# Remove cópias temporárias com sucesso
if (Test-Path "banco_frota_build.db") { Remove-Item -Force "banco_frota_build.db" }
if (Test-Path "config_unificada_build.json") { Remove-Item -Force "config_unificada_build.json" }

Write-Host "==============================================" -ForegroundColor Green
Write-Host "PROCESSO DE BUILD CONCLUIDO COM SUCESSO!" -ForegroundColor Green
Write-Host "Instalador disponivel em: $InstallerPath" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
