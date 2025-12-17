#!/bin/bash

# Script para probar el sistema distribuido completo
# Ejecutar en Máquina 1 después de que ambos nodos estén activos

echo "========================================="
echo "TEST: SISTEMA DISTRIBUIDO SPOTIFICE"
echo "========================================="
echo ""

CONFIG="--Ice.Config=client.config"

# Test 1: Verificar estado de nodos
echo "[TEST 1] Estado de nodos y servicios"
echo "---"
icegridadmin -u admin -p admin $CONFIG -e "query"
echo ""
sleep 1

# Test 2: Listar servidores disponibles
echo "[TEST 2] Servidores disponibles"
echo "---"
icegridadmin -u admin -p admin $CONFIG -e "show servers" | grep -E "MediaServer|MediaRender|IceStorm"
echo ""
sleep 1

# Test 3: Verificar MediaServer1 (Máquina 1)
echo "[TEST 3] Probando MediaServer1 (local en Máquina 1)"
echo "---"
echo "Ejecutando: python3 media_control.py --MediaServer.Proxy=MediaServer1 --MediaRender.Proxy=MediaRender1"
echo ""
# Aquí podrías ejecutar el test, pero lo comentamos para no bloquear
# timeout 10 ./media_control.py --Ice.Config=client.config --MediaServer.Proxy=MediaServer1 --MediaRender.Proxy=MediaRender1
echo "✓ Comando listo (ejecuta manualmente)"
echo ""
sleep 1

# Test 4: Verificar MediaServer2 (Máquina 2)
echo "[TEST 4] Probando MediaServer2 (remoto en Máquina 2)"
echo "---"
echo "Ejecutando: python3 media_control.py --MediaServer.Proxy=MediaServer2 --MediaRender.Proxy=MediaRender2"
echo ""
# timeout 10 ./media_control.py --Ice.Config=client.config --MediaServer.Proxy=MediaServer2 --MediaRender.Proxy=MediaRender2
echo "✓ Comando listo (ejecuta manualmente)"
echo ""
sleep 1

# Test 5: Verificar IceStorm
echo "[TEST 5] Verificando IceStorm"
echo "---"
icegridadmin -u admin -p admin $CONFIG -e "show server IceStorm"
echo ""
echo "Monitor en otra terminal:"
echo "  $ ./monitor_client.py"
echo ""

# Test 6: Información de objetos
echo "[TEST 6] Información de objetos desplegados"
echo "---"
echo "MediaServer1:"
icegridadmin -u admin -p admin $CONFIG -e "show object MediaServer1" 2>/dev/null || echo "  (info disponible en icegridgui)"
echo ""
echo "MediaServer2:"
icegridadmin -u admin -p admin $CONFIG -e "show object MediaServer2" 2>/dev/null || echo "  (info disponible en icegridgui)"
echo ""

echo "========================================="
echo "RESUMEN DE PRUEBAS"
echo "========================================="
echo ""
echo "✓ Si ambos nodos aparecen como 'up', el despliegue es exitoso"
echo ""
echo "Pruebas manuales recomendadas:"
echo ""
echo "1. Reproducción desde MediaServer1 (Máquina 1):"
echo "   ./media_control.py --Ice.Config=client.config"
echo ""
echo "2. Reproducción desde MediaServer2 (Máquina 2 - remoto):"
echo "   ./media_control.py --Ice.Config=client.config \\"
echo "     --MediaServer.Proxy=MediaServer2 \\"
echo "     --MediaRender.Proxy=MediaRender2"
echo ""
echo "3. Monitor de eventos en tiempo real:"
echo "   ./monitor_client.py"
echo ""
echo "4. GUI de IceGrid (opcional):"
echo "   icegridgui --Ice.Config=client.config"
echo ""
echo "========================================="