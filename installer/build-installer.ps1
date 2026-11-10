<#
  build-installer.ps1 - package MLB Bobblehead Recomp for release.

  Produces, in installer\dist\:
    MLB-Bobblehead-Recomp-<ver>-setup.exe    (Inno Setup installer)
    MLB-Bobblehead-Recomp-<ver>-portable.zip (unzip-and-run bundle)
    SHA256SUMS.txt                           (checksums for both)

  Prereqs: both games built (pros\ and battle\ out\build\win-amd64-release),
  the launcher built (launcher\MLB Bobblehead Launcher.exe), and Inno Setup 6
  (ISCC.exe) installed. Run from anywhere; paths are resolved from this script.
#>
[CmdletBinding()]
param(
    [string]$Version = "0.1.0",
    [switch]$SkipLauncherBuild
)
$ErrorActionPreference = 'Stop'

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot     = Split-Path -Parent $InstallerDir
$Dist         = Join-Path $InstallerDir 'dist'
$Launcher     = 'MLB Bobblehead Launcher.exe'
$LauncherExe  = Join-Path $RepoRoot "launcher\$Launcher"
$ProsBuild    = Join-Path $RepoRoot 'pros\out\build\win-amd64-release'
$BattleBuild  = Join-Path $RepoRoot 'battle\out\build\win-amd64-release'

function Find-ISCC {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "ISCC.exe (Inno Setup 6) not found. Install it: winget install JRSoftware.InnoSetup"
}

# --- Build the launcher ---------------------------------------------------
if (-not $SkipLauncherBuild) {
    $csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if (-not (Test-Path $csc)) { throw "csc.exe not found at $csc" }
    Write-Host "Building launcher..." -ForegroundColor Cyan
    Push-Location (Join-Path $RepoRoot 'launcher')
    & $csc -nologo -target:winexe -out:$Launcher -r:System.Windows.Forms.dll -r:System.Drawing.dll `
        -r:System.IO.Compression.dll -r:System.IO.Compression.FileSystem.dll -r:System.Management.dll Launcher.cs
    Pop-Location
    if ($LASTEXITCODE -ne 0) { throw "Launcher build failed." }
}

# --- Sanity checks --------------------------------------------------------
$required = @(
    $LauncherExe,
    (Join-Path $ProsBuild   'bobbleheadpros.exe'),
    (Join-Path $ProsBuild   'rexruntime.dll'),
    (Join-Path $ProsBuild   'rexgpu-xenos.dll'),
    (Join-Path $BattleBuild 'bobbleheadbattle.exe'),
    (Join-Path $BattleBuild 'rexruntime.dll'),
    (Join-Path $BattleBuild 'rexgpu-xenos.dll'),
    (Join-Path $InstallerDir 'assets\pros.ico'),
    (Join-Path $InstallerDir 'assets\battle.ico'),
    (Join-Path $RepoRoot 'launcher\art\pros.png'),
    (Join-Path $RepoRoot 'launcher\art\battle.png')
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    $msg = "Missing build inputs:`n  " + ($missing -join "`n  ")
    if ($missing -match '\.ico$') { $msg += "`n`nGenerate the icons first:  installer\make-icons.ps1" }
    throw $msg
}

New-Item -ItemType Directory -Force -Path $Dist | Out-Null

# --- Compile the installer ------------------------------------------------
$iscc = Find-ISCC
Write-Host "Compiling installer with $iscc ..." -ForegroundColor Cyan
& $iscc "/DAppVersion=$Version" (Join-Path $InstallerDir 'MLBBobble.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC failed." }

# --- Build the portable zip ----------------------------------------------
Write-Host "Building portable zip..." -ForegroundColor Cyan
$stage = Join-Path $Dist '_portable'
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage, "$stage\pros", "$stage\battle", "$stage\icons", "$stage\art" | Out-Null

Copy-Item $LauncherExe $stage
Copy-Item (Join-Path $InstallerDir 'assets\pros.ico')   "$stage\icons"
Copy-Item (Join-Path $InstallerDir 'assets\battle.ico') "$stage\icons"
Copy-Item (Join-Path $RepoRoot 'launcher\art\pros.png')   "$stage\art"
Copy-Item (Join-Path $RepoRoot 'launcher\art\battle.png') "$stage\art"
foreach ($f in 'bobbleheadpros.exe','rexruntime.dll','rexgpu-xenos.dll','bobbleheadpros.toml') {
    Copy-Item (Join-Path $ProsBuild $f) "$stage\pros"
}
foreach ($f in 'bobbleheadbattle.exe','rexruntime.dll','rexgpu-xenos.dll','bobbleheadbattle.toml') {
    Copy-Item (Join-Path $BattleBuild $f) "$stage\battle"
}
if (Test-Path (Join-Path $RepoRoot 'README.md')) { Copy-Item (Join-Path $RepoRoot 'README.md') $stage }

$zip = Join-Path $Dist "MLB-Bobblehead-Recomp-$Version-portable.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path "$stage\*" -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $stage -Recurse -Force

# --- Checksums ------------------------------------------------------------
Write-Host "Writing checksums..." -ForegroundColor Cyan
$setup = Join-Path $Dist "MLB-Bobblehead-Recomp-$Version-setup.exe"
$sums  = Join-Path $Dist 'SHA256SUMS.txt'
$lines = @()
foreach ($artifact in @($setup, $zip)) {
    if (Test-Path $artifact) {
        $h = (Get-FileHash $artifact -Algorithm SHA256).Hash.ToLower()
        $lines += "$h  $(Split-Path $artifact -Leaf)"
    }
}
$lines | Set-Content -Path $sums -Encoding ascii

Write-Host "`nDone. Artifacts in $Dist :" -ForegroundColor Green
Get-ChildItem $Dist -File | Where-Object { $_.Name -notlike '_*' } |
    Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,2)}} | Format-Table -Auto
