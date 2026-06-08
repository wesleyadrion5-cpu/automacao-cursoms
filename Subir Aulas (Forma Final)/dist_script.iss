; Script do Inno Setup para o Robô Dona Francisca

[Setup]
AppId={{D1F498E3-C5E5-46D9-B101-CF926D4587EE}
AppName=Dona Francisca Automator
AppVersion=1.0
AppPublisher=CursoMS
DefaultDirName={userpf}\Dona Francisca Automator
DefaultGroupName=Dona Francisca Automator
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=Instalador_Dona_Francisca_1.0
SetupIconFile=..\Play Branco.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=none
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Dona Francisca Automator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "banco_frota_build.db"; DestName: "banco_frota.db"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "config_unificada_build.json"; DestName: "config_unificada.json"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "..\Play Branco.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Dona Francisca Automator"; Filename: "{app}\Dona Francisca Automator.exe"; IconFilename: "{app}\Play Branco.ico"
Name: "{group}\{cm:UninstallProgram,Dona Francisca Automator}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Dona Francisca Automator"; Filename: "{app}\Dona Francisca Automator.exe"; Tasks: desktopicon; IconFilename: "{app}\Play Branco.ico"

[Run]
Filename: "{app}\Dona Francisca Automator.exe"; Description: "{cm:LaunchProgram,Dona Francisca Automator}"; Flags: nowait postinstall skipifsilent
