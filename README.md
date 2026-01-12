# 🎵 Music Agent

An AI-powered Telegram bot that creates personalized music playlists on YouTube Music based on your mood, preferences, and listening history.

## ✨ Features

- **Natural Language Requests**: Just tell the bot what you want
  - "gym playlist"
  - "something melancholic for tonight"
  - "surprise me"
  - "Anirudh songs but not the usual ones"
  
- **Multi-Agent Orchestration**: Three specialized AI agents work together
  - **Search Agent**: Finds songs using multiple search strategies
  - **Lyrics Agent**: Analyzes song lyrics to match your taste
  - **Playlist Agent**: Sequences songs for optimal flow
  
- **Smart Caching**: Songs are analyzed once and cached — future requests are faster and cheaper

- **YouTube Music Integration**: Creates actual playlists on your YouTube Music account

- **Personalized Taste Profile**: Learns your preferences over time

## 🏗️ Architecture

```
User Request (Telegram)
         │
         ▼
┌─────────────────────────────────────┐
│         ORCHESTRATOR                │
│   (Understands intent, plans)       │
│                                     │
│   • Infers mood from request + time │
│   • Decides search strategy         │
│   • Coordinates all agents          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         SEARCH AGENT                │
│   (Finds candidate songs)           │
│                                     │
│   Tools:                            │
│   • search_songs(query)             │
│   • get_artist_songs(name)          │
│   • get_watch_playlist(song_id)     │
│   • get_liked_songs()               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         LYRICS AGENT                │
│   (Analyzes & scores songs)         │
│                                     │
│   For each song:                    │
│   • Fetch lyrics (if available)     │
│   • Analyze mood, energy, themes    │
│   • Score against user request      │
│   • Cache analysis in SQLite        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         PLAYLIST AGENT              │
│   (Sequences & creates playlist)    │
│                                     │
│   • Orders songs for optimal flow   │
│   • Creates YouTube Music playlist  │
│   • Returns shareable URL           │
└─────────────────────────────────────┘
```

## 📁 Project Structure

```
music-agent/
├── .env                    # Environment variables (not in git)
├── .gitignore
├── config.py               # Configuration and LLM setup
├── bot.py                  # Telegram bot handlers
├── orchestrator.py         # Main orchestration logic
├── browser.json            # YouTube Music auth (not in git)
├── music.db                # SQLite database (not in git)
├── requirements.txt
├── README.md
│
├── agents/
│   ├── __init__.py
│   ├── search_agent.py     # Finds songs via YouTube Music
│   ├── lyrics_agent.py     # Analyzes lyrics and scores
│   └── playlist_agent.py   # Sequences and creates playlist
│
├── tools/
│   ├── __init__.py
│   └── ytmusic.py          # YouTube Music API wrapper
│
└── db/
    ├── __init__.py
    └── database.py         # SQLite operations
```

## 🚀 Setup

### Prerequisites

- Python 3.10+
- Telegram Bot Token (from @BotFather)
- xAI API Key (for Grok)
- YouTube Music account

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/music-agent.git
cd music-agent

# Using uv (recommended)
uv venv
uv pip install -r requirements.txt

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. YouTube Music Authentication

```bash
ytmusicapi browser
```

Follow prompts to authenticate. This creates `browser.json`.

### 3. Create Telegram Bot

1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow prompts to get your bot token

### 4. Environment Variables

Create `.env` file:

```env
TELEGRAM_TOKEN=your-telegram-bot-token
ALLOWED_USER_ID=your-telegram-user-id
XAI_API_KEY=your-xai-api-key
```

To get your Telegram user ID:
1. Run the bot: `python bot.py`
2. Send `/myid` to your bot
3. Update `.env` with the ID

### 5. Run

```bash
python bot.py
```

## 📱 Usage

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/taste key value` | Set taste preference |
| `/profile` | Show current profile |
| `/myid` | Get your Telegram user ID |

### Setting Your Taste Profile

```
/taste favorite_artists Sid Sriram, DSP, Imagine Dragons
/taste loves lyrical depth, melodies, poetry
/taste hates remix, DJ versions
/taste gym high energy, upbeat, workout
/taste night slow, melancholic, emotional
```

### Example Requests

```
gym playlist
something to code to
melancholic evening mood
surprise me with something different
90s classics
chill lo-fi vibes
songs like Bohemian Rhapsody
travel playlist for long drive
```

## 🗄️ Database Schema

```sql
-- Cached song analysis
songs (
    song_id TEXT PRIMARY KEY,
    title TEXT,
    artist TEXT,
    lyrics TEXT,
    mood TEXT,
    energy INTEGER,      -- 1-10 scale
    themes TEXT,         -- JSON array
    analyzed_at TIMESTAMP
)

-- User taste profile
profile (
    key TEXT PRIMARY KEY,
    value TEXT
)

-- Recommendation history (avoid repeats)
recommendations (
    song_id TEXT,
    context TEXT,
    recommended_at TIMESTAMP
)
```

## 💰 Cost Estimation

Using Grok 4.1 Fast (~$0.05 per million tokens):

| Action | Tokens | Cost |
|--------|--------|------|
| One playlist request | ~50,000 | ~₹0.20 |
| Analyzing 50 new songs | ~25,000 | ~₹0.10 |
| Monthly (20 requests/day) | ~30M | ~₹125 |

After initial cache warmup, costs drop significantly since most songs are already analyzed.

## 🚂 Railway Deployment

### 1. Push to GitHub

```bash
git add .
git commit -m "Ready for deployment"
git push
```

### 2. Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Select your repository

### 3. Add Environment Variables

In Railway dashboard, add:
- `TELEGRAM_TOKEN`
- `ALLOWED_USER_ID`
- `XAI_API_KEY`
- `YTMUSIC_AUTH` (contents of browser.json as string)

### 4. Update config.py for Railway

```python
import os
import json

YTMUSIC_AUTH = os.getenv("YTMUSIC_AUTH")

# In ytmusic.py, handle Railway auth:
if os.getenv("YTMUSIC_AUTH"):
    yt = YTMusic(json.loads(os.getenv("YTMUSIC_AUTH")))
else:
    yt = YTMusic(str(BROWSER_JSON))
```

### 5. Add Procfile

```
web: python bot.py
```

## 🔮 Future Enhancements (V2)

- [ ] **Mood Signals**: Infer mood from time, day, recent listening
- [ ] **Conversation Memory**: Multi-turn conversations with context
- [ ] **Scheduled Pings**: Morning playlist suggestions, weekly discovery
- [ ] **Feedback Loop**: Learn from 👍/👎 reactions
- [ ] **Song of the Day**: Proactive daily recommendations
- [ ] **Deeper Profiling**: Learn patterns over time

## 🛠️ Tech Stack

- **LLM**: Grok 4.1 Fast (via xAI API)
- **Framework**: LangChain
- **Music API**: ytmusicapi
- **Bot**: python-telegram-bot
- **Database**: SQLite
- **Deployment**: Railway

## 📝 License

MIT

## 🙏 Acknowledgments

- [ytmusicapi](https://github.com/sigma67/ytmusicapi) for YouTube Music integration
- [LangChain](https://langchain.com) for agent framework
- [xAI](https://x.ai) for Grok API

---

Built with ❤️ for music lovers
