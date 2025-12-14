#!/usr/bin/env python3

import logging
import os
import sys
from contextlib import contextmanager

import Ice
from Ice import identityToString as id2str

from gst_player import GstPlayer

Ice.loadSlice(f'-I{Ice.getSliceDir()} {os.path.abspath(os.path.join(os.path.dirname(__file__), "spotifice_v1.ice"))}')
import Spotifice  # type: ignore # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MediaRender")


class MediaRenderI(Spotifice.MediaRender):
    def __init__(self, player):
        self.player = player
        self.server: Spotifice.MediaServerPrx = None
        self.current_track = None
        
        self.state = Spotifice.PlaybackState.STOPPED
        self.repeat = False
        self.current_playlist: Spotifice.Playlist = None
        self.playlist_index = -1
        self.history = []

    def ensure_player_stopped(self):
        if self.player.is_playing():
            raise Spotifice.PlayerError(reason="Already playing")

    def ensure_server_bound(self):
        if not self.server:
            raise Spotifice.BadReference(reason="No MediaServer bound")

    # --- RenderConnectivity ---

    def bind_media_server(self, media_server, current=None):
        try:
            proxy = media_server.ice_timeout(500)
            proxy.ice_ping()
        except Ice.ConnectionRefusedException as e:
            raise Spotifice.BadReference(reason=f"MediaServer not reachable: {e}")

        self.server = media_server
        logger.info(f"Bound to MediaServer '{id2str(media_server.ice_getIdentity())}'")

    def unbind_media_server(self, current=None):
        self.stop(current)
        self.server = None
        logger.info("Unbound MediaServer")

    # --- ContentManager ---

    def load_track(self, track_id, current=None, _internal_call=False):
        if not _internal_call:
            self.current_playlist = None
            self.playlist_index = -1
            self.history = []

        self.ensure_server_bound()

        try:
            with self.keep_playing_state(current):
                self.current_track = self.server.get_track_info(track_id)

            logger.info(f"Current track set to: {self.current_track.title}")

        except Spotifice.TrackError as e:
            logger.error(f"Error setting track: {e.reason}")
            raise

    def get_current_track(self, current=None):
        return self.current_track

    def load_playlist(self, playlist_id, current=None):
        self.ensure_server_bound()
        
        try:
            playlist = self.server.get_playlist(playlist_id)
            if not playlist.track_ids:
                raise Spotifice.PlaylistError(playlist_id, "Playlist está vacía")

            logger.info(f"Cargando playlist: {playlist.name}")
            self.current_playlist = playlist
            self.playlist_index = 0
            self.history = []
            
            self.load_track(
                self.current_playlist.track_ids[self.playlist_index], 
                current, 
                _internal_call=True
            )

        except Spotifice.Error as e:
            logger.error(f"Error cargando playlist {playlist_id}: {e}")
            raise

    # --- PlaybackController ---

    @contextmanager
    def keep_playing_state(self, current):
        playing = self.player.is_playing()
        if playing:
            self.stop(current)
        try:
            yield
        finally:
            if playing:
                self.play(current)

    def play(self, current=None):
        def get_chunk_hook(chunk_size):
            try:
                return self.server.get_audio_chunk(current.id, chunk_size)
            except Spotifice.IOError as e:
                logger.error(e)
            except Ice.Exception as e:
                logger.critical(e)

        if self.state == Spotifice.PlaybackState.PAUSED:
            logger.info("Reanudando reproducción...")
            self.player.resume()
            self.state = Spotifice.PlaybackState.PLAYING
            return

        assert current, "remote invocation required"

        self.ensure_player_stopped()
        self.ensure_server_bound()

        if not self.current_track:
            raise Spotifice.TrackError(reason="No track loaded")

        try:
            self.server.open_stream(self.current_track.id, current.id)
        except Spotifice.BadIdentity as e:
            logger.error(f"Error starting stream: {e.reason}")
            raise Spotifice.StreamError(reason="Strean setup failed")

        self.player.configure(get_chunk_hook)
        if not self.player.confirm_play_starts():
            raise Spotifice.PlayerError(reason="Failed to confirm playback")

        logger.info(f"Reproduciendo: {self.current_track.title}")
        self.state = Spotifice.PlaybackState.PLAYING
        if not self.history or self.history[-1] != self.current_track.id:
             self.history.append(self.current_track.id)

    def stop(self, current=None):
        if self.server and current:
            try:
                self.server.close_stream(current.id)
            except Ice.Exception:
                pass

        if not self.player.stop():
            raise Spotifice.PlayerError(reason="Failed to confirm stop")

        logger.info("Reproducción detenida.")
        self.state = Spotifice.PlaybackState.STOPPED

    def pause(self, current=None):
        if self.state != Spotifice.PlaybackState.PLAYING:
            logger.warning("No se puede pausar, no está reproduciendo.")
            return

        self.player.pause()
        self.state = Spotifice.PlaybackState.PAUSED
        logger.info("Reproducción pausada.")
    
    def get_status(self, current=None):
        track_id = self.current_track.id if self.current_track else ""
        
        status = Spotifice.PlaybackStatus(
            state=self.state,
            current_track_id=track_id,
            repeat=self.repeat
        )
        return status

    def set_repeat(self, value, current=None):
        logger.info(f"Modo Repetir: {'Activado' if value else 'Desactivado'}")
        self.repeat = value

    def next(self, current=None):
        if not self.current_playlist:
            logger.warning("Siguiente: No hay playlist cargada.")
            return
            
        was_playing = (self.state == Spotifice.PlaybackState.PLAYING)
        
        self.playlist_index += 1
        
        if self.playlist_index >= len(self.current_playlist.track_ids):
            if self.repeat:
                self.playlist_index = 0
            else:
                logger.info("Siguiente: Fin de la playlist.")
                self.playlist_index -= 1
                return
        
        logger.info(f"Siguiente: Cargando track {self.playlist_index}")
        
        track_id = self.current_playlist.track_ids[self.playlist_index]
        self.load_track(track_id, current, _internal_call=True)

    def previous(self, current=None):
        if len(self.history) < 2:
            logger.warning("Anterior: No hay historial previo.")
            return

        was_playing = (self.state == Spotifice.PlaybackState.PLAYING)

        self.history.pop()
        track_id = self.history.pop()
        
        logger.info(f"Anterior: Cargando track {track_id}")
        
        self.load_track(track_id, current, _internal_call=True)
        


def main(ic, player):
    servant = MediaRenderI(player)

    adapter = ic.createObjectAdapter("MediaRenderAdapter")
    proxy = adapter.add(servant, ic.stringToIdentity("mediaRender1"))
    logger.info(f"MediaRender: {proxy}")

    adapter.activate()
    ic.waitForShutdown()

    logger.info("Shutdown")


if __name__ == "__main__":
    # Eliminamos el chequeo estricto
    player = GstPlayer()
    player.start()
    try:
        # Usamos sys.argv completo
        with Ice.initialize(sys.argv) as communicator:
            main(communicator, player)
    except KeyboardInterrupt:
        logger.info("Server interrupted by user.")
    finally:
        player.shutdown()