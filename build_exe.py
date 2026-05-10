import PyInstaller.__main__
import os
import sys
import customtkinter

# Get base path
base_dir = os.path.dirname(os.path.abspath(__file__))

# Get CustomTkinter path for bundling
ctk_path = os.path.dirname(customtkinter.__file__)

# Define separator for --add-data (depends on OS)
sep = os.pathsep

# PyInstaller arguments
args = [
    'main.py',
    '--name=HardwareDiagnosticTool',
    '--onedir',                # One directory for stability with binaries
    '--contents-directory=_internal', # Put internal dependencies in _internal folder (Clean structure)
    '--noconsole',              # GUI app, no terminal window
    '--clean',                  # Clean cache
    '--noconfirm',               # Overwrite output directory without asking
    f'--add-data=hwinfo{sep}hwinfo',
    f'--add-data=assets{sep}assets',
    f'--add-data=Novabench{sep}Novabench',
    '--collect-all=customtkinter',
    '--collect-all=matplotlib',
    '--collect-submodules=utils',
    '--collect-submodules=gui',
    '--collect-submodules=modules',
]

print(f"Starting PyInstaller build with arguments: {args}")

if __name__ == "__main__":
    PyInstaller.__main__.run(args)
    print("\nBuild complete. Check the 'dist' directory.")
