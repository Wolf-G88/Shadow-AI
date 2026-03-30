#define MyAppName "Shadow AI"
#define MyAppVersion "V1.00"
#define MyAppNumericVersion "1.0.0.0"
#define MyAppPublisher "Wolf Clan"
#define MyAppExeName "ShadowAI.exe"
#define MyAppId "{{E2B2B35B-24AF-4B9A-B7C3-2B25C4F99275}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
SetupIconFile=..\ShadowAI.ico
DefaultDirName={autopf}\Shadow AI
DefaultGroupName=Shadow AI
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=shadow-ai-windows-v1.00-full-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoProductVersion={#MyAppNumericVersion}
VersionInfoVersion={#MyAppNumericVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\ShadowAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Shadow AI"; Filename: "{app}\ShadowAI.exe"
Name: "{autodesktop}\Shadow AI"; Filename: "{app}\ShadowAI.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ShadowAI.exe"; Description: "{cm:LaunchProgram,Shadow AI}"; Flags: nowait postinstall skipifsilent
