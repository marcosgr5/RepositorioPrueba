#!/usr/bin/env python3

import sys
from time import sleep

import Ice

Ice.loadSlice('-I{} spotifice_v1.ice'.format(Ice.getSliceDir()))
import Spotifice  # type: ignore # noqa: E402


def get_proxy(ic, property, cls):
    proxy = ic.propertyToProxy(property)

    for _ in range(5):
        try:
            proxy.ice_ping()
            break
        except Ice.ConnectionRefusedException:
            sleep(0.5)

    object = cls.checkedCast(proxy)
    if object is None:
        raise RuntimeError(f'Invalid proxy for {property}')

    return object


def main(ic):
    server = get_proxy(ic, 'MediaServer.Proxy', Spotifice.MediaServerPrx)
    render = get_proxy(ic, 'MediaRender.Proxy', Spotifice.MediaRenderPrx)

    print("--- Probando Hito 1 ---")
    
    render.bind_media_server(server)
    render.stop()

    print("Fetching all playlists...")
    playlists = server.get_all_playlists()
    if not playlists:
        print("No playlists found.")
        return

    for p in playlists:
        print(f"- Playlist: {p.name} ({len(p.track_ids)} tracks)")

    playlist_id = playlists[0].id
    print(f"\nCargando playlist {playlist_id}...")
    render.load_playlist(playlist_id)
    
    track = render.get_current_track()
    print(f"Track actual (automático por Hito 1): {track.title}")

    print("\nReproduciendo por 3 segundos...")
    render.play()
    sleep(3)
    
    print("Pausando por 2 segundos...")
    render.pause()
    status = render.get_status()
    print(f"Estado actual: {status.state}")
    sleep(2)

    print("Reanudando (con play())...")
    render.play()
    status = render.get_status()
    print(f"Estado actual: {status.state}")
    sleep(2)

    print("\nProbando Next()...")
    render.next()
    track = render.get_current_track()
    print(f"Nuevo track (Next): {track.title}")
    sleep(3)

    print("\nProbando Previous()...")
    render.previous()
    track = render.get_current_track()
    print(f"Track anterior (Previous): {track.title}")
    sleep(3)

    print("\nParando.")
    render.stop()
    status = render.get_status()
    print(f"Estado final: {status.state}")


if __name__ == '__main__':
    # Eliminamos el chequeo estricto
    # Usamos sys.argv completo
    with Ice.initialize(sys.argv) as communicator:
        main(communicator)