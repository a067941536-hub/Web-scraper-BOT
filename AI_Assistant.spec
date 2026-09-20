# -*- mode: python ; coding: utf-8 -*-
import sys
import os

sys.setrecursionlimit(20000)

from PyInstaller.utils.hooks import collect_all

datas = [('appp.py', '.')]
binaries = []
hiddenimports = ['webview']

# 收集 Streamlit 資源
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['gui_launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',                # 徹底排除 torch，防止執行崩潰 Hook
        'scipy',
        'tensorboard',
        'caffe2',
        'matplotlib',
        'tkinter',
        'PIL'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI_Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AI_Assistant',
)