# Curve Analyzer Packaging

This project builds desktop apps that users can run without VS Code.

## Windows Build

Run from PowerShell:

```powershell
cd D:\curve_analyzer
.\build_release.ps1 -Version 1.0.0
```

Output:

```text
release\Curve_Analyzer_Portable_v1.0.0.zip
```

Windows users should unzip it and double-click:

`Curve Analyzer.exe`

If Windows SmartScreen appears, users can choose `More info` then `Run anyway`.
For broad public distribution, use a code-signing certificate.

## macOS Build

The Windows `.exe` cannot run on macOS. To create a Mac app, copy this project
folder to a Mac and build it there:

```bash
cd ~/Downloads/curve_analyzer
chmod +x build_macos_release.sh
./build_macos_release.sh 1.0.0
```

Output:

```text
release/Curve_Analyzer_macOS_Portable_v1.0.0.zip
```

Mac users should unzip it and double-click:

`Curve Analyzer.app`

If macOS blocks the app because it is unsigned, right-click the app, choose
`Open`, then choose `Open` again. For smooth public distribution, sign and
notarize the app with an Apple Developer ID certificate.
