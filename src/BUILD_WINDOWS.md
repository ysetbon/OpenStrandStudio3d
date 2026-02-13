# Build & Install - Windows

## Prerequisites

1. Install Python 3.9+ from [python.org](https://www.python.org/downloads/)
2. Install Inno Setup from [jrsoftware.org](https://jrsoftware.org/isdl.php)

## Steps

### 1. Install dependencies, generate icon, and build the EXE

```
cd src && pip install -r requirements.txt pyinstaller pillow && python generate_windows_icon.py && pyinstaller OpenStrandStudio3D.spec
```

This produces:
- `src/openstrandstudio3d_icon_gray.ico` (and synced `src/openstrandstudio3d_icon.ico`) from `src/openstrandstudio3d_icon_gray.png`
- `src/dist/OpenStrandStudio3D.exe`

### 2. Test the EXE

Run `src/dist/OpenStrandStudio3D.exe` and verify the app launches correctly.

### 3. Build the installer

Open `src/inno setup/OpenStrandStudio3D_1_00.iss` in Inno Setup Compiler and click **Build > Compile**.

This produces the installer at `src/dist/OpenStrandStudio3DSetup_13_Feb_2026_1_00.exe`.

### 4. Test the installer

Run the generated setup EXE. Verify:
- App installs to Program Files
- Desktop shortcut is created (if selected)
- `.oss3d` files are associated with the app
- App launches after install

If Windows still shows an old icon, remove existing desktop/start-menu shortcuts for OpenStrand Studio 3D and reinstall using the freshly compiled setup EXE.
