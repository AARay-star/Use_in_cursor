import PyInstaller.__main__

PyInstaller.__main__.run([
    'Demo1.py',
    '--name=我的窗口程序',
    '--windowed',
    '--onefile',
    '--icon=NONE',
    '--clean',
    '--noconfirm'
]) 