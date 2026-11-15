# VoxDose 2.0 - revision 2.0.2

Original MATLAB dosimetry code: **Pasquale Bottalico**. VoxDose adaptation and development: **Tiago Lima Bicalho Cruz - Universidade Federal de Minas Gerais (UFMG)**. These roles remain visible together in the application and scientific exports.

## English / Portugues

- New configurations start in **English**. Brazilian Portuguese remains available in Settings. Explicit language choices are saved.
- Hover over an **(i)** symbol to read its explanation immediately. Move away to dismiss it. There is no modal dialog or OK button. Keyboard focus also shows the explanation. Settings can hide these symbols and field tips.
- Novas configuracoes iniciam em **ingles**. O portugues brasileiro continua disponivel em Settings / Ajustes. A escolha explicita de idioma e preservada.
- Passe o mouse sobre **(i)** para ler a explicacao, sem clicar. Ao afastar o mouse, a dica desaparece. O foco pelo teclado tambem mostra a ajuda. E possivel desabilitar simbolos e dicas em Ajustes.

## Windows

`VoxDose-2.0.exe` remains a self-contained, offline executable, including Python and dependencies. No external Python installation is needed. The portable copy writes results, settings and logs alongside the executable.

`VoxDose-2.0.2-Windows-Setup.exe` is built with NSIS 3.13. It installs for the current user under `%LOCALAPPDATA%\Programs\VoxDose 2.0` by default, with Start menu shortcuts, optional desktop shortcut, both illustrated PDF manuals, technical report, original-code/adaptation attribution, and uninstaller. It does not download a runtime or require administrator privileges.

The installed application keeps writable files under `%LOCALAPPDATA%\VoxDose`. The uninstaller removes only its known application files and shortcuts, preserving results, preferences and unknown files. It never recursively deletes an installation directory.

O instalador inclui o executavel, os manuais em portugues e ingles, o relatorio tecnico e os creditos. Os dados da versao instalada ficam em `%LOCALAPPDATA%\VoxDose`, separados da instalacao, e sao preservados na desinstalacao.

## macOS: native build required / compilacao nativa necessaria

**No macOS binary was produced or validated on this Windows computer.** The `.pkg` under `build/onefile` is a PyInstaller CArchive containing Windows DLLs; it is not an Apple installer and must not be published as a Mac download.

The separate `VoxDose-2.0.2-macOS-build-source.zip` is **source code and a builder**, not an end-user Mac application. On a Mac with Python 3.11 or newer, run `bash Build-macOS.command` from the extracted directory. The builder installs build dependencies in a local virtual environment, generates an architecture-specific `.app`, runs three runtime checks, and then creates native `.dmg` and `.pkg` files in `dist/macos`. Build on each intended architecture; this script does not claim a universal binary. Installed Mac application data goes in `~/Library/Application Support/VoxDose`, outside the bundle.

An optional `APPLE_CODESIGN_IDENTITY` is used for Developer ID signing if configured. Apple notarization and installer signing are not configured; the manifest reports their status. A release must be checked on the target Macs before presenting it as a validated Mac download.

**Nenhum aplicativo macOS foi gerado ou validado neste Windows.** O pacote de fontes prepara a compilacao, mas ainda e necessario executar e testar essa etapa em um Mac.

Primary build documentation: [PyInstaller platform-specific builds](https://pyinstaller.org/en/stable/operating-mode.html), [NSIS scripting reference](https://nsis.sourceforge.io/Docs/Chapter4.html).

## Verification / verificacao

Runtime and regression evidence for this revision is saved in `validation/release_2.0.2/three_runs.json`. Installer installation/launch/uninstallation evidence is in `validation/release_2.0.2/installer_three_runs.json`. Each record includes the actual executable SHA-256. Earlier revision evidence remains preserved separately.

The numerical analysis core was not changed. Earlier documented low-SNR F0 limitations remain applicable. No clinical validation or universal fatigue threshold is claimed.
