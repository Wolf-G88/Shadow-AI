#define MyAppName "Shadow AI"
#define MyAppVersion "V1.00"
#define MyAppNumericVersion "1.0.0.0"
#define MyAppPublisher "Wolf Clan"
#define MyAppURL "https://github.com/Wolf-G88/Shadow-AI"
#define MyAppId "{{A5F48613-5FCB-4A9A-B644-C9A4A1F49775}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
SetupIconFile=..\ShadowAI.ico
DefaultDirName={autopf}\Shadow AI
DefaultGroupName=Shadow AI
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=shadow-ai-windows-v1.00-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Shadow AI thin Windows installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppNumericVersion}
VersionInfoVersion={#MyAppNumericVersion}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\ShadowAI.ico
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\shadow-ai-windows-v1.00\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Shadow AI"; Filename: "{app}\run_windows.vbs"; IconFilename: "{app}\ShadowAI.ico"
Name: "{autodesktop}\Shadow AI"; Filename: "{app}\run_windows.vbs"; Tasks: desktopicon; IconFilename: "{app}\ShadowAI.ico"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install_windows.ps1"" -AutoInstallPython"; StatusMsg: "Setting up Shadow AI runtime. This can take a few minutes..."; Flags: waituntilterminated runhidden
Filename: "{app}\run_windows.vbs"; Description: "{cm:LaunchProgram,Shadow AI}"; Flags: nowait postinstall skipifsilent shellexec
