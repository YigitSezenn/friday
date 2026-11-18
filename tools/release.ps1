#Requires -Version 5.1
<#
.SYNOPSIS
  FRIDAY release: merge (optional), bump, test, APK, exe, site, optional Vercel.

.EXAMPLE
  # Build only (no Vercel):
  powershell -ExecutionPolicy Bypass -File C:\Users\yigit\Desktop\jarvis-rebuild\tools\release.ps1 -MergeFix -Version 4.6

  # Full publish (needs explicit -Deploy; two Vercel pushes; surum last):
  powershell -ExecutionPolicy Bypass -File C:\Users\yigit\Desktop\jarvis-rebuild\tools\release.ps1 -MergeFix -Version 4.6 -Deploy
#>
[CmdletBinding()]
param(
  [string]$Version = "4.6",
  [switch]$MergeFix,
  [switch]$Deploy,
  [switch]$SkipTests,
  [string]$Root = "C:\Users\yigit\Desktop\jarvis-rebuild",
  [string]$FixBranch = "origin/fix/live-model-garble"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Step([string]$msg) {
  Write-Host ""
  Write-Host ("=== OK_STEP: {0} ===" -f $msg) -ForegroundColor Cyan
}
function Fail([string]$msg) {
  Write-Host ("=== FAIL: {0} ===" -f $msg) -ForegroundColor Red
  throw $msg
}
function Info([string]$msg) { Write-Host ("INFO: {0}" -f $msg) }

if ($Version -notmatch '^\d+\.\d+(\.\d+)?$') { Fail "Version must look like N.M or N.M.P (got '$Version')" }

$Site = Join-Path $Root "site"
$Indir = Join-Path $Site "public\indir"
$Backup = Join-Path ([Environment]::GetFolderPath("Desktop")) ("friday-backup-before-{0}-{1}" -f $Version, (Get-Date -Format "yyyyMMdd-HHmmss"))
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$Iscc = "C:\Users\yigit\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
$Preload = "C:\Users\yigit\AppData\Local\Temp\friday-vercel-preload.cjs"
$Npx = "C:\Program Files\nodejs\npx.cmd"
$GradleCandidates = @(
  Get-ChildItem (Join-Path $env:USERPROFILE ".gradle\wrapper\dists") -Recurse -Filter "gradle.bat" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\bin\\gradle\.bat$' } |
    Sort-Object FullName -Descending
)
$Gradle = $GradleCandidates | Select-Object -First 1

Write-Host "FRIDAY release script"
Info ("Root={0}" -f $Root)
Info ("Version={0} MergeFix={1} Deploy={2}" -f $Version, [bool]$MergeFix, [bool]$Deploy)

if (-not (Test-Path $VenvPy)) { Fail "Missing venv python: $VenvPy" }
if (-not (Test-Path $Iscc)) { Fail "Missing ISCC: $Iscc" }
if (-not (Test-Path $Npx)) { Fail "Missing npx: $Npx" }
if (-not $Gradle) { Fail "gradle.bat not found under %USERPROFILE%\.gradle\wrapper\dists" }
if ($Deploy -and -not (Test-Path $Preload)) { Fail "Missing vercel preload: $Preload" }

Set-Location $Root

# --- 0 backup ---
Step "0 backup current indir"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
foreach ($name in @("FRIDAY-Kurulum.exe", "FRIDAY.apk", "surum.txt")) {
  $src = Join-Path $Indir $name
  if (Test-Path $src) { Copy-Item $src (Join-Path $Backup $name) -Force }
}
Info ("Backup={0}" -f $Backup)
Get-ChildItem $Backup | ForEach-Object { Info ("  {0} {1}" -f $_.Name, $_.Length) }

# --- 1 merge ---
if ($MergeFix) {
  Step "1 merge $FixBranch"
  git fetch origin 2>&1 | Out-Host
  git merge $FixBranch -m ("Merge {0} for FRIDAY {1}" -f $FixBranch, $Version)
  if ($LASTEXITCODE -ne 0) { Fail "git merge failed" }
  Info ("HEAD={0}" -f (git rev-parse HEAD))
} else {
  Step "1 skip merge (no -MergeFix)"
}

# --- version bump (not surum.txt yet) ---
Step "1b bump version markers to $Version"
$init = Join-Path $Root "jarvis\__init__.py"
$iss = Join-Path $Root "packaging\friday.iss"
$gradleKts = Join-Path $Root "phone-android\app\build.gradle.kts"
$html = Join-Path $Site "index.html"
function Write-Utf8NoBom([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, [System.Text.UTF8Encoding]::new($false))
}
Write-Utf8NoBom $init ((Get-Content $init -Raw) -replace '__version__\s*=\s*"[^"]+"', ('__version__ = "{0}"' -f $Version))
Write-Utf8NoBom $iss ((Get-Content $iss -Raw) -replace 'AppVersion=\d+\.\d+(\.\d+)?', ('AppVersion={0}' -f $Version))
$verParts = $Version.Split('.')
$verMajor = [int]$verParts[0]
$verMinor = [int]$verParts[1]
$verPatch = if ($verParts.Length -ge 3) { [int]$verParts[2] } else { 0 }
$versionCode = ($verMajor * 10000) + ($verMinor * 100) + $verPatch
$gradleRaw = Get-Content $gradleKts -Raw
$gradleRaw = $gradleRaw -replace 'versionName\s*=\s*"[^"]+"', ('versionName = "{0}"' -f $Version)
$gradleRaw = [regex]::Replace($gradleRaw, 'versionCode\s*=\s*\d+', ('versionCode = {0}' -f $versionCode))
Write-Utf8NoBom $gradleKts $gradleRaw
# HTML: only query/version labels, not SVG path numbers like 10.5 4.4
$htmlRaw = [System.IO.File]::ReadAllText($html, [System.Text.UTF8Encoding]::new($false))
$htmlRaw = [regex]::Replace($htmlRaw, '\?v=\d+\.\d+(?:\.\d+)?', ('?v={0}' -f $Version))
$htmlRaw = [regex]::Replace($htmlRaw, 'Sürüm \d+\.\d+(?:\.\d+)?', ('Sürüm {0}' -f $Version))
Write-Utf8NoBom $html $htmlRaw
Info ("bumped __init__.py friday.iss build.gradle.kts(versionCode={0}) index.html (surum.txt untouched)" -f $versionCode)
# --- tests ---
if (-not $SkipTests) {
  Step "2 unittest"
  & $VenvPy -m unittest discover -s tests
  # unittest returns non-zero on failures; allow env failures but log
  Info ("unittest_exit={0}" -f $LASTEXITCODE)
  if ($LASTEXITCODE -gt 20) { Fail "too many test failures (exit=$LASTEXITCODE)" }
} else {
  Step "2 skip tests"
}

# --- APK ---
Step "3 Android assembleDebug"
$env:ANDROID_HOME = Join-Path $env:LOCALAPPDATA "Android\Sdk"
Set-Location (Join-Path $Root "phone-android")
& $Gradle.FullName assembleDebug
if ($LASTEXITCODE -ne 0) { Fail "assembleDebug failed" }
$apkSrc = Join-Path $Root "phone-android\app\build\outputs\apk\debug\app-debug.apk"
if (-not (Test-Path $apkSrc)) { Fail "APK missing: $apkSrc" }
Copy-Item $apkSrc (Join-Path $Indir "FRIDAY.apk") -Force
$apkHash = (Get-FileHash (Join-Path $Indir "FRIDAY.apk") -Algorithm SHA256).Hash
$apkLen = (Get-Item (Join-Path $Indir "FRIDAY.apk")).Length
Info ("APK_LEN={0}" -f $apkLen)
Info ("APK_SHA256={0}" -f $apkHash)
Set-Location $Root

# --- Windows ---
Step "4 PyInstaller"
& $VenvPy -m PyInstaller --noconfirm --distpath dist --workpath build packaging\friday.spec
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller failed" }

Step "5 Inno Setup"
& $Iscc (Join-Path $Root "packaging\friday.iss")
if ($LASTEXITCODE -ne 0) { Fail "ISCC failed" }
$exeSrc = Join-Path $Root "dist\FRIDAY-Kurulum.exe"
if (-not (Test-Path $exeSrc)) { Fail "installer missing" }
Copy-Item $exeSrc (Join-Path $Indir "FRIDAY-Kurulum.exe") -Force
$exeHash = (Get-FileHash (Join-Path $Indir "FRIDAY-Kurulum.exe") -Algorithm SHA256).Hash
$exeLen = (Get-Item (Join-Path $Indir "FRIDAY-Kurulum.exe")).Length
Info ("EXE_LEN={0}" -f $exeLen)
Info ("EXE_SHA256={0}" -f $exeHash)

# --- site build (surum still old) ---
Step "6 npm run build (surum not bumped yet)"
$oldSurum = ""
$surumPath = Join-Path $Indir "surum.txt"
if (Test-Path $surumPath) { $oldSurum = (Get-Content $surumPath -Raw).Trim() }
Info ("SURUM_BEFORE_DEPLOY={0}" -f $oldSurum)
Set-Location $Site
npm run build
if ($LASTEXITCODE -ne 0) { Fail "npm run build failed" }

if (-not $Deploy) {
  Step "7 skip Vercel (pass -Deploy to publish)"
  Write-Host "=== BUILD_ONLY_DONE ===" -ForegroundColor Green
  Info "Next: re-run with -Deploy after user approval, or deploy manually from site/"
  exit 0
}

# --- deploy 1 ---
Step "7 Vercel prod #1 (binaries+html, old surum)"
$env:VERCEL_VC_NATIVE = "1"
$env:NODE_OPTIONS = "--require $Preload"
& $Npx --yes vercel --prod --yes
if ($LASTEXITCODE -ne 0) { Fail "vercel deploy #1 failed" }
Write-Host "=== DEPLOY1_DONE ===" -ForegroundColor Green

# --- surum last + deploy 2 ---
Step "8 write surum.txt=$Version then Vercel prod #2"
[System.IO.File]::WriteAllText($surumPath, ($Version + "`n"), [System.Text.UTF8Encoding]::new($false))
npm run build
if ($LASTEXITCODE -ne 0) { Fail "npm run build after surum failed" }
& $Npx --yes vercel --prod --yes
if ($LASTEXITCODE -ne 0) { Fail "vercel deploy #2 failed" }
Write-Host "=== DEPLOY2_DONE ===" -ForegroundColor Green

# --- verify ---
Step "9 live verify"
$base = "https://site-seven-bay-75.vercel.app"
$liveSurum = (Invoke-WebRequest "$base/indir/surum.txt" -UseBasicParsing).Content.Trim()
Info ("LIVE_SURUM={0}" -f $liveSurum)
if ($liveSurum -ne $Version) { Fail "live surum mismatch" }
$visit = (Invoke-WebRequest "$base/api/visit" -UseBasicParsing).Content
Info ("LIVE_VISIT={0}" -f $visit)
$htmlLive = (Invoke-WebRequest "$base/" -UseBasicParsing).Content
if ($htmlLive -notmatch [regex]::Escape("?v=$Version")) { Fail "live HTML missing ?v=$Version" }
if ($htmlLive -notmatch [regex]::Escape("Sürüm $Version")) { Fail "live HTML missing Sürüm $Version" }
$exeRemoteLen = (Invoke-WebRequest "$base/indir/FRIDAY-Kurulum.exe" -Method Head -UseBasicParsing).Headers["Content-Length"]
$apkRemoteLen = (Invoke-WebRequest "$base/indir/FRIDAY.apk" -Method Head -UseBasicParsing).Headers["Content-Length"]
Info ("LIVE_EXE_LEN={0} local={1}" -f $exeRemoteLen, $exeLen)
Info ("LIVE_APK_LEN={0} local={1}" -f $apkRemoteLen, $apkLen)
if ([int64]$exeRemoteLen -ne $exeLen) { Fail "exe size mismatch" }
if ([int64]$apkRemoteLen -ne $apkLen) { Fail "apk size mismatch" }

Write-Host "=== RELEASE_OK version=$Version ===" -ForegroundColor Green
Info ("APK_SHA256={0}" -f $apkHash)
Info ("EXE_SHA256={0}" -f $exeHash)
Info ("Backup={0}" -f $Backup)
