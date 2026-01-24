# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['fbr_invoice_uploader\\app\\main.py'],
    pathex=['fbr_invoice_uploader'],
    binaries=[],
    datas=[('C:\\laragon\\www\\Python1\\Python\\.venv\\Lib\\site-packages\\customtkinter', 'customtkinter/'), ('C:\\laragon\\www\\Python1\\Python\\.venv\\Lib\\site-packages\\certifi\\cacert.pem', 'certifi/'), ('assets', 'assets'), ('capture_config.json', '.')],
    hiddenimports=['babel.numbers', 'pymysql', 'PIL', 'customtkinter', 'requests', 'tenacity', 'playwright', 'qrcode', 'app.services.form_capture_service'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
splash = Splash(
    'assets/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
    name='Honda_FBR_Uploader',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Honda_FBR_Uploader',
)
