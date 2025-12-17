#!/bin/bash

MASTER_IP="192.168.1.206"

echo "========================================="
echo "Desplegando MAESTRO en $MASTER_IP"
echo "========================================="
echo ""

# Limpieza
echo "[1/7] Limpiando procesos anteriores..."
killall python3 icegridnode icegridregistry icepatch2server icebox 2>/dev/null
sleep 2

echo "[2/7] Limpiando bases de datos..."
rm -rf db/registry/* db/node1/* db/node2/* db/icestorm deploy
mkdir -p db/registry db/node1 db/node2 db/icestorm deploy

# Preparar distribución
echo "[3/7] Preparando distribución para IcePatch2..."
cp *.py *.xml client.config registry.config node1.config node2.config deploy/ 2>/dev/null
cp -r media playlists deploy/ 2>/dev/null
icepatch2calc deploy

# Password
echo "admin $(openssl passwd -5 admin)" > db/registry/passwords

# 1. Arrancar Registry
echo "[4/7] Iniciando IceGrid Registry en $MASTER_IP:4061..."
icegridregistry --Ice.Config=registry.config &
REGISTRY_PID=$!
sleep 3

# 2. Arrancar IcePatch2
echo "[5/7] Iniciando IcePatch2 en $MASTER_IP:4064..."
icepatch2server --Ice.Config=registry.config \
  --IcePatch2.Directory=deploy \
  --IcePatch2.Endpoints="tcp -h 0.0.0.0 -p 4064" \
  --IcePatch2.InstanceName=Spotifice.IcePatch2 &
ICEPATCH_PID=$!
sleep 2

# 3. Arrancar Node1 (LOCAL en Máquina 1)
echo "[6/7] Iniciando IceGrid Node1..."
icegridnode --Ice.Config=node1.config &
NODE1_PID=$!
sleep 3

# 4. Desplegar aplicación
echo "[7/7] Desplegando aplicación Spotifice..."
icegridadmin --Ice.Config=client.config -u admin -p admin -e "application remove Spotifice" 2>/dev/null
sleep 1
icegridadmin --Ice.Config=client.config -u admin -p admin -e "application add spotifice.xml"

sleep 3

echo ""
echo "========================================="
echo "✓ MAESTRO DESPLEGADO CORRECTAMENTE"
echo "========================================="
echo ""
echo "Estado actual:"
echo ""
icegridadmin --Ice.Config=client.config -u admin -p admin -e "query"
echo ""
echo "========================================="
echo ""
echo "PRÓXIMO PASO:"
echo "  En Máquina 2 (192.168.1.85):"
echo "  $ bash run_node2.sh"
echo ""
echo "========================================="