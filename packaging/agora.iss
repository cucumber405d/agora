; Inno Setup script: per-user install of the PyInstaller onedir build (no admin rights).
; Build: iscc /DAppVersion=0.2.0 packaging\agora.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{192C691D-75CA-4F8F-86FA-1BF10256200A}
AppName=Agora
AppVersion={#AppVersion}
AppPublisher=Dmitry Ibikus
AppPublisherURL=https://github.com/cucumber405d/agora
DefaultDirName={localappdata}\Programs\Agora
DefaultGroupName=Agora
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Agora-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes
UninstallDisplayName=Agora {#AppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
Name: "addtopath"; Description: "Add Agora to PATH (run ""agora doctor"" from any console)"; Flags: unchecked

[Files]
Source: "..\dist\agora\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "launch.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Agora"; Filename: "{app}\launch.cmd"; WorkingDir: "{userdocs}"; IconFilename: "{app}\agora.exe"
Name: "{userdesktop}\Agora"; Filename: "{app}\launch.cmd"; WorkingDir: "{userdocs}"; IconFilename: "{app}\agora.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function NeedsAddPath(Dir: string): Boolean;
var
  Path: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
    Path := '';
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Path) + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Path, Dir: string;
  P: Integer;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
    exit;
  Dir := ';' + ExpandConstant('{app}');
  P := Pos(Uppercase(Dir), Uppercase(Path));
  if P > 0 then
  begin
    Delete(Path, P, Length(Dir));
    RegWriteExpandStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path);
  end;
end;
