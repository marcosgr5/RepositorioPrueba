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

def main():
    # Initialize with explicit configuration
    init_args = [
        '--Ice.Default.Locator=Spotifice/Locator:tcp -h localhost -p 4061',
    ]
    init_args.extend(sys.argv[1:])
    
    with Ice.initialize(init_args) as ic:
        print("Conectando al TopicManager...")
        
        # Retry logic for IceStorm connection
        manager = None
        for attempt in range(15):
            try:
                base = ic.stringToProxy("SpotificeIceStorm/TopicManager:tcp -h 127.0.0.1 -p 9999")
                manager = IceStorm.TopicManagerPrx.checkedCast(base)
                if manager:
                    print(f"✓ Conectado al TopicManager (intento {attempt + 1})")
                    break
            except Exception as e:
                print(f"  Intento {attempt + 1}/15 fallido: {type(e).__name__}")
                if attempt < 14:
                    time.sleep(1)
        
        if not manager:
            print("✗ Error: No se puede conectar a IceStorm después de 15 intentos.")
            return

        topic_name = "Updates"
        topic = None
        
        try:
            topic = manager.retrieve(topic_name)
            print(f"✓ Tema '{topic_name}' encontrado")
        except IceStorm.NoSuchTopic:
            print(f"  Creando tema '{topic_name}'...")
            topic = manager.create(topic_name)
            print(f"✓ Tema '{topic_name}' creado")

        # Create adapter with explicit endpoints
        adapter = ic.createObjectAdapterWithEndpoints(
            "MonitorAdapter", 
            "tcp -h 127.0.0.1"
        )
        monitor = MonitorI()
        subscriber = adapter.addWithUUID(monitor)
        
        print(f"✓ Subscriber creado: {subscriber}")
        
        # CRITICAL: Activate adapter BEFORE subscribing
        adapter.activate()
        print(f"✓ Adaptador activado")
        
        # Subscribe with retry logic
        qos = {"reliability": "ordered"}
        subscription_success = False
        
        for attempt in range(10):
            try:
                print(f"  Intentando suscribirse (intento {attempt + 1}/10)...")
                pub = topic.subscribeAndGetPublisher(qos, subscriber)
                print(f"✓ Suscrito correctamente. Publisher: {pub}")
                subscription_success = True
                break
            except IceStorm.AlreadySubscribed:
                print("  Ya estabas suscrito a este tema.")
                subscription_success = True
                break
            except Ice.NoEndpointException as e:
                print(f"  NoEndpointException: El publicador no tiene endpoints registrados aún")
                if attempt < 9:
                    time.sleep(2)
            except Exception as e:
                print(f"  Error: {type(e).__name__}: {e}")
                if attempt < 9:
                    time.sleep(1)
        
        if not subscription_success:
            print("✗ No se pudo suscribir al tema después de 10 intentos")
            return

        print(f"✓ Esperando eventos... (Ctrl+C para salir)")
        print("-" * 30)
        
        try:
            ic.waitForShutdown()
        except KeyboardInterrupt:
            print("\n✓ Desconectando...")
        finally:
            try:
                topic.unsubscribe(subscriber)
                print("✓ Desuscrito correctamente")
            except Exception as e:
                print(f"  Nota al desuscribirse: {type(e).__name__}")

if __name__ == '__main__':
    main()