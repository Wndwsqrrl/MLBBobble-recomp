<#
  make-icons.ps1 - generate installer\assets\pros.ico and battle.ico from each
  game's own TitleIcon.png.

  These icons are DERIVED FROM COPYRIGHTED GAME ART, so they are not committed
  to the repository (same policy as launcher\art\). Generate them locally from
  your own extracted game data before building the installer.

  Usage (defaults point at the typical dump locations; override as needed):
    .\make-icons.ps1 -ProsData "D:\Games\Xbox 360\MLB Bobblehead Pros (World) (XBLA)" `
                     -BattleData "D:\Games\Xbox 360\MLB Bobblehead Battle (World) (XBLA)\extracted"

  TitleIcon.png is searched for at the root of the given folder and one level
  down (so either the dump root or its 'extracted' subfolder works).
#>
[CmdletBinding()]
param(
    [string]$ProsData   = "D:\Games\Xbox 360\MLB Bobblehead Pros (World) (XBLA)",
    [string]$BattleData = "D:\Games\Xbox 360\MLB Bobblehead Battle (World) (XBLA)\extracted"
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AssetDir     = Join-Path $InstallerDir 'assets'
New-Item -ItemType Directory -Force -Path $AssetDir | Out-Null

function Find-TitleIcon([string]$root) {
    $direct = Join-Path $root 'TitleIcon.png'
    if (Test-Path $direct) { return $direct }
    $hit = Get-ChildItem $root -Recurse -Depth 1 -Filter 'TitleIcon.png' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($hit) { return $hit.FullName }
    throw "TitleIcon.png not found under '$root'."
}

function New-Ico([string]$srcPng, [string]$outIco) {
    $sizes = 16,24,32,48,64,128,256
    $src = [System.Drawing.Bitmap]::new($srcPng)
    try {
        $pngs = @()
        foreach ($s in $sizes) {
            $bmp = [System.Drawing.Bitmap]::new($s, $s, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $g = [System.Drawing.Graphics]::FromImage($bmp)
            $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g.PixelOffsetMode   = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $g.DrawImage($src, 0, 0, $s, $s)
            $g.Dispose()
            $ms = [System.IO.MemoryStream]::new()
            $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
            $bmp.Dispose()
            $pngs += ,@{ Size = $s; Bytes = $ms.ToArray() }
            $ms.Dispose()
        }
    } finally { $src.Dispose() }

    $fs = [System.IO.File]::Create($outIco)
    $bw = [System.IO.BinaryWriter]::new($fs)
    try {
        # ICONDIR
        $bw.Write([uint16]0)              # reserved
        $bw.Write([uint16]1)              # type = icon
        $bw.Write([uint16]$pngs.Count)    # image count
        # ICONDIRENTRY table
        $offset = 6 + 16 * $pngs.Count
        foreach ($p in $pngs) {
            $dim = if ($p.Size -ge 256) { [byte]0 } else { [byte]$p.Size }
            $bw.Write($dim)               # width
            $bw.Write($dim)               # height
            $bw.Write([byte]0)            # palette count
            $bw.Write([byte]0)            # reserved
            $bw.Write([uint16]1)          # color planes
            $bw.Write([uint16]32)         # bits per pixel
            $bw.Write([uint32]$p.Bytes.Length)
            $bw.Write([uint32]$offset)
            $offset += $p.Bytes.Length
        }
        foreach ($p in $pngs) { $bw.Write($p.Bytes) }
    } finally { $bw.Dispose(); $fs.Dispose() }
    Write-Host "  $outIco  ($([math]::Round((Get-Item $outIco).Length/1KB)) KB, $($pngs.Count) sizes)"
}

Write-Host "Generating icons:" -ForegroundColor Cyan
New-Ico (Find-TitleIcon $ProsData)   (Join-Path $AssetDir 'pros.ico')
New-Ico (Find-TitleIcon $BattleData) (Join-Path $AssetDir 'battle.ico')
Write-Host "Done." -ForegroundColor Green
