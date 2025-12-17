#!/usr/bin/env python3
import logging
import sys
import json
from pathlib import Path
import Ice
from Ice import identityToString as id2str

Ice.loadSlice('-I{} spotifice_v1.ice'.format(Ice.getSliceDir()))
import Spotifice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MediaServer")

class StreamedFile:
    def __init__(self, track_info, media_dir):
        self.track = track_info
        filepath = media_dir / track_info.filename
        try:
            self.file = open(filepath, 'rb')
        except Exception as e:
            raise Spotifice.IOError(track_info.filename, f"Error opening media file: {e}")

    def read(self, size):
        return self.file.read(size)

    def close(self):
        try:
            if self.file:
                self.file.close()
        except Exception as e:
            logger.error(f"Error closing file for track '{self.track.id}': {e}")

class MediaServerI(Spotifice.MediaServer):
    def __init__(self, media_dir, communicator):
        self.media_dir = Path(media_dir)
        self.tracks = {}
        self.active_streams = {}
        self.playlists = {}
        properties = communicator.getProperties()
        playlist_dir = properties.getPropertyWithDefault('MediaServer.Playlists', 'playlists')
        self.playlist_dir = Path(playlist_dir)
        self.load_media()
        self.load_playlists()

    def load_media(self):
        if not self.media_dir.exists():
            logger.warning(f"Directory {self.media_dir} does not exist.")
            return
        for filepath in sorted(Path(self.media_dir).iterdir()):
            if filepath.is_file() and filepath.suffix.lower() == ".mp3":
                self.tracks[filepath.name] = self.track_info(filepath)
        logger.info(f"Load media:  {len(self.tracks)} tracks")

    def load_playlists(self):
        logger.info(f"Cargando playlists desde {self.playlist_dir}...")
        if not self.playlist_dir.exists(): return
        count = 0
        for filepath in sorted(self.playlist_dir.iterdir()):
            if filepath.suffix.lower() == ".playlist":
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    valid_track_ids = [tid for tid in data.get("track_ids", []) if tid in self.tracks]
                    playlist = Spotifice.Playlist(data.get("id"), data.get("name"), data.get("description", ""), data.get("owner", ""), 0, valid_track_ids)
                    if playlist.id:
                        self.playlists[playlist.id] = playlist
                        count += 1
                except Exception as e:
                    logger.warning(f"Error cargando playlist {filepath.name}: {e}")
        logger.info(f"Load playlists: {count} playlists cargadas.")

    @staticmethod
    def track_info(filepath):
        return Spotifice.TrackInfo(filepath.name, filepath.stem, filepath.name)

    def get_all_tracks(self, current=None):
        return list(self.tracks.values())

    def get_track_info(self, track_id, current=None):
        if track_id not in self.tracks: raise Spotifice.TrackError(track_id, "Track not found")
        return self.tracks[track_id]

    def open_stream(self, track_id, render_id, current=None):
        str_render_id = id2str(render_id)
        if track_id not in self.tracks: raise Spotifice.TrackError(track_id, "Track not found")
        self.active_streams[str_render_id] = StreamedFile(self.tracks[track_id], self.media_dir)
        logger.info(f"Open stream for track '{track_id}' on render '{str_render_id}'")

    def close_stream(self, render_id, current=None):
        str_render_id = id2str(render_id)
        if stream_state := self.active_streams.pop(str_render_id, None):
            stream_state.close()
            logger.info(f"Closed stream for render '{str_render_id}'")

    def get_audio_chunk(self, render_id, chunk_size, current=None):
        str_render_id = id2str(render_id)
        if str_render_id not in self.active_streams: raise Spotifice.StreamError(str_render_id, "No open stream")
        try:
            data = self.active_streams[str_render_id].read(chunk_size)
            if not data:
                logger.info(f"Track exhausted")
                self.close_stream(render_id, current)
            return data
        except Exception as e:
            raise Spotifice.IOError("unknown", f"Error reading file: {e}")

    def get_all_playlists(self, current=None):
        return list(self.playlists.values())

    def get_playlist(self, playlist_id, current=None):
        if playlist_id not in self.playlists: raise Spotifice.PlaylistError(playlist_id, "Playlist no encontrada")
        return self.playlists[playlist_id]

def main(ic):
    properties = ic.getProperties()
    media_dir = properties.getPropertyWithDefault('MediaServer.Content', 'media')
    
    # Identidad Dinámica
    identity = properties.getPropertyWithDefault("MediaServer.Identity", "MediaServer1")

    servant = MediaServerI(Path(media_dir), ic)
    adapter = ic.createObjectAdapter("MediaServerAdapter")
    
    proxy = adapter.add(servant, ic.stringToIdentity(identity))
    logger.info(f"MediaServer '{identity}' ready: {proxy}")

    adapter.activate()
    ic.waitForShutdown()

if __name__ == "__main__":
    try:
        with Ice.initialize(sys.argv) as communicator:
            main(communicator)
    except KeyboardInterrupt:
        pass