[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{B7A24F3E-5E3C-4C8D-9B1D-6F8A2E1A3C4B}
AppName=ALaM Crop Monitoring
AppVersion=1.0.0.0
AppPublisher=Department of Science and Technology – Advanced Science and Technology Institute
AppPublisherURL=https://asti.dost.gov.ph/
AppSupportURL=https://asti.dost.gov.ph/support
AppUpdatesURL=https://asti.dost.gov.ph/alam
DefaultDirName={autopf}\ALaM Crop Monitoring
DefaultGroupName=ALaM Crop Monitoring
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
Source: "dist\ALAM_Tkinter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ALaM Crop Monitoring"; Filename: "{app}\ALAM_Tkinter.exe"
Name: "{group}\{cm:UninstallProgram,ALaM Traffic Monitoring}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\ALaM Traffic Monitoring"; Filename: "{app}\ALAM_Tkinter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ALAM_Tkinter.exe"; Description: "{cm:LaunchProgram,ALaM Traffic Monitoring}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\ALaM Traffic Monitoring"