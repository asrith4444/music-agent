# agents/search_agent.py

import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from config import llm

@tool
def search_songs(query: str) -> list:
    """Search YouTube Music for songs"""
    from tools.ytmusic import search_songs as yt_search
    return yt_search(query, limit=30)

@tool
def get_artist_songs(artist_name: str) -> list:
    """Get songs by a specific artist"""
    from tools.ytmusic import get_artist_songs as yt_artist
    return yt_artist(artist_name, limit=20)

@tool
def get_watch_playlist(song_id: str) -> list:
    """Get similar songs to a specific song"""
    from tools.ytmusic import get_watch_playlist as yt_watch
    return yt_watch(song_id, limit=25)

@tool
def get_liked_songs() -> list:
    """Get user's liked songs from YouTube Music"""
    from tools.ytmusic import get_liked_songs as yt_liked
    return yt_liked(limit=50)

SEARCH_AGENT_PROMPT = """You are a Telugu music search expert.

Your job: Given a user request and their taste profile, decide what searches to run to find the best songs.

User's taste profile:
{profile}

Rules:
1. Cast a wide net. Run multiple searches with different angles.
2. For gym/workout: search high energy, mass, upbeat
3. For sad/melancholic: search melody, emotional, slow
4. For surprise: go outside user's usual patterns
5. Always consider Telugu songs primarily
6. Call multiple tools to gather diverse results
"""

class SearchAgent:
    def __init__(self):
        self.tools = [search_songs, get_artist_songs, get_watch_playlist, get_liked_songs]
        self.llm_with_tools = llm.bind_tools(self.tools)
    
    def run(self, request: str, profile: dict) -> list:
        """Search for songs based on request and profile"""
        profile_str = json.dumps(profile, indent=2)
        prompt = SEARCH_AGENT_PROMPT.format(profile=profile_str)
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Find songs for: {request}")
        ]
        
        all_songs = []
        max_iterations = 10  # prevent infinite loop
        
        for _ in range(max_iterations):
            response = self.llm_with_tools.invoke(messages)
            
            if not response.tool_calls:
                break
            
            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                for t in self.tools:
                    if t.name == tool_name:
                        try:
                            result = t.invoke(tool_args)
                            all_songs.extend(result)
                        except Exception as e:
                            print(f"Tool {tool_name} error: {e}")
                        break
            
            # Add response and continue
            messages.append(response)
            messages.append(HumanMessage(content=f"Found {len(all_songs)} songs so far. Need more variety? Call more tools or say DONE."))
        
        # Deduplicate
        seen = set()
        unique = []
        for song in all_songs:
            if song['song_id'] not in seen:
                seen.add(song['song_id'])
                unique.append(song)
        
        return unique
