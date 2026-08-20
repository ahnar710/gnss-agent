; GNSS 文献调研 Agent — Inno Setup 安装器脚本
; 构建：先运行 PyInstaller（dist\GNSS文献调研Agent\），再 iscc 本文件。
; 前置：Inno Setup 6（https://jrsoftware.org/isinfo.php）
; 注意：发版时同步更新 MyAppVersion（与 packaging/version_info.txt、app/__init__.py 一致）

#define MyAppName "GNSS 文献调研 Agent"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "GNSS 文献调研 Agent 项目组"
#define MyAppExeName "GNSSAgent.exe"
#define MyAppId "{{3C8A2B4E-9D41-4F6B-B0D2-4E7A3F1C9A05}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 安装到用户目录，避免 UAC 弹窗（非管理员可装）
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 输出到项目 dist_installer 目录
OutputDir=..\dist_installer
OutputBaseFilename=GNSS文献调研Agent_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
SetupLogging=yes
; 静默安装支持：/VERYSILENT /SUPPRESSMSGBOXES
DisableDirPage=auto
DisableFinishedPage=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
; PyInstaller 产物整个目录打入安装包
Source: "..\dist\GNSS文献调研Agent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

; 说明：用户调研数据存放在 %USERPROFILE%\.gnss_agent（config.py 打包模式路径），
; 卸载时默认保留（避免误删用户数据）。如需彻底清理，卸载后手动删除该目录。
