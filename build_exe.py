# build_exe.py
import PyInstaller.__main__
import os
import shutil
import sys
import glob

def clean_build():
    """Remove previous build and dist directories to ensure a clean slate"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Cleaning {d}...")
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"Warning: Could not delete {d}: {e}")

def create_executable(main_file, app_name):
    """
    Create an executable from the application using PyInstaller.
    Optimized for the Tkinter version with YOLO integration.
    """
    
    clean_build()
    
    # Define PyInstaller arguments
    args = [
        main_file,             # Your main Python file
        '--name=' + app_name,  # Name of the executable
        '--onedir',           # One-directory mode (more stable for development/heavy apps)
        '--noupx',            # Disable UPX compression to avoid hangs
        '--console',          # Keep console open for debugging (to see startup logs)
        '--clean',            # Clean PyInstaller cache
        
        # Hidden imports for libraries that might be missed
        '--hidden-import=ultralytics',
        '--hidden-import=PIL.ImageTk',
        '--hidden-import=PIL.ImageDraw',
        
        # Add resources folder
        '--add-data=resources;resources' if os.path.exists('resources') else None,
        
        # Add models (optional - currently provided separately per user request)
        # '--add-data=yolo11n.pt;.' if os.path.exists('yolo11n.pt') else None,
    ]
    
    # Remove None values from args
    args = [arg for arg in args if arg is not None]
    
    print(f"Building executable '{app_name}' from '{main_file}'...")
    print(f"Arguments: {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print(f"\nBuild complete! Executable folder created in 'dist/{app_name}'")
        print(f"Main file: dist/{app_name}/{app_name}.exe")
    except Exception as e:
        print(f"ERROR: Build failed: {e}")

if __name__ == "__main__":
    # Default values for this project
    default_main = "mainwindow.py"
    default_name = "ALAM_Tkinter"
    
    main_file = sys.argv[1] if len(sys.argv) > 1 else default_main
    app_name = sys.argv[2] if len(sys.argv) > 2 else default_name
    
    if not os.path.exists(main_file):
        print(f"Error: Main file '{main_file}' not found.")
        sys.exit(1)
        
    create_executable(main_file, app_name)
