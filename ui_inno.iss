[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{B7A24F3E-5E3C-4C8D-9B1D-6F8A2E1A3C4B}
AppName=ALAM Traffic Monitor
AppVersion=1.0.0.0
AppPublisher=Department of Science and Technology – Advanced Science and Technology Institute
AppPublisherURL=https://asti.dost.gov.ph/
AppSupportURL=https://asti.dost.gov.ph/support
AppUpdatesURL=https://asti.dost.gov.ph/alam
DefaultDirName={autopf}\ALAM Traffic Monitor
DefaultGroupName=ALAM Traffic Monitor
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename=ALaM_Crop_Monitoring_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
AppCopyright=© 2025 DOST-ASTI. All rights reserved.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application files (onedir mode)
Source: "dist\ALAM_Traffic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ALAM Traffic Monitor"; Filename: "{app}\ALAM_Traffic.exe"
Name: "{group}\{cm:UninstallProgram,ALAM Traffic Monitor}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\ALAM Traffic Monitor"; Filename: "{app}\ALAM_Traffic.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ALAM_Traffic.exe"; Description: "{cm:LaunchProgram,ALAM Traffic Monitor}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\ALAM Traffic Monitor"