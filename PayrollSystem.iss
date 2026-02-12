[Setup]
AppName=Payroll System
AppVersion=1.6.0
DefaultDirName={localappdata}\Programs\PayrollSystem
DefaultGroupName=Payroll System
OutputDir=output
OutputBaseFilename=PayrollSystem_Installer
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "dist\PayrollSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Payroll System"; Filename: "{app}\PayrollSystem.exe"
Name: "{userdesktop}\Payroll System"; Filename: "{app}\PayrollSystem.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"
