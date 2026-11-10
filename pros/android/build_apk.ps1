# Package the Android build of MLB Bobblehead Pros into a debug-signed APK, without Gradle.
#   aapt2 compile/link (resources + manifest) -> javac (SDL's Java + our activity) -> d8
#   -> add classes.dex + stripped .so libs -> zipalign -> apksigner.
#
# The game .so must already be built:
#   cmake --build pros/out/build/android-arm64 --target bobbleheadpros   (-> libmain.so)
#
# Usage:  powershell -ExecutionPolicy Bypass -File build_apk.ps1 [-Install]
# Output: pros/android/out/MLBBobbleheadPros.apk
param([switch]$Install)
$ErrorActionPreference = 'Stop'

# --- tools ---------------------------------------------------------------------------------------
$SDK   = "$env:LOCALAPPDATA\Android\Sdk"
$NDK   = "$SDK\ndk\30.0.16248370"
$BT    = "$SDK\build-tools\36.0.0"
$JAR   = "$SDK\platforms\android-34\android.jar"
$JAVA  = "C:\Program Files\Android\Android Studio\jbr\bin"           # JDK 17+ (JBR); default java is 8
$NDKBIN = "$NDK\toolchains\llvm\prebuilt\windows-x86_64\bin"
# d8.bat / apksigner.bat launch `%JAVA_HOME%\bin\java` (or bare `java`); the machine default is
# Java 8, too old for d8/apksigner. Point them at the JBR for this process only.
$env:JAVA_HOME = Split-Path $JAVA -Parent
$env:PATH = "$JAVA;$env:PATH"
$LIBCXX = "$NDK\toolchains\llvm\prebuilt\windows-x86_64\sysroot\usr\lib\aarch64-linux-android\libc++_shared.so"

# --- inputs --------------------------------------------------------------------------------------
$HERE    = $PSScriptRoot
$GAME_SO = "$HERE\..\out\build\android-arm64\libmain.so"
$SDK_LIB = "D:\recomp-work\rexglue-sdk\out\install\android-arm64\lib"
$SDL_JAVA = "D:\recomp-work\rexglue-sdk\thirdparty\sdl3\android-project\app\src\main\java"
$MANIFEST = "$HERE\AndroidManifest.xml"
$RES      = "$HERE\res"
$KEY      = "$HERE\out\debug.keystore"
$NAME     = "MLBBobbleheadPros"

foreach ($p in @($GAME_SO, "$SDK_LIB\librexruntime.so", "$SDK_LIB\librexgpu-xenos.so", $LIBCXX, $JAR)) {
    if (-not (Test-Path $p)) { throw "missing input: $p" }
}

$OUT = "$HERE\out"
$W   = "$OUT\work"
Remove-Item $W -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $W,"$W\classes","$W\lib\arm64-v8a" | Out-Null

# --- resources -----------------------------------------------------------------------------------
Write-Host "[1/6] aapt2 compile + link resources"
& "$BT\aapt2.exe" compile --dir $RES -o "$W\res.zip"
if ($LASTEXITCODE) { throw "aapt2 compile failed" }
& "$BT\aapt2.exe" link -o "$W\base.apk" --manifest $MANIFEST -I $JAR `
    "$W\res.zip" --min-sdk-version 30 --target-sdk-version 34 --auto-add-overlay
if ($LASTEXITCODE) { throw "aapt2 link failed" }

# --- java -> dex ---------------------------------------------------------------------------------
Write-Host "[2/6] javac (SDL + activity)"
$srcs = @()
$srcs += Get-ChildItem $SDL_JAVA -Recurse -Filter '*.java' | ForEach-Object { $_.FullName }
$srcs += Get-ChildItem "$HERE\java" -Recurse -Filter '*.java' | ForEach-Object { $_.FullName }
$srcList = "$W\sources.txt"
[System.IO.File]::WriteAllLines($srcList, $srcs)  # no BOM: javac @argfile rejects it
& "$JAVA\javac.exe" --release 17 -nowarn -classpath $JAR -d "$W\classes" "@$srcList"
if ($LASTEXITCODE) { throw "javac failed" }

Write-Host "[3/6] d8 -> classes.dex"
$classes = Get-ChildItem "$W\classes" -Recurse -Filter '*.class' | ForEach-Object { $_.FullName }
$clsList = "$W\classes.txt"
[System.IO.File]::WriteAllLines($clsList, $classes)  # no BOM
& "$BT\d8.bat" --release --min-api 30 --lib $JAR --output $W "@$clsList"
if ($LASTEXITCODE) { throw "d8 failed" }

# --- native libs (stripped) ----------------------------------------------------------------------
Write-Host "[4/6] stage + strip native libs"
Copy-Item $GAME_SO "$W\lib\arm64-v8a\libmain.so"
Copy-Item "$SDK_LIB\librexruntime.so"   "$W\lib\arm64-v8a\"
Copy-Item "$SDK_LIB\librexgpu-xenos.so" "$W\lib\arm64-v8a\"
Copy-Item $LIBCXX "$W\lib\arm64-v8a\libc++_shared.so"
& "$NDKBIN\llvm-strip.exe" --strip-debug (Get-ChildItem "$W\lib\arm64-v8a\*.so" | ForEach-Object { $_.FullName })
if ($LASTEXITCODE) { throw "strip failed" }

# --- assemble (classes.dex compressed, .so stored) -----------------------------------------------
Write-Host "[5/6] assemble apk"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$unaligned = "$W\unaligned.apk"
Copy-Item "$W\base.apk" $unaligned
$zip = [System.IO.Compression.ZipFile]::Open($unaligned, [System.IO.Compression.ZipArchiveMode]::Update)
try {
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$W\classes.dex", "classes.dex", [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    foreach ($so in Get-ChildItem "$W\lib\arm64-v8a\*.so") {
        # Stored (no compression) so zipalign -P 16 can page-align it for the loader.
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $so.FullName, "lib/arm64-v8a/$($so.Name)", [System.IO.Compression.CompressionLevel]::NoCompression) | Out-Null
    }
} finally { $zip.Dispose() }

$aligned = "$W\aligned.apk"
& "$BT\zipalign.exe" -f -P 16 4 $unaligned $aligned
if ($LASTEXITCODE) { throw "zipalign failed" }

# --- sign ----------------------------------------------------------------------------------------
Write-Host "[6/6] sign"
if (-not (Test-Path $KEY)) {
    & "$JAVA\keytool.exe" -genkeypair -keystore $KEY -storepass android -keypass android `
        -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
    if ($LASTEXITCODE) { throw "keytool failed" }
}
$apk = "$OUT\$NAME.apk"
& "$BT\apksigner.bat" sign --ks $KEY --ks-pass pass:android --key-pass pass:android --out $apk $aligned
if ($LASTEXITCODE) { throw "apksigner failed" }
Remove-Item $W -Recurse -Force -ErrorAction SilentlyContinue

$mb = [math]::Round((Get-Item $apk).Length / 1MB, 1)
Write-Host "APK: $apk  ($mb MB)"
if ($Install) {
    & "$SDK\platform-tools\adb.exe" install -r $apk
}
