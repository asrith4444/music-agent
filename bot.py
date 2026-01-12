# bot.py

import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from orchestrator import Orchestrator
from db.database import init_db, get_profile, set_profile
from config import TELEGRAM_TOKEN, ALLOWED_USER_ID

# Initialize
init_db()
orchestrator = Orchestrator()

# --- Auth Check ---

def is_authorized(user_id: int) -> bool:
    if ALLOWED_USER_ID == 0:
        return True
    return user_id == ALLOWED_USER_ID

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Sorry, this bot is private.")
        return
    
    await update.message.reply_text(
        "Hey! I'm your music agent.\n\n"
        "Just tell me what you want:\n"
        "• 'gym playlist'\n"
        "• 'something melancholic'\n"
        "• 'surprise me'\n"
        "• 'Anirudh but not the usual ones'\n\n"
        "I'll create a playlist on your YouTube Music."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("Sorry, this bot is private.")
        return
    
    user_request = update.message.text
    
    # Send initial message
    status_msg = await update.message.reply_text("🎵 Starting...")
    
    # Progress callback
    async def update_progress(text: str):
        try:
            await status_msg.edit_text(text)
        except Exception as e:
            print(f"Progress update error: {e}")
    
    try:
        # Run orchestrator with progress callback
        result = await orchestrator.run(user_request, progress_callback=update_progress)
        
        # Format and send final response
        response = format_playlist_response(result)
        await status_msg.edit_text(response, parse_mode='HTML')
        
    except Exception as e:
        await status_msg.edit_text(f"Something went wrong: {str(e)}")

async def set_taste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /taste key value\n\n"
            "Examples:\n"
            "/taste favorite_artists Sid Sriram, DSP, Anirudh\n"
            "/taste hates item songs, remix\n"
            "/taste loves lyrical depth, 90s melodies"
        )
        return
    
    key = args[0]
    value = ' '.join(args[1:])
    set_profile(key, value)
    
    await update.message.reply_text(f"✓ Set {key}: {value}")

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    profile = get_profile()
    
    if not profile:
        await update.message.reply_text("No taste profile set yet. Use /taste to set preferences.")
        return
    
    text = "🎧 Your taste profile:\n\n"
    for key, value in profile.items():
        text += f"<b>{key}</b>: {value}\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your user ID: {user_id}")

# --- Helpers ---

def format_playlist_response(result: dict) -> str:
    name = result.get('playlist_name', 'Your Playlist')
    description = result.get('description', '')
    total = result.get('total_songs', 0)
    duration = result.get('estimated_duration', '')
    url = result.get('youtube_url', '')
    flow = result.get('flow_description', '')
    
    songs = result.get('songs', [])[:5]
    song_list = '\n'.join([
        f"  {s.get('position', i+1)}. {s.get('title', 'Unknown')} - {s.get('artist', '')}"
        for i, s in enumerate(songs)
    ])
    if len(result.get('songs', [])) > 5:
        song_list += f"\n  ... and {len(result.get('songs', [])) - 5} more"
    
    response = f"""🎵 <b>{name}</b>

{description}

<b>Songs ({total}):</b>
{song_list}

{f'<i>{flow}</i>' if flow else ''}
{f'⏱ {duration}' if duration else ''}
"""
    
    if url:
        response += f"\n▶️ <a href='{url}'>Open in YouTube Music</a>"
    
    plan = result.get('orchestrator_plan', {})
    if plan:
        response += f"\n\n<i>Strategy: {plan.get('strategy', '')} | Mood: {plan.get('inferred_mood', '')}</i>"
    
    return response

# --- Main ---

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("taste", set_taste))
    app.add_handler(CommandHandler("profile", show_profile))
    app.add_handler(CommandHandler("myid", get_my_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
