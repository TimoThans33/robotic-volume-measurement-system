# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
script_dir = os.getcwd()
added_files=[("/usr/local/lib/tjess/libtjess-transport-dll.so", ".")]
#added_files = []
#added_files += collect_data_files('app.third_party.tjess_python.tjess', include_py_files=False)

for file in added_files:
    print(f'Adding {file} to binaries')

a = Analysis(   ['main.py'],
                pathex=[script_dir],
                binaries=None,
                datas=[]+added_files,
                hiddenimports=['tabulate'],
                hookspath=[],
                runtime_hooks=[],
                excludes=[],
                win_no_prefer_redirects=False,
                win_private_assemblies=False,
                cipher=block_cipher,
                noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
                cipher=block_cipher)
exe = EXE(pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='pvt-dimensioner-client',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=True )
