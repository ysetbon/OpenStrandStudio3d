# Build & Install - macOS

## Prerequisites

1. Install Python 3.9 to 3.13 (**not** 3.14 — PyQt5 crashes on Python 3.14 due to internal dict API changes)
   - Via Homebrew: `brew install python@3.13`
   - Or from [python.org](https://www.python.org/downloads/)
2. Xcode Command Line Tools: `xcode-select --install`

## Steps

### 1. Clone and set up

```
git clone https://github.com/ysetbon/OpenStrandStudio3d.git
cd OpenStrandStudio3d/src
```

### 2. Create a virtual environment with Python 3.13

```
/usr/local/bin/python3.13 -m venv venv
source venv/bin/activate
python --version
```

Verify it says `Python 3.13.x` before continuing.

### 3. Install dependencies, generate icon, and build the .app bundle

```
pip install -r requirements.txt pyinstaller pillow
python generate_mac_icon.py
rm -rf dist build
pyinstaller --clean OpenStrandStudio3D_mac.spec
```

This produces `dist/OpenStrandStudio3D.app`.

### 4. Test the app

```
open dist/OpenStrandStudio3D.app
```

Verify the app launches correctly.

### 5. Build the PKG installer

```
bash build_installer_3d_1_00.sh
```

This produces the `.pkg` installer in `installer_output/`.

### 6. Test the installer

Double-click the `.pkg` file. Verify:
- App installs to `/Applications/OpenStrandStudio 3D.app`
- Desktop icon is created
- App launches after install
