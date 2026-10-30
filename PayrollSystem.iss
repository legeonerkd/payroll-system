[Setup]
AppName=Payroll System
AppVersion=1.9.2
AppPublisher=PayrollSystem Team
AppPublisherURL=https://github.com/legeonerkd/payroll-system
AppSupportURL=https://github.com/legeonerkd/payroll-system/issues
AppUpdatesURL=https://github.com/legeonerkd/payroll-system/releases
DefaultDirName={localappdata}\Programs\PayrollSystem
DefaultGroupName=Payroll System
OutputDir=output
OutputBaseFilename=PayrollSystem_v1.9.2_Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\PayrollSystem.exe
WizardStyle=modern
DisableProgramGroupPage=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\PayrollSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Payroll System"; Filename: "{app}\PayrollSystem.exe"; IconFilename: "{app}\PayrollSystem.exe"
Name: "{group}\Uninstall Payroll System"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Payroll System"; Filename: "{app}\PayrollSystem.exe"; Tasks: desktopicon; IconFilename: "{app}\PayrollSystem.exe"
Name: "{userstartup}\Payroll System"; Filename: "{app}\PayrollSystem.exe"; Tasks: startupicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon"; Description: "Run at Windows &startup"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\PayrollSystem.exe"; Description: "Launch Payroll System"; Flags: postinstall nowait skipifsilent

; User databases and backups are intentionally preserved during uninstall.

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Можно добавить дополнительные действия после установки
  end;
end;
