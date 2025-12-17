#!/bin/bash

MASTER_IP="192.168.1.206"
NODE2_IP="192.168.1.85"

echo "========================================="
echo "Desplegando NODO 2"
echo "========================================="
echo ""
echo "Maestro: $MASTER_IP"
echo "Este nodo: $NODE2_IP"
echo ""

# Verificar conectividad
echo "[1/5] Verificando conectividad al Maestro..."
if ping -c 1 $MASTER_IP &> /dev/null; then
    echo "✓ Conectado al Maestro"
else
    echo "✗ ERROR: No se puede alcanzar el Maestro en $MASTER_IP"
    echo "Verifica:"
    echo "  1. Ambas máquinas están en la misma red"
    echo "  2. El Maestro está ejecutando (run_master.sh en Máquina 1)"
    echo "  3. No hay firewall bloqueando puerto 4061"
    exit 1
fi

# Limpieza local
echo "[2/5] Limpiando procesos anteriores..."
killall python3 icegridnode 2>/dev/null
sleep 2

rm -rf db/node2/* db/icestorm
mkdir -p db/node2

# Verificar archivos necesarios
echo "[3/5] Verificando archivos necesarios..."
if [ ! -d "media" ] || [ ! -d "playlists" ]; then
    echo ""
    echo "✗ ERROR: Faltan carpetas 'media' o 'playlists'"
    echo ""
    echo "Copia los archivos desde Máquina 1 (192.168.1.206):"
    echo ""
    echo "  mkdir -p ~/spotifice"
    echo "  cd ~/spotifice"
    echo "  scp -r usuario@192.168.1.206:~/spotifice/*.py ./"
    echo "  scp -r usuario@192.168.1.206:~/spotifice/media ./"
    echo "  scp -r usuario@192.168.1.206:~/spotifice/playlists ./"
    echo ""
    echo "Reemplaza 'usuario' con tu usuario de Linux"
    echo ""
    exit 1
fi

echo "✓ Archivos encontrados (media y playlists)"

# Crear/actualizar node2.config
echo "[4/5] Creando configuración de node2..."
cat > node2.config << EOF
IceGrid.InstanceName=Spotifice
Ice.Default.Locator=Spotifice/Locator:tcp -h $MASTER_IP -p 4061
IceGrid.Node.Name=node2
IceGrid.Node.Data=db/node2
IceGrid.Node.Output=db/node2
IceGrid.Node.Endpoints=tcp -h $NODE2_IP
EOF

echo "✓ Configuración lista"

# Iniciar Node2
echo "[5/5] Iniciando IceGrid Node2..."
icegridnode --Ice.Config=node2.config &
NODE2_PID=$!

sleep 4

echo ""
echo "========================================="
echo "✓ NODO 2 DESPLEGADO"
echo "========================================="
echo ""
echo "Para verificar en Máquina 1:"
echo "  $ icegridadmin --Ice.Config=client.config -u admin -p admin"
echo "  > query"
echo ""
echo "Deberías ver:"
echo "  node1 (up)"
echo "  node2 (up)"
echo "  IceStorm (up)"
echo "  MediaServer1 (up)"
echo "  MediaServer2 (up)"
echo "  MediaRender1 (up)"
echo "  MediaRender2 (up)"
echo ""
echo "========================================="
