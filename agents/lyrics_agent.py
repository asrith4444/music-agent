# agents/lyrics_agent.py

import json
from langchain_core.messages import HumanMessage, SystemMessage
from config import llm

LYRICS_ANALYSIS_PROMPT = """You are a song lyrics analyst.

Analyze the song lyrics and determine if they match the user's taste.

User's taste profile:
{profile}

Current request: {request}

Analyze:
1. Mood (happy, sad, romantic, energetic, melancholic, devotional, etc.)
2. Energy (1-10 scale, 1=slow ballad, 10=high energy)
3. Themes (love, heartbreak, friendship, motivation, nostalgia, etc.)
4. Match score (1-10, how well it fits the request)

If lyrics are not available, make best guess from title/artist.

Respond ONLY with valid JSON:
{{
    "mood": "romantic, longing",
    "energy": 4,
    "themes": ["love", "rain", "memories"],
    "match_score": 8,
    "reason": "Poetic lyrics about longing, matches user's preference"
}}
"""

SCORE_CACHED_PROMPT = """Score how well this song matches the current request.

User's taste profile:
{profile}

Current request: {request}

Song info:
- Title: {title}
- Artist: {artist}
- Mood: {mood}
- Energy: {energy}
- Themes: {themes}

Respond ONLY with valid JSON:
{{
    "match_score": 8,
    "reason": "High energy matches gym request"
}}
"""

class LyricsAgent:
    def __init__(self):
        self.llm = llm
    
    async def analyze_batch_with_progress(
        self, 
        songs: list, 
        request: str, 
        profile: dict,
        progress_callback=None
    ) -> list:
        """Analyze songs with progress updates."""
        from tools.ytmusic import get_lyrics
        from db.database import get_song, save_song
        
        analyzed = []
        total = len(songs)
        
        for i, song in enumerate(songs):
            # Progress update every 5 songs
            if progress_callback and (i % 5 == 0 or i == total - 1):
                await progress_callback(f"🎵 Analyzing songs... {i + 1}/{total}")
            
            # Check cache
            cached = get_song(song['song_id'])
            if cached and cached.get('mood'):
                scored = self._score_cached(cached, request, profile)
                analyzed.append(scored)
                continue
            
            # Fetch lyrics
            if 'lyrics' not in song or not song['lyrics']:
                lyrics_data = get_lyrics(song['song_id'])
                song['lyrics'] = lyrics_data['lyrics'] if lyrics_data else None
            
            # Analyze
            analysis = self._analyze_single(song, request, profile)
            
            # Save
            save_song({
                "song_id": song['song_id'],
                "title": song.get('title'),
                "artist": song.get('artist'),
                "lyrics": song.get('lyrics'),
                "mood": analysis.get('mood'),
                "energy": analysis.get('energy'),
                "themes": json.dumps(analysis.get('themes', []))
            })
            
            analyzed.append(analysis)
        
        return analyzed
    
    def analyze_batch(self, songs: list, request: str, profile: dict) -> list:
        """Sync version without progress (for backwards compatibility)."""
        from tools.ytmusic import get_lyrics
        from db.database import get_song, save_song
        
        analyzed = []
        
        for song in songs:
            cached = get_song(song['song_id'])
            if cached and cached.get('mood'):
                scored = self._score_cached(cached, request, profile)
                analyzed.append(scored)
                continue
            
            if 'lyrics' not in song or not song['lyrics']:
                lyrics_data = get_lyrics(song['song_id'])
                song['lyrics'] = lyrics_data['lyrics'] if lyrics_data else None
            
            analysis = self._analyze_single(song, request, profile)
            
            save_song({
                "song_id": song['song_id'],
                "title": song.get('title'),
                "artist": song.get('artist'),
                "lyrics": song.get('lyrics'),
                "mood": analysis.get('mood'),
                "energy": analysis.get('energy'),
                "themes": json.dumps(analysis.get('themes', []))
            })
            
            analyzed.append(analysis)
        
        return analyzed
    
    def _analyze_single(self, song: dict, request: str, profile: dict) -> dict:
        profile_str = json.dumps(profile, indent=2)
        prompt = LYRICS_ANALYSIS_PROMPT.format(profile=profile_str, request=request)
        
        lyrics_preview = song.get('lyrics', 'Not available')
        if lyrics_preview and len(lyrics_preview) > 2000:
            lyrics_preview = lyrics_preview[:2000] + "..."
        
        song_info = f"""
Song: {song.get('title', 'Unknown')}
Artist: {song.get('artist', 'Unknown')}
Lyrics: {lyrics_preview}
"""
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=song_info)
        ]
        
        try:
            response = self.llm.invoke(messages)
            analysis = json.loads(response.content)
            analysis['song_id'] = song['song_id']
            analysis['title'] = song.get('title')
            analysis['artist'] = song.get('artist')
            return analysis
        except Exception as e:
            print(f"Analysis error for {song.get('title')}: {e}")
            return {
                "song_id": song['song_id'],
                "title": song.get('title'),
                "artist": song.get('artist'),
                "mood": "unknown",
                "energy": 5,
                "themes": [],
                "match_score": 5,
                "reason": "Could not analyze"
            }
    
    def _score_cached(self, cached: dict, request: str, profile: dict) -> dict:
        profile_str = json.dumps(profile, indent=2)
        
        themes = cached.get('themes', '[]')
        if isinstance(themes, str):
            try:
                themes = json.loads(themes)
            except:
                themes = []
        
        prompt = SCORE_CACHED_PROMPT.format(
            profile=profile_str,
            request=request,
            title=cached.get('title'),
            artist=cached.get('artist'),
            mood=cached.get('mood'),
            energy=cached.get('energy'),
            themes=themes
        )
        
        messages = [
            SystemMessage(content="You score songs against user requests. Respond only with JSON."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            score_data = json.loads(response.content)
            return {
                **cached,
                "themes": themes,
                "match_score": score_data.get('match_score', 5),
                "reason": score_data.get('reason', '')
            }
        except Exception as e:
            print(f"Scoring error: {e}")
            return {**cached, "themes": themes, "match_score": 5, "reason": ""}
