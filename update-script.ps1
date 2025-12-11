# --- Config ---
$PyInstallerCommand = 'pyinstaller --onefile --noconsole --add-binary="C:\Users\tim\youtube-downloader-gui\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe;." --add-binary="C:\Users\tim\youtube-downloader-gui\deno-x86_64-pc-windows-msvc\deno.exe;." C:\Users\tim\youtube-downloader-gui\main.py'
$GitBash = "C:\Program Files\Git\bin\bash.exe"          # Default Git Bash path on Win11

# Convert current directory to a bash-friendly /c/... path
$RepoWin = (Get-Location).Path
$RepoBash = "/" + $RepoWin.Substring(0,1).ToLower() + $RepoWin.Substring(2) -replace '\\','/'

# ------------- Step 1: git fetch + pull via bash -------------
& $GitBash -i -c "cd '$RepoBash' && git fetch && git pull"

# ------------- Step 2 + 3: Rebuild venv to include newest changes -------------

if (Test-Path .venv) {
    Remove-Item .venv -Recurse -Force
}

python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install .


# ------------- Step 4: Manualy run PyInstaller -------------
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoWin'; .\.venv\Scripts\Activate.ps1"

# Wait until the new terminal is closed
Write-Host "Waiting for manual build to finish. Close the new terminal when done."
Start-Sleep -Seconds 2
Wait-Process -Name "powershell" -ErrorAction SilentlyContinue

# ------------- Step 5: Run exe -------------
$Exe = Get-ChildItem -Path ".\dist" -Filter *.exe -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1
& $Exe.FullName
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ------------- Step 6: git push via bash -------------
& $GitBash -i -c "cd '$RepoBash' && git add -A && git commit -m 'auto' && git push"