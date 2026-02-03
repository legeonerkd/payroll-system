[Setup]
AppName=Payroll System
AppVersion=1.4.0
DefaultDirName={pf}\PayrollSystem
DefaultGroupName=Payroll System
OutputDir=Output
OutputBaseFilename=PayrollSystem_Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=icon.ico

[Files]
Source: "dist\PayrollSystem.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Payroll System"; Filename: "{app}\PayrollSystem.exe"
Name: "{commondesktop}\Payroll System"; Filename: "{app}\PayrollSystem.exe"

[Run]
Filename: "{app}\PayrollSystem.exe"; Description: "Run Payroll System"; Flags: nowait postinstall skipifsilent
