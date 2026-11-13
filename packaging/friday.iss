; Per-user FRIDAY setup. Python is not required on the target PC.
#define AppRoot "C:\Users\yigit\Desktop\jarvis-rebuild"

[Setup]
AppId={{8F3A1C2E-6B47-4D19-9A55-F21DA7000001}
AppName=FRIDAY
AppVersion=3.9
AppPublisher=FRIDAY
DefaultDirName={localappdata}\FRIDAY
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#AppRoot}\dist
OutputBaseFilename=FRIDAY-Kurulum
SetupIconFile={#AppRoot}\assets\friday.ico
UninstallDisplayIcon={app}\FRIDAY.exe
UninstallDisplayName=FRIDAY
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "{#AppRoot}\dist\FRIDAY\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*,KURULUM.txt"

[Icons]
Name: "{autodesktop}\FRIDAY"; Filename: "{app}\FRIDAY.exe"; WorkingDir: "{app}"; IconFilename: "{app}\FRIDAY.exe"; Comment: "FRIDAY"; AppUserModelID: "FRIDAY.Rebuild"
Name: "{userprograms}\FRIDAY"; Filename: "{app}\FRIDAY.exe"; WorkingDir: "{app}"; IconFilename: "{app}\FRIDAY.exe"; Comment: "FRIDAY"; AppUserModelID: "FRIDAY.Rebuild"
Name: "{userprograms}\FRIDAY kaldır"; Filename: "{uninstallexe}"; IconFilename: "{app}\FRIDAY.exe"; Comment: "FRIDAY kaldır"

[Run]
Filename: "{app}\FRIDAY.exe"; Description: "FRIDAY'i ac"; Flags: nowait postinstall skipifsilent

[Code]
function WebView2Present: Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
  if not Result then
    Result := RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Boot: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  if WebView2Present then
    exit;
  Boot := ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe');
  Exec('powershell.exe', '-NoProfile -WindowStyle Hidden -Command "Invoke-WebRequest -Uri ''https://go.microsoft.com/fwlink/p/?LinkId=2124703'' -OutFile ''' + Boot + '''"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if FileExists(Boot) then
    Exec(Boot, '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function FridayDirName(const Dir: String): String;
begin
  Result := ExtractFileName(RemoveBackslash(Dir));
end;

procedure DeleteFridayDir(const Dir: String);
var
  Trimmed, Parent: String;
begin
  Trimmed := RemoveBackslash(Dir);
  if CompareText(FridayDirName(Trimmed), 'FRIDAY') <> 0 then
    exit;
  Parent := FridayDirName(ExtractFileDir(Trimmed));
  if (CompareText(Parent, 'Local') <> 0) and (CompareText(Parent, 'Roaming') <> 0) then
    exit;
  DelTree(Trimmed, True, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM FRIDAY.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if CurUninstallStep = usPostUninstall then
  begin
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'FRIDAY');
    DeleteFridayDir(ExpandConstant('{localappdata}\FRIDAY'));
    DeleteFridayDir(ExpandConstant('{userappdata}\FRIDAY'));
    if CompareText(FridayDirName(ExpandConstant('{app}')), 'FRIDAY') = 0 then
      DeleteFridayDir(ExpandConstant('{app}'));
  end;
end;
