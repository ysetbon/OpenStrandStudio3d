# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Anaconda stores Qt DLLs and plugins in Library/, not inside the PyQt5 package.
CONDA_PREFIX = os.environ.get('CONDA_PREFIX', r'C:\ProgramData\anaconda3')
QT_BIN = os.path.join(CONDA_PREFIX, 'Library', 'bin')
QT_PLUGINS = os.path.join(CONDA_PREFIX, 'Library', 'plugins')

qt_binaries = []
# Core Qt5 DLLs required at runtime
for dll in ['Qt5Core_conda.dll', 'Qt5Gui_conda.dll', 'Qt5Widgets_conda.dll',
            'Qt5OpenGL_conda.dll', 'Qt5Svg_conda.dll']:
    dll_path = os.path.join(QT_BIN, dll)
    if os.path.exists(dll_path):
        qt_binaries.append((dll_path, '.'))

# Platform plugin (qwindows.dll) - required for any GUI to work
qt_platform_src = os.path.join(QT_PLUGINS, 'platforms', 'qwindows.dll')
qt_datas = []
if os.path.exists(qt_platform_src):
    qt_datas.append((os.path.join(QT_PLUGINS, 'platforms', 'qwindows.dll'), 'PyQt5/Qt5/plugins/platforms'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=qt_binaries,
    datas=[('openstrandstudio3d_icon_gray.ico', '.'), ('openstrandstudio3d_icon.ico', '.'), ('openstrandstudio3d_icon.png', '.')] + qt_datas,
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtOpenGL', 'OpenGL', 'OpenGL.GL', 'OpenGL.GLU', 'numpy'],
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
    a.binaries,
    a.datas,
    [],
    name='OpenStrandStudio3D',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['openstrandstudio3d_icon_gray.ico'],
)
