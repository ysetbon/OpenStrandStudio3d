# Build & Install - Windows

## Prerequisites

1. Install Python 3.9+ from [python.org](https://www.python.org/downloads/)
2. Install Inno Setup from [jrsoftware.org](https://jrsoftware.org/isdl.php)

## Steps

### 1. Install dependencies and build the EXE

```
cd src && pip install -r requirements.txt pyinstaller && pyinstaller OpenStrandStudio3D.spec
```

This produces `src/dist/OpenStrandStudio3D.exe`.

### 2. Test the EXE

Run `src/dist/OpenStrandStudio3D.exe` and verify the app launches correctly.

### 3. Build the installer

Open `src/inno setup/OpenStrandStudio3D_1_01.iss` in Inno Setup Compiler and click **Build > Compile**.

This produces the installer at `src/dist/OpenStrandStudio3DSetup_09_Feb_2026_1_01.exe`.

### 4. Test the installer

Run the generated setup EXE. Verify:
- App installs to Program Files
- Desktop shortcut is created (if selected)
- `.oss3d` files are associated with the app
- App launches after install
