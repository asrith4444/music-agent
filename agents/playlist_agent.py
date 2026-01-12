# agents/playlist_agent.py

import json
from langchain_core.messages import HumanMessage, SystemMessage
from config import llm

PLAYLIST_AGENT_PROMPT = """You are a playlist curator and sequencing expert.

Your job: Take analyzed songs and create a perfectly ordered playlist.

User's taste profile:
{profile}

Sequencing rules:
1. Start with a song that hooks — not too slow, not peak energy
2. Build energy gradually for first 30%
3. Peak energy around 40-60% of playlist
4. Maintain with slight variations
5. Wind down last 2-3 songs (unless gym/party playlist)
6. Avoid back-to-back songs by same artist
7. Consider mood transitions — don't jump from heartbreak to party
8. For gym: keep energy high throughout, peak early
9. For sleep/chill: keep energy low, gradually decrease
10. For travel: singalong peaks, varied energy

Respond ONLY with valid JSON:
{{
    "playlist_name": "Evening Melancholy Mix",
    "description": "A journey through longing and nostalgia",
    "total_songs": 15,
    "estimated_duration": "52 mins",
    "songs": [
        {{
            "position": 1,
            "song_id": "xxx",
            "title": "Song Name",
            "artist": "Artist",
            "reason": "Gentle opener, sets melancholic tone"
        }}
    ],
    "flow_description": "Opens soft, builds emotional intensity mid-playlist, resolves with peaceful acceptance"
}}
"""

class PlaylistAgent:
    def __init__(self):
        self.llm = llm
    
    def create_playlist(
        self, 
        songs: list, 
        request: str, 
        profile: dict,
        target_length: int = 15,
        create_on_youtube: bool = True
    ) -> dict:
        """
        Create an ordered playlist from analyzed songs.
        """
        profile_str = json.dumps(profile, indent=2)
        prompt = PLAYLIST_AGENT_PROMPT.format(profile=profile_str)
        
        # Sort by match_score, take top candidates
        sorted_songs = sorted(songs, key=lambda x: x.get('match_score', 0), reverse=True)
        candidates = sorted_songs[:target_length * 2]
        
        songs_info = json.dumps([
            {
                "song_id": s['song_id'],
                "title": s.get('title'),
                "artist": s.get('artist'),
                "mood": s.get('mood'),
                "energy": s.get('energy'),
                "themes": s.get('themes'),
                "match_score": s.get('match_score')
            }
            for s in candidates
        ], indent=2)
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"""
Request: {request}
Target length: {target_length} songs

Available songs (pick and sequence the best ones):
{songs_info}

Create the playlist.
""")
        ]
        
        try:
            response = self.llm.invoke(messages)
            playlist = json.loads(response.content)
        except Exception as e:
            print(f"Playlist creation error: {e}")
            playlist = {
                "playlist_name": request,
                "description": "",
                "total_songs": target_length,
                "songs": [
                    {
                        "position": i + 1,
                        "song_id": s['song_id'],
                        "title": s.get('title'),
                        "artist": s.get('artist'),
                        "reason": ""
                    }
                    for i, s in enumerate(candidates[:target_length])
                ],
                "flow_description": ""
            }
        
        # Create actual YouTube Music playlist
        if create_on_youtube:
            from tools.ytmusic import create_playlist, add_to_playlist, get_playlist_url
            
            try:
                yt_playlist_id = create_playlist(
                    title=playlist.get('playlist_name', request),
                    description=playlist.get('description', '')
                )
                
                song_ids = [s['song_id'] for s in playlist['songs']]
                add_to_playlist(yt_playlist_id, song_ids)
                
                playlist['youtube_url'] = get_playlist_url(yt_playlist_id)
                playlist['playlist_id'] = yt_playlist_id
            except Exception as e:
                print(f"YouTube playlist error: {e}")
                playlist['youtube_error'] = str(e)
                playlist['youtube_url'] = None
        
        return playlist

