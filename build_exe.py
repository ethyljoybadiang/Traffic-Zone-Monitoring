# build_exe.py — Cross-platform build script (Linux & Windows)
import PyInstaller.__main__
import os
import shutil
import sys
import platform

# ─── Config ────────────────────────────────────────────────────────────────
APP_NAME    = "ALAM_Traffic"
MAIN_FILE   = "mainwindow.py"
IS_WINDOWS  = platform.system() == "Windows"
SEP         = ";" if IS_WINDOWS else ":"   # PyInstaller data separator
# ───────────────────────────────────────────────────────────────────────────


def clean_build():
    """Remove previous build/dist directories for a clean slate."""
    for d in ['build', 'dist', '__pycache__']:
        if os.path.exists(d):
            print(f"  Cleaning {d}/...")
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"  [WARNING] Could not delete {d}: {e}")


def collect_data_args():
    """Build --add-data args based on what actually exists in the project."""
    data_pairs = [
        ("resources", "resources"),  # UI assets / icons
    ]
    args = []
    for src, dst in data_pairs:
        if os.path.exists(src):
            args.append(f"--add-data={src}{SEP}{dst}")
    return args


def create_executable(main_file=MAIN_FILE, app_name=APP_NAME):
    """
    Build a standalone executable using PyInstaller.

    On Windows  → --noconsole (no terminal window shown to the user)
    On Linux    → --console   (keeps terminal for GPU/CUDA log visibility)
    """
    print(f"\n{'='*60}")
    print(f"  ALAM Build Script")
    print(f"  Platform : {platform.system()} {platform.machine()}")
    print(f"  App name : {app_name}")
    print(f"  Entry    : {main_file}")
    print(f"{'='*60}\n")

    if not os.path.exists(main_file):
        print(f"[ERROR] Entry file '{main_file}' not found.")
        sys.exit(1)

    clean_build()

    args = [
        main_file,
        f"--name={app_name}",
        "--onedir",           # folder mode — more stable for ML/GPU apps
        "--noupx",            # skip UPX (causes false-positive AV flags)
        "--clean",            # clear PyInstaller cache each run

        # Show console on Linux (helpful for GPU/CUDA debug); hide on Windows
        "--noconsole" if IS_WINDOWS else "--console",

        # ── Runtime hook: fixes torch/_numpy/_ufuncs.py NameError ──────────
        "--runtime-hook=runtime_hooks/fix_torch_numpy.py",

        # ── torch/torchvision need collect-all (deep lazy imports + exec) ───
        "--collect-all=torch",
        "--collect-all=torchvision",

        # ── ultralytics: do NOT use collect-all — its __init__ uses         ──
        # __getattr__ lazy imports; data-copied files aren't frozen modules.
        # Use explicit hidden imports instead so PyInstaller freezes them.
        "--hidden-import=ultralytics",
        "--hidden-import=ultralytics.models",
        "--hidden-import=ultralytics.models.yolo",
        "--hidden-import=ultralytics.models.rtdetr",
        "--hidden-import=ultralytics.models.fastsam",
        "--hidden-import=ultralytics.models.nas",
        "--hidden-import=ultralytics.models.sam",
        "--hidden-import=ultralytics.models.utils",
        "--hidden-import=ultralytics.engine",
        "--hidden-import=ultralytics.engine.model",
        "--hidden-import=ultralytics.engine.predictor",
        "--hidden-import=ultralytics.engine.trainer",
        "--hidden-import=ultralytics.engine.validator",
        "--hidden-import=ultralytics.nn",
        "--hidden-import=ultralytics.nn.tasks",
        "--hidden-import=ultralytics.nn.autobackend",
        "--hidden-import=ultralytics.nn.modules",
        "--hidden-import=ultralytics.trackers",
        "--hidden-import=ultralytics.trackers.byte_tracker",
        "--hidden-import=ultralytics.trackers.bot_sort",
        "--hidden-import=ultralytics.utils",
        "--hidden-import=ultralytics.utils.ops",
        "--hidden-import=ultralytics.utils.loss",
        "--hidden-import=ultralytics.utils.metrics",
        "--hidden-import=ultralytics.utils.plotting",
        "--hidden-import=ultralytics.utils.torch_utils",
        "--hidden-import=ultralytics.data",
        "--hidden-import=ultralytics.data.augment",
        "--hidden-import=ultralytics.data.loaders",

        # Copy package metadata so version checks / torch.hub work
        "--copy-metadata=torch",
        "--copy-metadata=torchvision",
        "--copy-metadata=ultralytics",
        "--copy-metadata=numpy",
        "--copy-metadata=filelock",
        "--copy-metadata=packaging",

        # Other hidden imports PyInstaller often misses
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=cv2",
        "--hidden-import=shapely",
        "--hidden-import=schedule",
        "--hidden-import=reportlab",
        "--hidden-import=lap",

        # Only exclude truly unrelated GUI toolkits
        "--exclude-module=PySide6",
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
    ]

    # Add data files
    args += collect_data_args()

    print("Running PyInstaller with args:")
    for a in args:
        print(f"  {a}")
    print()

    try:
        PyInstaller.__main__.run(args)
        exe_ext = ".exe" if IS_WINDOWS else ""
        print(f"\n{'='*60}")
        print(f"  Build complete!")
        print(f"  Output folder : dist/{app_name}/")
        print(f"  Executable    : dist/{app_name}/{app_name}{exe_ext}")
        if IS_WINDOWS:
            print(f"\n  Next step: compile ui_inno.iss with Inno Setup")
            print(f"  to produce the Windows installer.")
        else:
            print(f"\n  Next step: run  ./build_linux_installer.sh")
            print(f"  to package into a .tar.gz distributable.")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    mf  = sys.argv[1] if len(sys.argv) > 1 else MAIN_FILE
    nm  = sys.argv[2] if len(sys.argv) > 2 else APP_NAME
    create_executable(mf, nm)
