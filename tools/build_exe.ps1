$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    throw 'Virtuelle Umgebung .venv nicht gefunden. Bitte zuerst in PyCharm anlegen.'
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Installation von PyInstaller fehlgeschlagen.' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name 'FileName-Replacer' `
    --icon 'resources\FileName-Replacer.ico' `
    --add-data 'resources\FileName-Replacer.ico;resources' `
    --add-data 'LICENSE;.' `
    'main.py'
if ($LASTEXITCODE -ne 0) { throw 'EXE-Build fehlgeschlagen.' }
Write-Host 'Fertig: dist\FileName-Replacer.exe'
