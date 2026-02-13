# Build & Install - macOS

## Prerequisites

1. Install Python 3.9 to 3.13 from [python.org](https://www.python.org/downloads/) (**not** 3.14 — PyQt5 crashes on Python 3.14 due to internal dict API changes)
2. Xcode Command Line Tools: `xcode-select --install`

## Steps

### 1. Install dependencies and build the .app bundle

```
cd src && pip3 install -r requirements.txt pyinstaller && pyinstaller OpenStrandStudio3D_mac.spec
```

This produces `src/dist/OpenStrandStudio3D.app`.

### 2. Test the app

```
open src/dist/OpenStrandStudio3D.app
```

Verify the app launches correctly.

### 3. Build the PKG installer

```
cd src && bash build_installer_3d_1_00.sh
```

This produces the `.pkg` installer in `src/installer_output/`.

### 4. Test the installer

Double-click the `.pkg` file. Verify:
- App installs to `/Applications/OpenStrandStudio 3D.app`
- Desktop icon is created
- App launches after install
