#define MyAppName "DMW Job Orders Exporter"
#define MyAppVersion "1.3.0"
#define ExeCLI "dmw-export.exe"
#define ExeGUI "dmw-export-gui.exe"
#define TaskName "DMW Monthly Export"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={pf}\DMW Exporter
DefaultGroupName={#MyAppName}
OutputBaseFilename=DMW-Exporter-Setup
OutputDir=.
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
DisableDirPage=no
DisableProgramGroupPage=no

[Files]
; your built binaries
Source: "dist\dmw-export.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\dmw-export-gui.exe"; DestDir: "{app}"; Flags: ignoreversion
; config: only if the user doesn't have one yet
Source: "config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\{#MyAppName} (GUI)"; Filename: "{app}\{#ExeGUI}"
Name: "{commondesktop}\{#MyAppName} (GUI)"; Filename: "{app}\{#ExeGUI}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
; Optional task to create a default monthly schedule (Day 28 @ 23:55)
Name: "createschedule"; Description: "Create a monthly schedule (Day 28 at 23:55)"; GroupDescription: "Automation:"; Flags: unchecked

[Run]
Filename: "schtasks.exe"; Parameters: "/Create /TN ""DMW Monthly Export"" /SC MONTHLY /D 1 /ST 00:05 /RL HIGHEST /TR ""{app}\dmw-export.exe"""; Flags: runhidden waituntilterminated; Tasks: createschedule; StatusMsg: "Creating monthly scheduled task..."

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/Delete /TN ""DMW Monthly Export"" /F"; Flags: runhidden waituntilterminated

; We keep config.json by default (so user settings survive uninstall)
; If you *do* want to remove it, uncomment the line below:
; [UninstallDelete]
; Type: files; Name: "{app}\config.json"
