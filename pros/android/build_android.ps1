# Build the Android (arm64-v8a) version of MLB Bobblehead Pros and package it as a debug APK.
#
#   1. ReXGlue SDK runtime for Android  -> <sdk>\out\install\android-arm64
#   2. The game, as libmain.so          -> pros\out\build\android-arm64\libmain.so
#   3. APK (no Gradle): aapt2 -> javac (SDL's Java + our activity) -> d8 -> zip -> zipalign -> apksigner
#                                        -> pros\android\out\MLBBobbleheadPros.apk
#
# Before running:
#   - The SDK checkout has both sdk-patches applied (rexglue-sdk-local.patch, then
#     rexglue-sdk-android.patch) and the Windows SDK is built + installed (its rexglue.exe
#     runs the codegen step). See sdk-patches\README.md.
#   - The Windows build of Pros has run codegen once (pros\generated\default\ exists).
#   - Android Studio (or the Android SDK command-line tools) with an NDK, build-tools and a
#     platform installed; a JDK 17+ (Android Studio's bundled JBR is found automatically).
#
# The APK contains the recompiled game: build it from your own copy of the game, keep it to
# yourself, and never publish it.
#
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File pros\android\build_android.ps1 -SdkSource <rexglue-sdk>
#   ... -SkipSdk      reuse the existing Android SDK install
#   ... -Install      adb install -r the APK afterwards
param(
    [string]$SdkSource = $env:REXGLUE_SDK,
    [string]$AndroidSdk = $(if ($env:ANDROID_HOME) { $env:ANDROID_HOME } elseif ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { "$env:LOCALAPPDATA\Android\Sdk" }),
    [string]$Ndk = $env:ANDROID_NDK_HOME,
    [string]$Jdk = "",
    [int]$MinApi = 30,
    [switch]$SkipSdk,
    [switch]$Install
)
$ErrorActionPreference = 'Stop'

function Fail($msg) { throw "build_android: $msg" }
function Newest($dir, $filter = '*') {
    if (-not (Test-Path $dir)) { return $null }
    Get-ChildItem $dir -Directory -Filter $filter |
        Sort-Object { [version](($_.Name -replace '^android-', '') -replace '[^0-9.].*$', '' -replace '^(\d+)$', '$1.0') } |
        Select-Object -Last 1
}
function Run($exe) {
    & $exe @args
    if ($LASTEXITCODE) { Fail "$(Split-Path $exe -Leaf) failed (exit $LASTEXITCODE)" }
}

# --- locate everything ---------------------------------------------------------------------------
$Pros = Split-Path $PSScriptRoot -Parent
if (-not $SdkSource) { $SdkSource = Join-Path (Split-Path (Split-Path $Pros -Parent) -Parent) 'rexglue-sdk' }
if (-not (Test-Path "$SdkSource\CMakeLists.txt")) { Fail "ReXGlue SDK not found at '$SdkSource' (pass -SdkSource)" }
$SdkSource = (Resolve-Path $SdkSource).Path

if (-not (Test-Path $AndroidSdk)) { Fail "Android SDK not found at '$AndroidSdk' (pass -AndroidSdk or set ANDROID_HOME)" }
if (-not $Ndk) { $n = Newest "$AndroidSdk\ndk"; if ($n) { $Ndk = $n.FullName } }
if (-not $Ndk -or -not (Test-Path "$Ndk\build\cmake\android.toolchain.cmake")) { Fail "Android NDK not found (install one in Android Studio's SDK Manager, or pass -Ndk)" }
$Bt = (Newest "$AndroidSdk\build-tools").FullName
if (-not $Bt) { Fail "no Android build-tools installed" }
$Platform = Get-ChildItem "$AndroidSdk\platforms" -Directory | Where-Object { Test-Path "$($_.FullName)\android.jar" } |
    Sort-Object { [double](($_.Name -replace '^android-', '') -replace '[^0-9.].*$', '') } | Select-Object -Last 1
if (-not $Platform) { Fail "no Android platform (android.jar) installed" }
$Jar = "$($Platform.FullName)\android.jar"
$TargetApi = [int](($Platform.Name -replace '^android-', '') -replace '\..*$', '')

if (-not $Jdk) {
    foreach ($c in @("$env:ProgramFiles\Android\Android Studio\jbr", "$env:LOCALAPPDATA\Programs\Android Studio\jbr", $env:JAVA_HOME)) {
        if ($c -and (Test-Path "$c\bin\javac.exe")) { $Jdk = $c; break }
    }
}
if (-not $Jdk -or -not (Test-Path "$Jdk\bin\javac.exe")) { Fail "no JDK found (pass -Jdk; JDK 17+ needed)" }
# d8.bat / apksigner.bat use JAVA_HOME (or the first java on PATH): make it this JDK.
$env:JAVA_HOME = $Jdk
$env:PATH = "$Jdk\bin;$env:PATH"

$Cmake = (Get-Command cmake -ErrorAction SilentlyContinue).Source
$CmakeDir = Newest "$AndroidSdk\cmake"
if (-not $Cmake -and $CmakeDir) { $Cmake = "$($CmakeDir.FullName)\bin\cmake.exe" }
$Ninja = (Get-Command ninja -ErrorAction SilentlyContinue).Source
if (-not $Ninja -and $CmakeDir) { $Ninja = "$($CmakeDir.FullName)\bin\ninja.exe" }
if (-not $Cmake -or -not (Test-Path $Cmake)) { Fail "cmake not found" }
if (-not $Ninja -or -not (Test-Path $Ninja)) { Fail "ninja not found (install CMake from Android Studio's SDK Manager)" }

$HostTool = "$SdkSource\out\install\win-amd64\bin\rexglue.exe"
if (-not (Test-Path $HostTool)) { Fail "Windows SDK install missing ($HostTool): build + install the SDK for Windows first" }

$NdkBin = "$Ndk\toolchains\llvm\prebuilt\windows-x86_64\bin"
$LibCxx = "$Ndk\toolchains\llvm\prebuilt\windows-x86_64\sysroot\usr\lib\aarch64-linux-android\libc++_shared.so"
$SdkBuild = "$SdkSource\out\build\android-arm64"
$SdkInstall = "$SdkSource\out\install\android-arm64"
$GameBuild = "$Pros\out\build\android-arm64"
$Toolchain = @("-DCMAKE_TOOLCHAIN_FILE=$Ndk\build\cmake\android.toolchain.cmake",
               "-DANDROID_ABI=arm64-v8a", "-DANDROID_PLATFORM=android-$MinApi", "-DANDROID_STL=c++_shared",
               "-DCMAKE_BUILD_TYPE=Release", "-G", "Ninja", "-DCMAKE_MAKE_PROGRAM=$Ninja")

Write-Host "SDK source : $SdkSource"
Write-Host "NDK        : $Ndk"
Write-Host "Platform   : $($Platform.Name)   build-tools: $(Split-Path $Bt -Leaf)   JDK: $Jdk"

# --- 1. SDK runtime for Android ------------------------------------------------------------------
if (-not $SkipSdk) {
    Write-Host "`n[1/3] ReXGlue SDK (android-arm64)"
    Run $Cmake -S $SdkSource -B $SdkBuild @Toolchain `
        -DREXGLUE_ENABLE_TRACY=OFF -DREXGLUE_BUILD_TESTS=OFF -DREXGLUE_USE_D3D12=OFF -DREXGLUE_USE_VULKAN=ON
    Run $Cmake --build $SdkBuild
    Run $Cmake --install $SdkBuild --prefix $SdkInstall
}
if (-not (Test-Path "$SdkInstall\lib\cmake\rexglue")) { Fail "Android SDK install missing at $SdkInstall" }

# --- 2. the game (libmain.so) --------------------------------------------------------------------
Write-Host "`n[2/3] Pros -> libmain.so"
Run $Cmake -S $Pros -B $GameBuild @Toolchain `
    "-Drexglue_DIR=$SdkInstall\lib\cmake\rexglue" "-DSDL3_DIR=$SdkInstall\lib\cmake\SDL3" `
    "-DCMAKE_FIND_ROOT_PATH=$SdkInstall" "-DREXGLUE_HOST_TOOL=$HostTool" `
    -DCMAKE_FIND_PACKAGE_NO_PACKAGE_REGISTRY=ON
Run $Cmake --build $GameBuild --target bobbleheadpros
$GameSo = "$GameBuild\libmain.so"
if (-not (Test-Path $GameSo)) { Fail "libmain.so was not produced" }

# --- 3. APK --------------------------------------------------------------------------------------
Write-Host "`n[3/3] APK"
$Out = "$PSScriptRoot\out"
$W = "$Out\work"
Remove-Item $W -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path "$W\classes", "$W\lib\arm64-v8a" | Out-Null

Run "$Bt\aapt2.exe" compile --dir "$PSScriptRoot\res" -o "$W\res.zip"
Run "$Bt\aapt2.exe" link -o "$W\base.apk" --manifest "$PSScriptRoot\AndroidManifest.xml" -I $Jar "$W\res.zip" `
    --min-sdk-version $MinApi --target-sdk-version $TargetApi --auto-add-overlay

# SDL's own Java layer (from the SDK's SDL3 copy) plus our activity.
$SdlJava = "$SdkSource\thirdparty\sdl3\android-project\app\src\main\java"
if (-not (Test-Path $SdlJava)) { Fail "SDL3 Java sources not found at $SdlJava" }
$sources = @(Get-ChildItem $SdlJava, "$PSScriptRoot\java" -Recurse -Filter '*.java' | ForEach-Object { $_.FullName })
[IO.File]::WriteAllLines("$W\sources.txt", $sources)   # no BOM: javac's @file rejects one
Run "$Jdk\bin\javac.exe" --release 17 -nowarn -classpath $Jar -d "$W\classes" "@$W\sources.txt"
$classes = @(Get-ChildItem "$W\classes" -Recurse -Filter '*.class' | ForEach-Object { $_.FullName })
[IO.File]::WriteAllLines("$W\classes.txt", $classes)
Run "$Bt\d8.bat" --release --min-api $MinApi --lib $Jar --output $W "@$W\classes.txt"

# Native libraries: the game, every shared library the SDK install provides, and the C++ runtime.
Copy-Item $GameSo "$W\lib\arm64-v8a\libmain.so"
Get-ChildItem "$SdkInstall\lib" -Filter '*.so' | ForEach-Object { Copy-Item $_.FullName "$W\lib\arm64-v8a\" }
Copy-Item $LibCxx "$W\lib\arm64-v8a\"
Run "$NdkBin\llvm-strip.exe" --strip-debug @(Get-ChildItem "$W\lib\arm64-v8a\*.so" | ForEach-Object { $_.FullName })
Write-Host ("libraries: " + ((Get-ChildItem "$W\lib\arm64-v8a\*.so").Name -join ', '))

Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
Copy-Item "$W\base.apk" "$W\unaligned.apk"
$zip = [IO.Compression.ZipFile]::Open("$W\unaligned.apk", [IO.Compression.ZipArchiveMode]::Update)
try {
    [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$W\classes.dex", "classes.dex", [IO.Compression.CompressionLevel]::Optimal)
    foreach ($so in Get-ChildItem "$W\lib\arm64-v8a\*.so") {
        # Stored, not compressed: the loader maps .so files straight out of the APK.
        [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $so.FullName, "lib/arm64-v8a/$($so.Name)", [IO.Compression.CompressionLevel]::NoCompression)
    }
} finally { $zip.Dispose() }
Run "$Bt\zipalign.exe" -f -P 16 4 "$W\unaligned.apk" "$W\aligned.apk"   # 16 KB page alignment for .so

$Key = "$Out\debug.keystore"
if (-not (Test-Path $Key)) {
    Run "$Jdk\bin\keytool.exe" -genkeypair -keystore $Key -storepass android -keypass android -alias androiddebugkey `
        -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
}
$Apk = "$Out\MLBBobbleheadPros.apk"
Run "$Bt\apksigner.bat" sign --ks $Key --ks-pass pass:android --key-pass pass:android --out $Apk "$W\aligned.apk"
Remove-Item $W -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ("`nAPK: $Apk  ({0:N1} MB)" -f ((Get-Item $Apk).Length / 1MB))

if ($Install) { Run "$AndroidSdk\platform-tools\adb.exe" install -r $Apk }
