#!/bin/bash

# --- 1. Limpieza Previa ---
echo "--- [1/6] Limpiando procesos y bases de datos antiguas... ---"
# Matamos procesos de IceGrid si están corriendo
killall icegridnode icegridregistry 2>/dev/null
# Esperamos un segundo para asegurar que liberan los puertos
sleep 1
# Borramos las bases de datos antiguas
rm -rf db/registry/* db/node1/* db/node2/*
# Creamos las carpetas necesarias
mkdir -p db/registry db/node1 db/node2 media playlists

# --- 2. Seguridad ---
echo "--- [2/6] Generando archivo de contraseñas... ---"
# Generamos usuario 'admin' con contraseña 'admin' usando SHA-256 (separado por espacio)
echo "admin $(openssl passwd -5 admin)" > db/registry/passwords

# --- 3. Arrancar Registro ---
echo "--- [3/6] Iniciando IceGrid Registry... ---"
icegridregistry --Ice.Config=registry.config &
PID_REGISTRY=$!
sleep 2 # Damos tiempo a que arranque

# --- 4. Arrancar Nodos ---
echo "--- [4/6] Iniciando Nodos... ---"
icegridnode --Ice.Config=node1.config &
PID_NODE1=$!
icegridnode --Ice.Config=node2.config &
PID_NODE2=$!
sleep 2

# --- 5. Desplegar Aplicación ---
echo "--- [5/6] Desplegando aplicación Spotifice... ---"
# Subimos el XML autenticándonos como admin
icegridadmin --Ice.Config=client.config -u admin -p admin -e "application add spotifice.xml"

# --- 6. Ejecutar Cliente ---
echo "--- [6/6] Lanzando Cliente... ---"
echo " (Presiona Ctrl+C para salir y cerrar todo)"
./media_control.py --Ice.Config=client.config

# --- 7. Cierre limpio ---
# Cuando cierres el cliente, matamos los procesos de fondo
echo "Cerrando infraestructura..."
kill $PID_REGISTRY $PID_NODE1 $PID_NODE2