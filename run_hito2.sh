#!/bin/bash
# Limpieza
killall python3 icegridnode icegridregistry icepatch2server 2>/dev/null
rm -rf db/registry/* db/node1/* db/node2/* deploy
mkdir -p db/registry db/node1 db/node2 deploy

# PREPARAR DISTRIBUCIÓN
echo "Generando carpeta de distribución..."
cp *.py *.xml client.config deploy/ 2>/dev/null
cp -r media playlists deploy/ 2>/dev/null
icepatch2calc deploy

# Password
echo "admin $(openssl passwd -5 admin)" > db/registry/passwords

# 1. Arrancar Registro
icegridregistry --Ice.Config=registry.config &
sleep 1

# 2. Arrancar Servidor de Archivos (IcePatch2)
echo "Iniciando IcePatch2..."
icepatch2server --Ice.Config=registry.config \
  --IcePatch2.Directory=deploy \
  --IcePatch2.Endpoints="tcp -h localhost -p 4064" \
  --IcePatch2.InstanceName=Spotifice.IcePatch2 &
sleep 1

# 3. Arrancar Nodos
icegridnode --Ice.Config=node1.config &
icegridnode --Ice.Config=node2.config &
sleep 2

# 4. Desplegar
icegridadmin --Ice.Config=client.config -u admin -p admin -e "application add spotifice.xml"

echo "--- HITO 2 DESPLEGADO ---"
echo "Prueba: ./media_control.py --Ice.Config=client.config --MediaServer.Proxy=MediaServer1 --MediaRender.Proxy=MediaRender1"