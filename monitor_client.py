#!/usr/bin/env python3
import sys
import time
import Ice
import IceStorm

Ice.loadSlice('-I{} spotifice_v1.ice'.format(Ice.getSliceDir()))
import Spotifice

class MonitorI(Spotifice.Monitor):
    def report(self, status, track, current=None):
        state_str = str(status.state)
        print(f"\n[EVENTO RECIBIDO]")
        print(f"  > Canción: {track.title}")
        print(f"  > Estado:  {state_str}")
        print("-" * 30)
        sys.stdout.flush()

def main():
    print("[DEBUG] Iniciando monitor_client.py", flush=True)
    
    # Initialize with explicit configuration and timeouts
    init_args = [
        '--Ice.Default.Locator=Spotifice/Locator:tcp -h localhost -p 4061',
        '--Ice.Connection.ConnectTimeout=5000',
        '--Ice.Connection.Timeout=10000',
    ]
    init_args.extend(sys.argv[1:])
    
    print("[DEBUG] Inicializando Ice...", flush=True)
    with Ice.initialize(init_args) as ic:
        print("[DEBUG] Ice inicializado", flush=True)
        print("Conectando al TopicManager...", flush=True)
        
        # Retry logic for IceStorm connection
        manager = None
        for attempt in range(15):
            try:
                print(f"[DEBUG] Intento {attempt + 1}/15 de conectar al TopicManager", flush=True)
                base = ic.stringToProxy("SpotificeIceStorm/TopicManager:tcp -h 127.0.0.1 -p 9999")
                print(f"[DEBUG] Proxy creado, haciendo ping...", flush=True)
                base.ice_timeout(5000)  # 5 second timeout
                base.ice_ping()
                print(f"[DEBUG] Ping exitoso, haciendo checkedCast...", flush=True)
                manager = IceStorm.TopicManagerPrx.checkedCast(base)
                if manager:
                    print(f"✓ Conectado al TopicManager (intento {attempt + 1})", flush=True)
                    break
                else:
                    print(f"[DEBUG] checkedCast retornó None", flush=True)
            except Ice.ConnectionRefusedException as e:
                print(f"  Intento {attempt + 1}/15 fallido: ConnectionRefused - ¿IceStorm corriendo?", flush=True)
                if attempt < 14:
                    time.sleep(1)
            except Ice.TimeoutException as e:
                print(f"  Intento {attempt + 1}/15 fallido: Timeout", flush=True)
                if attempt < 14:
                    time.sleep(1)
            except Exception as e:
                print(f"  Intento {attempt + 1}/15 fallido: {type(e).__name__}: {e}", flush=True)
                if attempt < 14:
                    time.sleep(1)
        
        if not manager:
            print("✗ Error: No se puede conectar a IceStorm después de 15 intentos.", flush=True)
            print("Verifica que IceStorm esté corriendo con: icegridadmin -u admin -p admin -e 'query'", flush=True)
            return

        topic_name = "Updates"
        topic = None
        
        try:
            print(f"[DEBUG] Recuperando tema '{topic_name}'...", flush=True)
            topic = manager.retrieve(topic_name)
            print(f"✓ Tema '{topic_name}' encontrado", flush=True)
        except IceStorm.NoSuchTopic:
            print(f"[DEBUG] Tema no existe, creando '{topic_name}'...", flush=True)
            topic = manager.create(topic_name)
            print(f"✓ Tema '{topic_name}' creado", flush=True)
        except Exception as e:
            print(f"✗ Error al acceder al tema: {type(e).__name__}: {e}", flush=True)
            return

        # Create adapter with explicit endpoints
        print(f"[DEBUG] Creando adaptador...", flush=True)
        adapter = ic.createObjectAdapterWithEndpoints(
            "MonitorAdapter", 
            "tcp -h 127.0.0.1"
        )
        monitor = MonitorI()
        subscriber = adapter.addWithUUID(monitor)
        
        print(f"✓ Subscriber creado: {subscriber}", flush=True)
        
        # CRITICAL: Activate adapter BEFORE subscribing
        print(f"[DEBUG] Activando adaptador...", flush=True)
        adapter.activate()
        print(f"✓ Adaptador activado", flush=True)
        
        # Subscribe with retry logic
        qos = {"reliability": "ordered"}
        subscription_success = False
        
        for attempt in range(10):
            try:
                print(f"  Intentando suscribirse (intento {attempt + 1}/10)...", flush=True)
                pub = topic.subscribeAndGetPublisher(qos, subscriber)
                print(f"✓ Suscrito correctamente. Publisher: {pub}", flush=True)
                subscription_success = True
                break
            except IceStorm.AlreadySubscribed:
                print("  Ya estabas suscrito a este tema.", flush=True)
                subscription_success = True
                break
            except Ice.NoEndpointException as e:
                print(f"  NoEndpointException: El publicador no tiene endpoints registrados aún", flush=True)
                if attempt < 9:
                    time.sleep(2)
            except Exception as e:
                print(f"  Error: {type(e).__name__}: {e}", flush=True)
                if attempt < 9:
                    time.sleep(1)
        
        if not subscription_success:
            print("✗ No se pudo suscribir al tema después de 10 intentos", flush=True)
            return

        print(f"✓ Esperando eventos... (Ctrl+C para salir)", flush=True)
        print("-" * 30)
        sys.stdout.flush()
        
        try:
            ic.waitForShutdown()
        except KeyboardInterrupt:
            print("\n✓ Desconectando...", flush=True)
        finally:
            try:
                topic.unsubscribe(subscriber)
                print("✓ Desuscrito correctamente", flush=True)
            except Exception as e:
                print(f"  Nota al desuscribirse: {type(e).__name__}", flush=True)

if __name__ == '__main__':
    main()