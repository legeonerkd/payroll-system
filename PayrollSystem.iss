[Setup]
AppName=Payroll System
AppVersion=1.7.0
DefaultDirName={localappdata}\Programs\PayrollSystem
DefaultGroupName=Payroll System
OutputDir=output
OutputBaseFilename=PayrollSystem_v1.7.0_Installer
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\PayrollSystem.exe

[Files]
Source: "dist\PayrollSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Payroll System"; Filename: "{app}\PayrollSystem.exe"; IconFilename: "{app}\PayrollSystem.exe"
Name: "{userdesktop}\Payroll System"; Filename: "{app}\PayrollSystem.exe"; Tasks: desktopicon; IconFilename: "{app}\PayrollSystem.exe"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\PayrollSystem.exe"; Description: "Launch Payroll System"; Flags: postinstall nowait skipifsilent
