[Setup]
AppName=Payroll System
AppVersion=1.4.0
DefaultDirName={localappdata}\Programs\PayrollSystem
DefaultGroupName=Payroll System
OutputDir=Output
OutputBaseFilename=PayrollSystem_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico
ArchitecturesInstallIn64BitMode=x64

; ❗ ВАЖНО: БЕЗ admin
PrivilegesRequired=lowest

[Files]
Source: "dist\PayrollSystem.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Payroll System"; Filename: "{app}\PayrollSystem.exe"
Name: "{userdesktop}\Payroll System"; Filename: "{app}\PayrollSystem.exe"

[Run]
Filename: "{app}\PayrollSystem.exe"; \
Description: "Run Payroll System"; \
Flags: nowait postinstall skipifsilent

