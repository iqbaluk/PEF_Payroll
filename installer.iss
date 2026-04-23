#define MyAppName "PEF Payroll"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SoftFlow Ltd"
#define MyAppExeName "PEF_Payroll.exe"

[Setup]
AppId={{A5A822D2-0685-4B9B-9A23-7F65A5E653AD}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PEF Payroll
DefaultGroupName=PEF Payroll
DisableProgramGroupPage=yes
OutputDir=dist-installer
OutputBaseFilename=PEF_Payroll_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\PEF_Payroll\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PEF Payroll"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\PEF Payroll"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch PEF Payroll"; Flags: nowait postinstall skipifsilent
