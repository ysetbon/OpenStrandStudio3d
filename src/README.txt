OpenStrandStudio 3D
====================

Version 1.00

A 3D strand and braid design application using OpenGL, built with Python and PyQt5.


About
-----

OpenStrandStudio 3D is based on the original OpenStrand Studio. It lets you create any knot in a diagrammatic way by using layers for each section of a strand and incorporating masked layers that allow for an "over-under effect."

The software was created by Yonatan Setbon to facilitate designing any knot, in order to demonstrate and explain how to make complex tutorials involving knot tying.


Features
--------

- 3D strand/braid visualization with OpenGL rendering
- Layer-based strand editing with over-under effects
- Move, rotate, and manipulate control points in 3D space
- Attach strands together to build complex knot structures
- Save and load projects (.oss3d format)
- Undo/Redo support
- Custom dark-themed UI


Downloads
---------

Pre-built installers are available:

- Windows: OpenStrandStudio3DSetup_1_00.exe (Inno Setup installer)
- macOS:   OpenStrand Studio 3D_1.00.pkg (PKG installer)


Building from Source
--------------------

Windows:
  1. Install Python 3.9+ and Inno Setup
  2. Install dependencies: pip install -r requirements.txt pyinstaller pillow
  3. Generate icon: python generate_windows_icon.py
  4. Build EXE: pyinstaller OpenStrandStudio3D.spec
  5. Compile installer: Open inno setup/OpenStrandStudio3D_1_00.iss in Inno Setup and compile

  See BUILD_WINDOWS.md for full instructions.

macOS:
  1. Install Python 3.9+ and Xcode Command Line Tools
  2. Install dependencies: pip install -r requirements.txt pyinstaller
  3. Build app: pyinstaller OpenStrandStudio3D_mac.spec
  4. Build installer: bash build_installer_3d_1_00.sh

  See BUILD_MAC.md for full instructions.


Contact
-------

Email:     ysetbon@gmail.com
YouTube:   https://www.youtube.com/@1anya7d (LanYarD channel)
Instagram: https://www.instagram.com/ysetbon/
LinkedIn:  https://www.linkedin.com/in/yonatan-setbon-4a980986/


License
-------

Copyright (c) 2026 Yonatan Setbon. All rights reserved.
