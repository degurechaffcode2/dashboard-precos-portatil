@echo off
title Dashboard de Precos - SINAPI + SEINFRA-CE
cd /d "%~dp0"

:: Verifica se dados.sqlite existe
if not exist "dados.sqlite" (
    echo ERRO: dados.sqlite nao encontrado!
    echo Cole dados.sqlite na mesma pasta do index.html
    pause
    exit /b 1
)

:: Encontra porta livre a partir de 8765
set PORT=8765
:checkport
powershell -Command "exit ((Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue).Count)" 2>nul
if %errorlevel% equ 0 (
    set /a PORT+=1
    goto checkport
)

echo ============================================
echo   Dashboard de Precos - SINAPI + SEINFRA-CE
echo ============================================
echo.
echo   Iniciando servidor local...
echo   Abrindo http://localhost:%PORT%
echo.
echo   Pressione Ctrl+C para parar
echo.

:: Abre o navegador
start "" http://localhost:%PORT%

:: Servidor HTTP via PowerShell
powershell -Command "$listener = New-Object System.Net.HttpListener; $listener.Prefixes.Add('http://localhost:%PORT%/'); $listener.Start(); Write-Host 'Servidor rodando...'; while ($listener.IsListening) { $ctx = $listener.GetContext(); $req = $ctx.Request; $res = $ctx.Response; $path = $req.Url.LocalPath -replace '^/', ''; if ($path -eq '') { $path = 'index.html' }; $filePath = Join-Path (Get-Location) $path; if (Test-Path $filePath) { if ($path -like '*.wasm') { $res.ContentType = 'application/wasm' } elseif ($path -like '*.sqlite') { $res.ContentType = 'application/octet-stream' } elseif ($path -like '*.html') { $res.ContentType = 'text/html; charset=utf-8' } elseif ($path -like '*.js') { $res.ContentType = 'application/javascript' } elseif ($path -like '*.css') { $res.ContentType = 'text/css' }; $bytes = [IO.File]::ReadAllBytes($filePath); $res.OutputStream.Write($bytes, 0, $bytes.Length) } else { $res.StatusCode = 404 }; $res.Close() }"
