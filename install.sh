#!/bin/bash

set -e

INSTALL_DIR="/opt/Backhaul-manager"

echo "Creating directory..."
mkdir -p $INSTALL_DIR

cd $INSTALL_DIR

echo "Downloading Backhaul..."

wget -O backhaul_linux_amd64.tar.gz \
https://github.com/Musixal/Backhaul/releases/download/v0.7.2/backhaul_linux_amd64.tar.gz

echo "Extracting..."

tar -xzf backhaul_linux_amd64.tar.gz

chmod +x backhaul

echo "Downloading Manager..."

wget -O manager.py \
https://raw.githubusercontent.com/nuck0nuck/Backhaul-manager/refs/heads/main/manager.py

chmod +x manager.py

echo "Creating command shortcut..."

cat > /usr/local/bin/bmanage << EOF
#!/bin/bash
cd $INSTALL_DIR
/usr/bin/python3 $INSTALL_DIR/manager.py
EOF

chmod +x /usr/local/bin/bmanage

echo
echo "===================================="
echo "Backhaul Manager Installed"
echo "Path: $INSTALL_DIR"
echo
echo "Run Manager:"
echo "bmanage"
echo "===================================="

