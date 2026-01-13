# orchestrator.py

import json
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from config import llm

from agents.search_agent import SearchAgent
from agents.lyrics_agent import LyricsAgent
from agents.playlist_agent import PlaylistAgent
from db.database import (
    get_profile,
    get_recent_recommendations,
    log_recommendation,
    get_cached_songs
)

INTENT_PROMPT = """You are a music agent assistant.

Determine if the user wants:
1. A playlist/music recommendation
2. Just chatting/greeting
3. Help with settings or profile

Examples:
- "Hi" → chat
- "How are you" → chat
- "gym playlist" → playlist
- "surprise me" → playlist
- "something melancholic" → playlist
- "what can you do" → chat
- "set my taste" → settings

Respond ONLY with valid JSON:
{{
    "intent": "chat" | "playlist" | "settings",
    "response": "your friendly response if chat, null if playlist/settings"
}}
"""

ORCHESTRATOR_PROMPT = """You are a music orchestrator for a music lover.

Your job: Understand what the user wants and decide the best strategy.

User's taste profile:
{profile}

Recent recommendations (avoid repeats):
{recent}

Current context:
- Time: {time}
- Day: {day}

For each request, decide:
1. What is the user really asking for?
2. What mood are they likely in?
3. Should we match their mood or shift it?
4. What search strategy?
5. How many songs? (gym=20, chill=15, quick=10)
6. Any special sequencing?

Respond ONLY with valid JSON:
{{
    "understood_request": "what user actually wants",
    "inferred_mood": "user's likely mood",
    "strategy": "match mood / shift mood / surprise",
    "search_queries": ["query1", "query2"],
    "search_artists": ["artist1"],
    "target_songs": 15,
    "playlist_mood": "how playlist should feel",
    "playlist_flow": "energy flow description",
    "special_instructions": "any other notes"
}}
"""

class Orchestrator:
    def __init__(self):
        self.llm = llm
        self.search_agent = SearchAgent()
        self.lyrics_agent = LyricsAgent()
        self.playlist_agent = PlaylistAgent()
    
    async def run(self, user_request: str, progress_callback=None) -> dict:
        """Main entry point with progress updates."""
        
        async def update(msg):
            if progress_callback:
                await progress_callback(msg)
        
        # Step 0: Check intent
        intent_result = self._check_intent(user_request)
        
        if intent_result['intent'] == 'chat':
            return {
                "type": "chat",
                "message": intent_result.get('response', "Hey! Ask me for a playlist anytime.")
            }
        
        if intent_result['intent'] == 'settings':
            return {
                "type": "settings",
                "message": "Use /taste to set preferences.\nExample: /taste favorite_artists Sid Sriram, DSP"
            }
        
        # Intent is playlist - continue with full flow
        await update("🧠 Understanding your request...")
        
        profile = get_profile()
        recent = get_recent_recommendations(days=30)
        now = datetime.now()
        plan = self._create_plan(user_request, profile, recent, now)
        
        # Step 2: Search
        await update(f"🔍 Searching for songs...")
        
        all_songs = self.search_agent.run(user_request, profile)
        
        from tools.ytmusic import search_songs, get_artist_songs
        
        for query in plan.get('search_queries', []):
            try:
                results = search_songs(query, limit=30)
                all_songs.extend(results)
            except Exception as e:
                print(f"Search error: {e}")
        
        for artist in plan.get('search_artists', []):
            try:
                results = get_artist_songs(artist, limit=20)
                all_songs.extend(results)
            except Exception as e:
                print(f"Artist search error: {e}")
        
        # Deduplicate
        seen = set()
        unique_songs = []
        for song in all_songs:
            if song['song_id'] not in seen and song['song_id'] not in recent:
                seen.add(song['song_id'])
                unique_songs.append(song)
        
        # Limit
        target = plan.get('target_songs', 15)
        MAX_TO_ANALYZE = target * 3
        if len(unique_songs) > MAX_TO_ANALYZE:
            unique_songs = unique_songs[:MAX_TO_ANALYZE]
        
        await update(f"📋 Found {len(unique_songs)} songs")
        
        # Step 3: Check cache
        cached, uncached_ids = get_cached_songs([s['song_id'] for s in unique_songs])
        uncached_songs = [s for s in unique_songs if s['song_id'] in uncached_ids]
        
        await update(f"💾 Cached: {len(cached)} | New: {len(uncached_songs)}")
        
        # Step 4: Analyze with progress
        if uncached_songs:
            analyzed_new = await self.lyrics_agent.analyze_batch_with_progress(
                uncached_songs, 
                user_request, 
                profile,
                progress_callback=update
            )
        else:
            analyzed_new = []
        
        # Step 5: Score cached
        await update("⚖️ Scoring songs against your request...")
        
        analyzed_cached = []
        for song in cached:
            scored = self.lyrics_agent._score_cached(song, user_request, profile)
            analyzed_cached.append(scored)
        
        all_analyzed = analyzed_cached + analyzed_new
        
        # Step 6: Create playlist
        await update("🎼 Creating playlist...")
        
        playlist = self.playlist_agent.create_playlist(
            songs=all_analyzed,
            request=user_request,
            profile=profile,
            target_length=plan.get('target_songs', 15),
            create_on_youtube=True
        )
        
        # Step 7: Log
        for song in playlist.get('songs', []):
            log_recommendation(song['song_id'], user_request)
        
        playlist['orchestrator_plan'] = plan
        playlist['type'] = 'playlist'
        
        return playlist
    
    def _check_intent(self, request: str) -> dict:
        """Determine if user wants playlist, chat, or settings."""
        messages = [
            SystemMessage(content=INTENT_PROMPT),
            HumanMessage(content=request)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return json.loads(response.content)
        except Exception as e:
            print(f"Intent check error: {e}")
            # Default to playlist if unsure
            return {"intent": "playlist", "response": None}
    
    def _create_plan(self, request: str, profile: dict, recent: list, now: datetime) -> dict:
        profile_str = json.dumps(profile, indent=2) if profile else "Not set yet"
        
        prompt = ORCHESTRATOR_PROMPT.format(
            profile=profile_str,
            recent=f"{len(recent)} songs recommended in last 30 days",
            time=now.strftime("%I:%M %p"),
            day=now.strftime("%A")
        )
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=request)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return json.loads(response.content)
        except Exception as e:
            print(f"Plan error: {e}")
            return {
                "understood_request": request,
                "inferred_mood": "neutral",
                "strategy": "match mood",
                "search_queries": [request],
                "search_artists": [],
                "target_songs": 15,
                "playlist_mood": request,
                "playlist_flow": "balanced",
                "special_instructions": ""
            }
