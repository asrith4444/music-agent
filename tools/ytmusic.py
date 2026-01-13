# tools/ytmusic.py

import os
import json
from pathlib import Path
from ytmusicapi import YTMusic

# Check for Railway environment variable first
YTMUSIC_AUTH = os.getenv("YTMUSIC_AUTH")

if YTMUSIC_AUTH:
    # Railway: use env variable
    yt = YTMusic(YTMUSIC_AUTH)
else:
    # Local: use file
    PROJECT_ROOT = Path(__file__).parent.parent
    BROWSER_JSON = PROJECT_ROOT / "browser.json"
    yt = YTMusic(str(BROWSER_JSON))

def get_history(limit=50):
    """Get recent listening history"""
    history = yt.get_history()[:limit]
    return [
        {
            "song_id": song['videoId'],
            "title": song['title'],
            "artist": song['artists'][0]['name'] if song.get('artists') else "Unknown",
            "album": (song.get('album') or {}).get('name', ''),
        }
        for song in history
    ]

def search_songs(query, limit=40):
    """Search for songs"""
    results = yt.search(query, filter="songs", limit=limit)
    return [
        {
            "song_id": r['videoId'],
            "title": r['title'],
            "artist": r['artists'][0]['name'] if r.get('artists') else "Unknown",
            "album": (r.get('album') or {}).get('name', ''),
        }
        for r in results
    ]

def get_artist_songs(artist_name, limit=30):
    """Get songs by artist"""
    search = yt.search(artist_name, filter="artists", limit=1)
    if not search:
        return []
    artist_id = search[0]['browseId']
    artist = yt.get_artist(artist_id)
    songs = artist.get('songs', {}).get('results', [])[:limit]
    return [
        {
            "song_id": s['videoId'],
            "title": s['title'],
            "artist": artist_name,
        }
        for s in songs
    ]

def get_watch_playlist(song_id, limit=25):
    """Get 'radio' / related songs for a song"""
    playlist = yt.get_watch_playlist(song_id)
    tracks = playlist.get('tracks', [])[:limit]
    return [
        {
            "song_id": t['videoId'],
            "title": t['title'],
            "artist": t['artists'][0]['name'] if t.get('artists') else "Unknown",
        }
        for t in tracks
    ]

def get_lyrics(song_id):
    """Get lyrics for a song"""
    try:
        watch = yt.get_watch_playlist(song_id)
        lyrics_browse_id = watch.get('lyrics')
        
        if not lyrics_browse_id:
            return None
        
        lyrics_data = yt.get_lyrics(lyrics_browse_id)
        
        if not lyrics_data:
            return None
            
        return {
            "song_id": song_id,
            "lyrics": lyrics_data.get('lyrics', ''),
            "source": lyrics_data.get('source', '')
        }
    except Exception as e:
        print(f"Lyrics error for {song_id}: {e}")
        return None

def create_playlist(title, description=""):
    """Create a new playlist, returns playlist_id"""
    playlist_id = yt.create_playlist(title, description)
    return playlist_id

def add_to_playlist(playlist_id, song_ids):
    """Add songs to a playlist"""
    yt.add_playlist_items(playlist_id, song_ids)
    return {"status": "added", "count": len(song_ids)}

def get_playlist_url(playlist_id):
    """Get shareable link"""
    return f"https://music.youtube.com/playlist?list={playlist_id}"

def get_liked_songs(limit=100):
    """Get user's liked songs"""
    liked = yt.get_liked_songs(limit=limit)
    return [
        {
            "song_id": t['videoId'],
            "title": t['title'],
            "artist": t['artists'][0]['name'] if t.get('artists') else "Unknown",
        }
        for t in liked.get('tracks', [])
    ]


if __name__ == "__main__":
    history = get_history()
    print(f"Found {len(history)} songs")
    for song in history[:5]:
        print(f"  {song['title']} - {song['artist']}")
