# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('openstrandstudio3d_icon.icns', '.'),
    ],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtOpenGL', 'PyQt5.QtSvg', 'OpenGL', 'OpenGL.GL', 'OpenGL.GLU', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OpenStrandStudio3D',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='openstrandstudio3d_icon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OpenStrandStudio3D',
)

app = BUNDLE(
    coll,
    name='OpenStrandStudio3D.app',
    icon='openstrandstudio3d_icon.icns',
    bundle_identifier='com.yonatan.openstrandstudio3d',
    info_plist={
        'CFBundleDisplayName': 'OpenStrandStudio 3D',
        'CFBundleName': 'OpenStrandStudio3D',
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': '1.00',
        'CFBundleVersion': '1.00',
        'CFBundleExecutable': 'OpenStrandStudio3D',
        'CFBundleIconFile': 'openstrandstudio3d_icon.icns',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSMinimumSystemVersion': '10.13.0',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
    },
)
