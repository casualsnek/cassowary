consold_a = Analysis(['__init__.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             noarchive=False)
			 
			 
consold_pyz = PYZ(consold_a.pure, consold_a.zipped_data)

consold_exe = EXE(consold_pyz,
          consold_a.scripts,
          [],
          exclude_binaries=True,
          name='cassowary',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

noconsold_coll = COLLECT(consold_exe,
               consold_a.binaries,
               consold_a.zipfiles,
               consold_a.datas,
               strip=False,
               upx=True,
               name='cassowary')
