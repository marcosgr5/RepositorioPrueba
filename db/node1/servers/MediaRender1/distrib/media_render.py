#!/usr/bin/env python3
import logging
import sys
import os
from contextlib import contextmanager
import Ice
import IceStorm  # Importante para Hito 3
from Ice import identityToString as id2str
from gst_player import GstPlayer

Ice.loadSlice(f'-I{Ice.getSliceDir()} {os.path.abspath(os.path.join(os.path.dirname(__file__), "spotifice_v1.ice"))}')
import Spotifice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MediaRender")

class MediaRenderI(Spotifice.MediaRender):
    def __init__(self, player, ic):
        self.player = player
        self.ic = ic  # Guardamos el comunicador para conectar a IceStorm
        self.server = None
        self.current_track = None
        self.state = Spotifice.PlaybackState.STOPPED
        self.repeat = False
        self.current_playlist = None
        self.playlist_index = -1
        self.history = []

        # --- HITO 3: Configuración de IceStorm ---
        self.publisher = None
        self.topic_name = "Updates"
        try:
            # Conectar al TopicManager (puerto 9999 definido en XML)
            obj = self.ic.stringToProxy("SpotificeIceStorm/TopicManager:tcp -p 9999")
            topic_manager = IceStorm.TopicManagerPrx.checkedCast(obj)
            
            if topic_manager:
                try:
                    topic = topic_manager.retrieve(self.topic_name)
                except IceStorm.NoSuchTopic:
                    topic = topic_manager.create(self.topic_name)
                
                # Obtener el publicador
                pub = topic.getPublisher()
                # UncheckedCast es más rápido y suficiente para publicar
                self.publisher = Spotifice.MonitorPrx.uncheckedCast(pub)
                logger.info("Connected to IceStorm 'Updates' topic")
        except Exception as e:
            logger.warning(f"Could not connect to IceStorm: {e}")
    
    def _notify(self):
        """Método auxiliar para enviar eventos a IceStorm"""
        if self.publisher and self.current_track:
            try:
                status = self.get_status()
                # Enviamos el evento (One-way para no bloquear)
                self.publisher.report(status, self.current_track)
            except Exception as e:
                logger.warning(f"Error publishing notification: {e}")

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

    def load_track(self, track_id, current=None, _internal_call=False):
        if not _internal_call:
            self.current_playlist = None
            self.history = []
        if not self.server: raise Spotifice.BadReference("No server")
        with self.keep_playing_state(current):
            self.current_track = self.server.get_track_info(track_id)
        logger.info(f"Track loaded: {self.current_track.title}")
        self._notify()  # Notificar carga

    def get_current_track(self, current=None):
        return self.current_track

    def load_playlist(self, playlist_id, current=None):
        if not self.server: raise Spotifice.BadReference("No server")
        pl = self.server.get_playlist(playlist_id)
        if not pl.track_ids: raise Spotifice.PlaylistError(playlist_id, "Empty")
        self.current_playlist = pl
        self.playlist_index = 0
        self.history = []
        self.load_track(pl.track_ids[0], current, _internal_call=True)

    @contextmanager
    def keep_playing_state(self, current):
        playing = self.player.is_playing()
        if playing: self.stop(current)
        try: yield
        finally: 
            if playing: self.play(current)

    def play(self, current=None):
        if self.state == Spotifice.PlaybackState.PAUSED:
            self.player.resume()
            self.state = Spotifice.PlaybackState.PLAYING
            self._notify() # Notificar reanudar
            return
        if not self.current_track: raise Spotifice.TrackError("No track")
        if not self.server: raise Spotifice.BadReference("No server")
        
        def get_chunk(size):
            try: 
                return self.server.get_audio_chunk(current.id, size)
            except Exception as e: 
                logger.error(f"Error getting chunk: {e}")
                return None
        
        def on_track_exhausted():
            logger.info(f"Track exhausted: {self.current_track.id}")
            self.state = Spotifice.PlaybackState.STOPPED
            self._notify() # Notificar fin
        
        self.server.open_stream(self.current_track.id, current.id)
        self.player.configure(get_chunk, track_exhausted_hook=on_track_exhausted)
        self.player.confirm_play_starts()
        self.state = Spotifice.PlaybackState.PLAYING
        if not self.history or self.history[-1] != self.current_track.id:
            self.history.append(self.current_track.id)
        logger.info(f"Playing: {self.current_track.title}")
        self._notify() # Notificar play

    def stop(self, current=None):
        if self.server and current:
            try: self.server.close_stream(current.id)
            except Exception as e: logger.debug(f"Error closing stream: {e}")
        self.player.stop()
        self.state = Spotifice.PlaybackState.STOPPED
        self._notify() # Notificar stop

    def pause(self, current=None):
        if self.state != Spotifice.PlaybackState.PLAYING:
            return
        if not self.player.is_playing():
            self.state = Spotifice.PlaybackState.STOPPED
            self._notify()
            return
        self.player.pause()
        self.state = Spotifice.PlaybackState.PAUSED
        logger.info("Reproducción pausada.")
        self._notify() # Notificar pausa

    def get_status(self, current=None):
        tid = self.current_track.id if self.current_track else ""
        return Spotifice.PlaybackStatus(self.state, tid, self.repeat)

    def next(self, current=None):
        if not self.current_playlist: return
        self.playlist_index += 1
        if self.playlist_index >= len(self.current_playlist.track_ids):
             self.playlist_index = 0
        self.load_track(self.current_playlist.track_ids[self.playlist_index], current, True)

    def previous(self, current=None):
        if len(self.history) > 1:
            self.history.pop()
            self.load_track(self.history.pop(), current, True)
    
    def set_repeat(self, value, current=None):
        self.repeat = value
        logger.info(f"Set repeat: {value}")


def main(ic, player):
    properties = ic.getProperties()
    # Identidad Dinámica
    identity = properties.getPropertyWithDefault("MediaRender.Identity", "MediaRender1")

    # Pasamos 'ic' para conectar a IceStorm
    servant = MediaRenderI(player, ic)
    adapter = ic.createObjectAdapter("MediaRenderAdapter")
    
    proxy = adapter.add(servant, ic.stringToIdentity(identity))
    logger.info(f"MediaRender '{identity}' ready: {proxy}")

    adapter.activate()
    ic.waitForShutdown()

if __name__ == "__main__":
    player = GstPlayer()
    player.start()
    try:
        with Ice.initialize(sys.argv) as communicator:
            main(communicator, player)
    except KeyboardInterrupt:
        pass
    finally:
        player.shutdown()