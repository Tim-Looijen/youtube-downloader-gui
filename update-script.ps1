# --- Config ---
$GitBash = "C:\Program Files\Git\bin\bash.exe"
$TagPrefix = "v1.0."

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
if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}
$PrefilledCommand = "pyinstaller main.spec"   # EDIT THIS

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoWin'; .\.venv\Scripts\Activate.ps1; Set-PSReadLineOption -EditMode Windows; [Microsoft.PowerShell.PSConsoleReadLine]::Insert('$PrefilledCommand')"

Write-Host "Waiting till building and testing is complete. Close the .venv terminal when done."
Start-Sleep -Seconds 1
Wait-Process -Name "powershell" -ErrorAction SilentlyContinue

# ------------- Step 5: git push & release -------------
$LatestTag = & $GitBash -lc "cd '$RepoBash'; git tag --list '${TagPrefix}*' | sort -V | tail -n 1"
$LatestTag = $LatestTag.Trim()

$Patch = [int]($LatestTag -replace "^$TagPrefix", "")
$NewPatch = $Patch + 1
$NewTag = "$TagPrefix$NewPatch"

& $GitBash -i -c "cd '$RepoBash' && git add -A && git commit -m 'Added new exe ready for release' && git push && git tag $NewTag && git push origin $NewTag"
