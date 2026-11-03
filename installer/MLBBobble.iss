; MLB Bobblehead Recomp - Inno Setup installer
; Builds <OutputBaseFilename>-setup.exe which installs the launcher + both
; recompiled games into Program Files and registers Start-Menu "app" entries
; (one per game, each with its own logo .ico) plus an Installed-apps / Programs
; and Features uninstall entry. The games are launched through the launcher,
; which locates each title's data root (bring-your-own game files).
;
; Compile:  ISCC.exe MLBBobble.iss  (or run installer\build-installer.ps1)

#define AppName    "MLB Bobblehead Recomp"
#define AppVersion "1.0.0"
#define AppPublisher "MLBBobble-recomp"
#define AppURL     "https://github.com/Wndwsqrrl/MLBBobble-recomp"
#define Launcher   "MLB Bobblehead Launcher.exe"

; SrcRoot is the repo root, relative to this .iss (which lives in installer\).
#define SrcRoot    "..\"
#define ProsBuild  SrcRoot + "pros\out\build\win-amd64-release"
#define BattleBuild SrcRoot + "battle\out\build\win-amd64-release"

[Setup]
AppId={{E770C84E-0D51-4FC8-AD4C-0D4AEC93E7F3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\MLB Bobblehead
DefaultGroupName=MLB Bobblehead
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\icons\pros.ico
OutputDir=dist
OutputBaseFilename=MLB-Bobblehead-Recomp-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts for both games"; GroupDescription: "Additional shortcuts:"

[Files]
; Launcher
Source: "{#SrcRoot}launcher\{#Launcher}"; DestDir: "{app}"; Flags: ignoreversion
; Launcher card box art (loaded from {app}\art by the launcher)
Source: "{#SrcRoot}launcher\art\pros.png";   DestDir: "{app}\art"; Flags: ignoreversion
Source: "{#SrcRoot}launcher\art\battle.png"; DestDir: "{app}\art"; Flags: ignoreversion
; Icons (used by the shortcuts and the uninstall entry)
Source: "assets\pros.ico";   DestDir: "{app}\icons"; Flags: ignoreversion
Source: "assets\battle.ico"; DestDir: "{app}\icons"; Flags: ignoreversion
; Pros game binaries
Source: "{#ProsBuild}\bobbleheadpros.exe"; DestDir: "{app}\pros"; Flags: ignoreversion
Source: "{#ProsBuild}\rexruntime.dll";     DestDir: "{app}\pros"; Flags: ignoreversion
Source: "{#ProsBuild}\rexgpu-xenos.dll";   DestDir: "{app}\pros"; Flags: ignoreversion
Source: "{#ProsBuild}\bobbleheadpros.toml"; DestDir: "{app}\pros"; Flags: ignoreversion
; Battle game binaries
Source: "{#BattleBuild}\bobbleheadbattle.exe"; DestDir: "{app}\battle"; Flags: ignoreversion
Source: "{#BattleBuild}\rexruntime.dll";       DestDir: "{app}\battle"; Flags: ignoreversion
Source: "{#BattleBuild}\rexgpu-xenos.dll";     DestDir: "{app}\battle"; Flags: ignoreversion
Source: "{#BattleBuild}\bobbleheadbattle.toml"; DestDir: "{app}\battle"; Flags: ignoreversion

[Icons]
; Start-Menu "apps" (All apps list) - one per game, each with its own logo.
; They launch through the launcher, which supplies each game's data root.
Name: "{autoprograms}\MLB Bobblehead Pros";   Filename: "{app}\{#Launcher}"; Parameters: "--play pros";   IconFilename: "{app}\icons\pros.ico";   WorkingDir: "{app}"; Comment: "Play MLB Bobblehead Pros"
Name: "{autoprograms}\MLB Bobblehead Battle"; Filename: "{app}\{#Launcher}"; Parameters: "--play battle"; IconFilename: "{app}\icons\battle.ico"; WorkingDir: "{app}"; Comment: "Play MLB Bobblehead Battle"
Name: "{autoprograms}\MLB Bobblehead Launcher"; Filename: "{app}\{#Launcher}"; IconFilename: "{app}\icons\pros.ico"; WorkingDir: "{app}"; Comment: "Open the MLB Bobblehead launcher"
; Desktop (optional)
Name: "{autodesktop}\MLB Bobblehead Pros";   Filename: "{app}\{#Launcher}"; Parameters: "--play pros";   IconFilename: "{app}\icons\pros.ico";   WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\MLB Bobblehead Battle"; Filename: "{app}\{#Launcher}"; Parameters: "--play battle"; IconFilename: "{app}\icons\battle.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
; Also list each game as its own entry in Settings > Installed apps / Programs
; and Features, with its own logo. Both point at the shared uninstaller (the
; games share the launcher + runtime), and the keys are removed on uninstall.
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; Flags: uninsdeletekey; ValueType: string; ValueName: "DisplayName";     ValueData: "MLB Bobblehead Pros"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; ValueType: string; ValueName: "DisplayIcon";     ValueData: "{app}\icons\pros.ico"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; ValueType: string; ValueName: "DisplayVersion";  ValueData: "{#AppVersion}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; ValueType: string; ValueName: "Publisher";       ValueData: "{#AppPublisher}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; ValueType: string; ValueName: "InstallLocation"; ValueData: "{app}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; ValueType: string; ValueName: "UninstallString"; ValueData: "{uninstallexe}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; ValueType: dword;  ValueName: "NoModify"; ValueData: "1"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadPros"; ValueType: dword;  ValueName: "NoRepair"; ValueData: "1"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; Flags: uninsdeletekey; ValueType: string; ValueName: "DisplayName";   ValueData: "MLB Bobblehead Battle"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; ValueType: string; ValueName: "DisplayIcon";    ValueData: "{app}\icons\battle.ico"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{#AppVersion}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; ValueType: string; ValueName: "Publisher";      ValueData: "{#AppPublisher}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; ValueType: string; ValueName: "InstallLocation"; ValueData: "{app}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; ValueType: string; ValueName: "UninstallString"; ValueData: "{uninstallexe}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; ValueType: dword;  ValueName: "NoModify"; ValueData: "1"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\MLBBobbleheadBattle"; ValueType: dword;  ValueName: "NoRepair"; ValueData: "1"

[Run]
Filename: "{app}\{#Launcher}"; Description: "Launch MLB Bobblehead now"; Flags: nowait postinstall skipifsilent
