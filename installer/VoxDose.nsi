; Per-user Windows installation. Original dose code: Pasquale Bottalico.
; VoxDose adaptation/development: Tiago Lima Bicalho Cruz, UFMG.
Unicode True
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"
!ifndef ROOT
!define ROOT ".."
!endif
!ifndef VERSION
!define VERSION "2.0.2"
!endif
Name "VoxDose 2.0"
OutFile "${ROOT}\dist\VoxDose-${VERSION}-Windows-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\VoxDose 2.0"
RequestExecutionLevel user
SetCompressor zlib
SetDatablockOptimize on
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "VoxDose 2.0"
VIAddVersionKey /LANG=1033 "FileDescription" "VoxDose scientific software installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Original dose code: Pasquale Bottalico; VoxDose adaptation: Tiago Lima Bicalho Cruz, UFMG"
Icon "${ROOT}\voxdose\assets\icon.ico"
UninstallIcon "${ROOT}\voxdose\assets\icon.ico"
BrandingText "VoxDose 2.0 - Scientific software"
ShowInstDetails show
ShowUninstDetails show
Var SettingsKey
Var UninstallKey
Var MenuFolder
Var TestMode

!define MUI_ABORTWARNING
!define MUI_ICON "${ROOT}\voxdose\assets\icon.ico"
!define MUI_UNICON "${ROOT}\voxdose\assets\icon.ico"
!define MUI_WELCOMEPAGE_TEXT "Scientific vocal dose analysis.$\r$\nPython and dependencies included.$\r$\nPortuguese and English manuals included.$\r$\n$\r$\nOriginal dosimetry code:$\r$\nPasquale Bottalico.$\r$\n$\r$\nVoxDose adaptation and development:$\r$\nTiago Lima Bicalho Cruz - UFMG."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\VoxDose-2.0.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "PortugueseBR"

Function .onInit
  SetShellVarContext current
  SetRegView 64
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "VoxDose requires 64-bit Windows."
    Abort
  ${EndIf}
  StrCpy $SettingsKey "Software\VoxDose2"
  StrCpy $UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\VoxDose2"
  StrCpy $MenuFolder "VoxDose 2.0"
  ${GetParameters} $R0
  ${GetOptions} $R0 "/TESTMODE=" $TestMode
  ${If} $TestMode == "1"
    StrCpy $SettingsKey "Software\VoxDose2.Validation"
    StrCpy $UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\VoxDose2.Validation"
    StrCpy $MenuFolder "VoxDose 2.0 Validation"
  ${EndIf}
FunctionEnd

Section "VoxDose and bilingual manuals (required)" Main
  SectionIn RO
  SetOutPath "$INSTDIR"
  File "${ROOT}\dist\VoxDose-2.0.exe"
  File "${ROOT}\NOTICE.txt"
  File "${ROOT}\CITATION.cff"
  File "${ROOT}\README.md"
  File /oname=VoxDose.ico "${ROOT}\voxdose\assets\icon.ico"
  FileOpen $0 "$INSTDIR\installed.flag" w
  FileWrite $0 "VoxDose ${VERSION}: per-user installation. Data is stored outside this folder."
  FileClose $0
  ${If} $TestMode == "1"
    FileOpen $0 "$INSTDIR\testmode.flag" w
    FileClose $0
  ${EndIf}
  SetOutPath "$INSTDIR\docs"
  File "${ROOT}\docs\Manual_pt_BR.pdf"
  File "${ROOT}\docs\Manual_en.pdf"
  File "${ROOT}\docs\Relatorio_VoxDose_2.0.pdf"
  File "${ROOT}\docs\RELEASE_2.0.2.md"
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "$SettingsKey" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "$UninstallKey" "DisplayName" "VoxDose 2.0"
  WriteRegStr HKCU "$UninstallKey" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "$UninstallKey" "Publisher" "VoxDose - Bottalico original code; Cruz / UFMG adaptation"
  WriteRegStr HKCU "$UninstallKey" "DisplayIcon" "$INSTDIR\VoxDose.ico"
  WriteRegStr HKCU "$UninstallKey" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "$UninstallKey" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "$UninstallKey" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
  WriteRegDWORD HKCU "$UninstallKey" "NoModify" 1
  WriteRegDWORD HKCU "$UninstallKey" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "$UninstallKey" "EstimatedSize" $0
  CreateDirectory "$SMPROGRAMS\$MenuFolder"
  CreateShortCut "$SMPROGRAMS\$MenuFolder\VoxDose 2.0.lnk" "$INSTDIR\VoxDose-2.0.exe" "" "$INSTDIR\VoxDose.ico"
  CreateShortCut "$SMPROGRAMS\$MenuFolder\Manual - English.lnk" "$INSTDIR\docs\Manual_en.pdf"
  CreateShortCut "$SMPROGRAMS\$MenuFolder\Manual - Portugues.lnk" "$INSTDIR\docs\Manual_pt_BR.pdf"
  CreateShortCut "$SMPROGRAMS\$MenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section /o "Desktop shortcut" DesktopShortcut
  CreateShortCut "$DESKTOP\$MenuFolder.lnk" "$INSTDIR\VoxDose-2.0.exe" "" "$INSTDIR\VoxDose.ico"
SectionEnd

Function un.onInit
  SetShellVarContext current
  SetRegView 64
  StrCpy $SettingsKey "Software\VoxDose2"
  StrCpy $UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\VoxDose2"
  StrCpy $MenuFolder "VoxDose 2.0"
  IfFileExists "$INSTDIR\testmode.flag" 0 +4
    StrCpy $SettingsKey "Software\VoxDose2.Validation"
    StrCpy $UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\VoxDose2.Validation"
    StrCpy $MenuFolder "VoxDose 2.0 Validation"
FunctionEnd

Section "Uninstall"
  ; Only installed program files are removed. Never delete user results/settings.
  Delete "$INSTDIR\VoxDose-2.0.exe"
  Delete "$INSTDIR\VoxDose.ico"
  Delete "$INSTDIR\NOTICE.txt"
  Delete "$INSTDIR\CITATION.cff"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\installed.flag"
  Delete "$INSTDIR\testmode.flag"
  Delete "$INSTDIR\docs\Manual_pt_BR.pdf"
  Delete "$INSTDIR\docs\Manual_en.pdf"
  Delete "$INSTDIR\docs\Relatorio_VoxDose_2.0.pdf"
  Delete "$INSTDIR\docs\RELEASE_2.0.2.md"
  RMDir "$INSTDIR\docs"
  Delete "$SMPROGRAMS\$MenuFolder\VoxDose 2.0.lnk"
  Delete "$SMPROGRAMS\$MenuFolder\Manual - English.lnk"
  Delete "$SMPROGRAMS\$MenuFolder\Manual - Portugues.lnk"
  Delete "$SMPROGRAMS\$MenuFolder\Uninstall.lnk"
  RMDir "$SMPROGRAMS\$MenuFolder"
  Delete "$DESKTOP\$MenuFolder.lnk"
  ReadRegStr $0 HKCU "$SettingsKey" "InstallDir"
  ${If} $0 == $INSTDIR
    DeleteRegKey HKCU "$SettingsKey"
    DeleteRegKey HKCU "$UninstallKey"
  ${EndIf}
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
