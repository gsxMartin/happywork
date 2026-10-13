# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：目录模式（onedir）、无控制台窗口。

构建：pyinstaller lezi.spec --noconfirm
产物：dist/lezi/lezi.exe（连同同目录的 _internal/ 一起分发）
运行时 config.json / state.json 写在 lezi.exe 同级目录；内容库从 _internal/resources 读取。
"""

a = Analysis(
    ["lezi_entry.py"],
    pathex=["src"],
    binaries=[],
    datas=[("resources/content_local.json", "resources")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="lezi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="lezi",
)