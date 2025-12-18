# --- Config ---
$GitBash = "C:\Program Files\Git\bin\bash.exe"
$TagPrefix = "v1.0."
$GitHubOwner = "Tim-Looijen"
$GitHubRepo = "youtube-downloader-gui"

# Convert current directory to a bash-compatible path
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

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoWin'; .\.venv\Scripts\Activate.ps1;"

Write-Host "Waiting till building and testing is complete. Close the .venv terminal when done."
Start-Sleep -Seconds 1
Wait-Process -Name "powershell" -ErrorAction SilentlyContinue

# ------------- Step 5: git push & tag -------------
$LatestTag = & $GitBash -lc "cd '$RepoBash'; git tag --list '${TagPrefix}*' | sort -V | tail -n 1"
$LatestTag = $LatestTag.Trim()

$Patch = [int]($LatestTag -replace "^$TagPrefix", "")
$NewPatch = $Patch + 1
$NewTag = "$TagPrefix$NewPatch"

& $GitBash -i -c "cd '$RepoBash' && git add --all && git commit -m 'automatic-release-commit' && git push && git tag $NewTag && git push origin $NewTag"

# ------------- Step 6: GitHub API Release -------------
$ReleaseTitle = "$NewTag"
$ReleaseNotes = "Automatic release $NewTag"

# Create GitHub release (no asset attached)
gh release create $NewTag dist\youtube-downloader-gui.exe --title $ReleaseTitle --notes $ReleaseNotes --repo "$GitHubOwner/$GitHubRepo"

Write-Host "`nRelease $NewTag created successfully on GitHub."

Write-Host "`nPress Enter to exit..."
Read-Host
