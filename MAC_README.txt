Curve Analyzer on macOS
=======================

Important
---------

The Windows file "Curve Analyzer.exe" will not run on a Mac.

To create a Mac app, build the same source code on a Mac. PyInstaller must build
on the operating system it targets.

Build on a Mac
--------------

1. Copy this project folder to the Mac.
2. Install Python 3.11 or newer from https://www.python.org/downloads/macos/
3. Open Terminal.
4. Go into the project folder, for example:

   cd ~/Downloads/curve_analyzer

5. Run:

   chmod +x build_macos_release.sh
   ./build_macos_release.sh 1.0.0

The Mac build will be created at:

   release/Curve_Analyzer_macOS_Portable_v1.0.0.zip

Using the Mac app
-----------------

1. Unzip Curve_Analyzer_macOS_Portable_v1.0.0.zip.
2. Open the "Curve Analyzer macOS" folder.
3. Double-click "Curve Analyzer.app".

If macOS blocks the app because it is unsigned:

1. Right-click "Curve Analyzer.app".
2. Choose Open.
3. Choose Open again when macOS asks.

For polished public distribution, sign and notarize the app with an Apple
Developer ID certificate. Without notarization, macOS may show a Gatekeeper
warning on other people's computers.
