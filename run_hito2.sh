#!/bin/bash
# Limpieza completa
echo "Limpiando procesos anteriores..."
killall python3 icegridnode icegridregistry icepatch2server icebox 2>/dev/null
sleep 1

echo "Limpiando bases de datos..."
rm -rf db/registry/* db/node1/* db/node2/* db/icestorm deploy
mkdir -p db/registry db/node1 db/node2 db/icestorm deploy

# PREPARAR DISTRIBUCIÓN
echo "Generando carpeta de distribución..."
cp *.py *.xml client.config deploy/ 2>/dev/null
cp -r media playlists deploy/ 2>/dev/null
icepatch2calc deploy

# Password
echo "admin $(openssl passwd -5 admin)" > db/registry/passwords

# 1. Arrancar Registro
echo "Iniciando Registry..."
icegridregistry --Ice.Config=registry.config &
REGISTRY_PID=$!
sleep 3

# 2. Arrancar Servidor de Archivos (IcePatch2)
echo "Iniciando IcePatch2..."
icepatch2server --Ice.Config=registry.config \
  --IcePatch2.Directory=deploy \
  --IcePatch2.Endpoints="tcp -h 0.0.0.0 -p 4064" \
  --IcePatch2.InstanceName=Spotifice.IcePatch2 &
ICEPATCH_PID=$!
sleep 2

# 3. Arrancar Nodos
echo "Iniciando Nodos..."
icegridnode --Ice.Config=node1.config &
NODE1_PID=$!
icegridnode --Ice.Config=node2.config &
NODE2_PID=$!
sleep 3

# 4. Desplegar aplicación
echo "Desplegando aplicación..."
icegridadmin --Ice.Config=client.config -u admin -p admin -e "application add spotifice.xml"

if [ $? -ne 0 ]; then
    echo "Error al desplegar. Intentando remover aplicación existente..."
    icegridadmin --Ice.Config=client.config -u admin -p admin -e "application remove Spotifice" 2>/dev/null
    sleep 1
    echo "Reintentando despliegue..."
    icegridadmin --Ice.Config=client.config -u admin -p admin -e "application add spotifice.xml"
fi

# 5. Wait for IceStorm to fully initialize
echo "Esperando a que IceStorm se inicialice..."
sleep 3

echo ""
echo "========================================="
echo "--- HITO 3 DESPLEGADO (IceStorm Activo) ---"
echo "========================================="
echo ""
echo "Prueba monitor:"
echo "  ./monitor_client.py"
echo ""
echo "Prueba control:"
echo "  ./media_control.py --Ice.Config=client.config"
echo ""
echo "Para detener todo:"
echo "  killall python3 icegridnode icegridregistry icepatch2server icebox"
echo ""
echo "========================================="