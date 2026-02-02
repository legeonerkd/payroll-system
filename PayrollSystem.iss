#define MyAppName "Payroll System"
#define MyAppVersion "1.4"
#define MyAppExeName "PayrollSystem.exe"
#define MyAppPublisher "Payroll System"
#define MyAppURL "https://example.com"

[Setup]
AppId={{A1B2C3D4-E5F6-47A9-9C1B-123456789ABC}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes

OutputDir=Output
OutputBaseFilename=PayrollSystem_Setup

Compression=lzma
SolidCompression=yes

SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Payroll System"; Flags: nowait postinstall skipifsilent

