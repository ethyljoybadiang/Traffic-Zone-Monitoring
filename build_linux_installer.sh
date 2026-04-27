#!/usr/bin/env bash
# build_linux_installer.sh — Package the PyInstaller output into a Linux distributable
# Usage:
#   chmod +x build_linux_installer.sh
#   ./build_linux_installer.sh
#
# Produces:
#   dist/ALAM_Traffic_linux_x86_64.tar.gz   (portable tarball)
#   dist/install_alam.sh                     (optional install script)

set -e  # exit on any error

APP_NAME="ALAM_Traffic"
APP_DIR="dist/${APP_NAME}"
VERSION="1.0.0"
ARCH=$(uname -m)
TARBALL="dist/${APP_NAME}_linux_${ARCH}_v${VERSION}.tar.gz"

echo "============================================================"
echo "  ALAM Linux Packager"
echo "  App : ${APP_NAME}"
echo "  Arch: ${ARCH}"
echo "============================================================"

# ── Step 1: Run PyInstaller if the dist folder doesn't exist yet ─────────
if [ ! -d "${APP_DIR}" ]; then
    echo ""
    echo "[1/3] PyInstaller dist not found — running build_exe.py first..."
    python build_exe.py
else
    echo "[1/3] PyInstaller dist found at ${APP_DIR}/ — skipping rebuild."
    echo "      (Delete dist/ and re-run this script to force a fresh build)"
fi

# ── Step 2: Create the portable tarball ──────────────────────────────────
echo ""
echo "[2/3] Creating tarball: ${TARBALL}"
cd dist
tar -czf "../${TARBALL}" "${APP_NAME}/"
cd ..
echo "      Done: ${TARBALL}"

# ── Step 3: Generate a simple install.sh alongside the tarball ───────────
echo ""
echo "[3/3] Writing dist/install_alam.sh ..."

cat > dist/install_alam.sh << 'INSTALL_SCRIPT'
#!/usr/bin/env bash
# install_alam.sh — Installs ALAM Traffic to /opt and creates a desktop shortcut
set -e

APP_NAME="ALAM_Traffic"
INSTALL_DIR="/opt/${APP_NAME}"
DESKTOP_FILE="/usr/share/applications/alam-traffic.desktop"

echo "Installing ALAM Traffic Monitor..."

# Extract if running from the bundled tarball
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "${SCRIPT_DIR}/${APP_NAME}" ]; then
    sudo cp -r "${SCRIPT_DIR}/${APP_NAME}" "${INSTALL_DIR}"
else
    echo "[ERROR] Cannot find ${APP_NAME}/ folder next to this script."
    exit 1
fi

sudo chmod +x "${INSTALL_DIR}/${APP_NAME}"

# Desktop shortcut
sudo tee "${DESKTOP_FILE}" > /dev/null << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ALAM Traffic Monitor
Comment=AI-powered Vehicle Counting System
Exec=${INSTALL_DIR}/${APP_NAME}
Icon=${INSTALL_DIR}/resources/icon.png
Terminal=false
Categories=Science;Education;
EOF

echo ""
echo "✓ Installed to ${INSTALL_DIR}"
echo "✓ Desktop shortcut created"
echo ""
echo "Launch with:  ${INSTALL_DIR}/${APP_NAME}"
echo "  or find 'ALAM Traffic Monitor' in your application menu."
INSTALL_SCRIPT

chmod +x dist/install_alam.sh
echo "      Done: dist/install_alam.sh"

echo ""
echo "============================================================"
echo "  Packaging complete!"
echo ""
echo "  Portable tarball : ${TARBALL}"
echo "  Install script   : dist/install_alam.sh"
echo ""
echo "  To distribute:"
echo "    1. Copy ${TARBALL} to the target Linux machine"
echo "    2. tar -xzf ${TARBALL##*/}"
echo "    3. bash install_alam.sh        (for system install)"
echo "    OR just run: ./${APP_NAME}/${APP_NAME}  (portable, no install)"
echo "============================================================"
