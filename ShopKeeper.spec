# PyInstaller spec file — builds ShopKeeper into a single standalone .exe.
#
# IMPORTANT: PyInstaller must be run on the SAME operating system you want
# the .exe for. To build a Windows .exe, run this ON a Windows PC — it
# cannot be built from Mac/Linux/this sandbox.
#
# Usage (on Windows, with your virtual environment active):
#   pip install pyinstaller
#   pyinstaller ShopKeeper.spec
#
# Output appears in: dist/ShopKeeper/ShopKeeper.exe

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    # These two lines are the important part: they tell PyInstaller to copy
    # the templates/ and static/ folders INTO the bundled app, preserving
    # the "app/templates" and "app/static" folder structure Flask expects.
    # Without this, the .exe would run but every page would 404 or show
    # unstyled HTML, since Flask wouldn't be able to find its own files.
    datas=[
        ("app/templates", "app/templates"),
        ("app/static", "app/static"),
    ],
    hiddenimports=[
        "flask_sqlalchemy",
        "flask_login",
        "sqlalchemy.sql.default_comparator",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ShopKeeper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # keep the console window — it shows the shop's local IP for phone access
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ShopKeeper",
)
