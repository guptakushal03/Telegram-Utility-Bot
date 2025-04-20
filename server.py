import json
import os
import logging
import requests
import PyPDF2
from io import BytesIO
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import aiohttp

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = os.getenv("TOKEN")
NOTES_FILE = "notes.json"
SUBSCRIBED_USERS_FILE = "subscribed_users.json"
API_URL = "https://fluxapi-fssj.onrender.com/"
JOKE_API_URL = "https://fluxapi-fssj.onrender.com/joke"
QUOTE_API_URL = "https://fluxapi-fssj.onrender.com/quote"

# Keeping Alive the app as Web Service
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_keep_alive_server():
    server = HTTPServer(('0.0.0.0', 8080), KeepAliveHandler)
    server.serve_forever()

threading.Thread(target=run_keep_alive_server, daemon=True).start()

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

USER_WAITING_FOR_PDF = {}

# start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Bot is online!\n"
        "Welcome to DailyTasker - A project by KG\n"
        "Use the following commands:\n"
        "/joke - Get a random joke\n"
        "/quote - Get a random quote daily\n"
        "/note - A note-taking functionality\n"
        "/summary - Summarize a PDF Document"
    )


# joke
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        try:
            requests.get(JOKE_API_URL, timeout=3)
        except requests.RequestException:
            pass

        await asyncio.sleep(2.5)

        response = requests.get(JOKE_API_URL, timeout=5)
        if response.status_code == 200:
            joke_data = response.json()
            await update.message.reply_text(joke_data.get("joke", "No joke found."))
        else:
            await update.message.reply_text("Failed to fetch a joke. Try again later.")
    except requests.RequestException:
        await update.message.reply_text("Error fetching joke. Please try again later.")


#note
def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {}

def save_notes(notes):
    with open(NOTES_FILE, "w") as f:
        json.dump(notes or [], f, indent=4)

def load_user_notes(user_id):
    notes = load_notes()
    return notes.get(str(user_id), {})

def save_user_notes(user_id, user_notes):
    notes = load_notes()
    notes[str(user_id)] = user_notes
    save_notes(notes)

# run time operations
async def create_note(update: Update, args, user_id):
    if len(args) < 1:
        await update.message.reply_text("Usage: /note create <Note Name>")
        return
    note_name = " ".join(args)
    user_notes = load_user_notes(user_id)
    if note_name in user_notes:
        await update.message.reply_text(f"'{note_name}' already exists!")
    else:
        user_notes[note_name] = []
        save_user_notes(user_id, user_notes)
        await update.message.reply_text(f"Note '{note_name}' created successfully!")

async def add_item(update: Update, args, user_id):
    if len(args) < 2:
        await update.message.reply_text("Usage: /note add <Note Name> <Item>")
        return
    note_name = args[0]
    item = " ".join(args[1:])
    user_notes = load_user_notes(user_id)
    if note_name in user_notes:
        user_notes[note_name].append(item)
        save_user_notes(user_id, user_notes)
        await update.message.reply_text(f"Added '{item}' to '{note_name}'.")
        await show_note(update, [note_name], user_id)
    else:
        await update.message.reply_text(f"Note '{note_name}' does not exist!")

async def show_note(update: Update, args, user_id):
    if len(args) < 1:
        await update.message.reply_text("Usage: /note show <Note Name>")
        return
    note_name = " ".join(args)
    user_notes = load_user_notes(user_id)
    if note_name in user_notes:
        items = "\n".join([f"{i+1}. {item}" for i, item in enumerate(user_notes[note_name])])
        await update.message.reply_text(f"📜 {note_name}:\n{items}" if items else f"'{note_name}' is empty.")
    else:
        await update.message.reply_text(f"Note '{note_name}' does not exist!")

async def list_notes(update: Update, user_id):
    user_notes = load_user_notes(user_id)
    if user_notes:
        await update.message.reply_text("📝 Notes:\n" + "\n".join(user_notes.keys()))
    else:
        await update.message.reply_text("No notes available.")

async def edit_item(update: Update, args, user_id):
    if len(args) < 3:
        await update.message.reply_text("Usage: /note edit <Note Name> <Item Number> <New Text>")
        return
    note_name = args[0]
    try:
        item_index = int(args[1]) - 1
    except ValueError:
        await update.message.reply_text("Item number must be a valid integer.")
        return
    new_text = " ".join(args[2:])
    user_notes = load_user_notes(user_id)
    if note_name in user_notes and 0 <= item_index < len(user_notes[note_name]):
        user_notes[note_name][item_index] = new_text
        save_user_notes(user_id, user_notes)
        await update.message.reply_text(f"Updated item {item_index + 1} in '{note_name}'.")
        await show_note(update, [note_name], user_id)
    else:
        await update.message.reply_text(f"Invalid note or item number.")

async def remove_item(update: Update, args, user_id):
    if len(args) < 2:
        await update.message.reply_text("Usage: /note remove <Note Name> <Item Number>")
        return
    note_name = args[0]
    try:
        item_index = int(args[1]) - 1
    except ValueError:
        await update.message.reply_text("Item number must be a valid integer.")
        return
    user_notes = load_user_notes(user_id)
    if note_name in user_notes and 0 <= item_index < len(user_notes[note_name]):
        removed_item = user_notes[note_name].pop(item_index)
        save_user_notes(user_id, user_notes)
        await update.message.reply_text(f"Removed '{removed_item}' from '{note_name}'.")
        await show_note(update, [note_name], user_id)
    else:
        await update.message.reply_text(f"Invalid note or item number.")

async def delete_note(update: Update, args, user_id):
    note_name = " ".join(args)
    user_notes = load_user_notes(user_id)
    if note_name in user_notes:
        del user_notes[note_name]
        save_user_notes(user_id, user_notes)
        await update.message.reply_text(f"Deleted note '{note_name}'.")
        await list_notes(update, user_id)
    else:
        await update.message.reply_text(f"Note '{note_name}' does not exist.")

async def note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Note Management Commands:\n"
        "/note create <Note Name> - Create a new note\n"
        "/note add <Note Name> <Item> - Add an item to a note\n"
        "/note show <Note Name> - Show all items in a note\n"
        "/note list - List all notes\n"
        "/note edit <Note Name> <Item Number> <New Text> - Edit an item in a note\n"
        "/note remove <Note Name> <Item Number> - Remove an item from a note\n"
        "/note delete <Note Name> - Delete an entire note"
    )

async def note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 1:
        await note(update, context)
        return

    command = context.args[0].lower()
    args = context.args[1:]
    user_id = update.message.chat_id

    if command == "create":
        await create_note(update, args, user_id)
    elif command == "add":
        await add_item(update, args, user_id)
    elif command == "show":
        await show_note(update, args, user_id)
    elif command == "list":
        await list_notes(update, user_id)
    elif command == "edit":
        await edit_item(update, args, user_id)
    elif command == "remove":
        await remove_item(update, args, user_id)
    elif command == "delete":
        await delete_note(update, args, user_id)
    else:
        await update.message.reply_text("Invalid subcommand. Use /note to see available commands.")


# summarize pdf
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    if user_id not in USER_WAITING_FOR_PDF:
        return

    del USER_WAITING_FOR_PDF[user_id]
    document: Document = update.message.document
    file = await context.bot.get_file(document.file_id)
    
    with BytesIO() as pdf_buffer:
        await file.download_to_memory(pdf_buffer)
        pdf_buffer.seek(0)
        
        try:
            reader = PyPDF2.PdfReader(pdf_buffer)
            text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
        except Exception as e:
            await update.message.reply_text("Error extracting text from PDF.")
            return

    if not text.strip():
        await update.message.reply_text("Could not extract readable text from this PDF.")
        return

    summary = summarize_text(text)
    await update.message.reply_text(f"Summary:\n{summary}")

def summarize_text(text):
    sentences = text.split(". ")
    summary = ". ".join(sentences[:5])
    return summary if len(sentences) > 5 else text

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    USER_WAITING_FOR_PDF[update.message.chat_id] = True
    await update.message.reply_text("Please send me a PDF file, and I'll summarize it.")


# For debugging - To know user id
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your chat ID is: {update.message.chat_id}")



# subscription quotes
def load_subscribed_users():
    if os.path.exists(SUBSCRIBED_USERS_FILE):
        with open(SUBSCRIBED_USERS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_subscribed_users(subscribed_users):
    with open(SUBSCRIBED_USERS_FILE, "w") as f:
        json.dump(subscribed_users or [], f, indent=4)

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    command = context.args[0] if context.args else None

    if command is None:
        await update.message.reply_text(
            "Welcome to the Daily Quote Service!\n\n"
            "This is a subscription-based service that sends you an inspiring quote every day at 10:15 am.\n\n"
            "You can manage your subscription using the following commands:\n"
            "/quote subscribe - Subscribe to daily quotes\n"
            "/quote unsubscribe - Unsubscribe from daily quotes\n"
            "/quote status - Check your subscription status"
        )
    elif command == "subscribe":
        subscribed_users = load_subscribed_users()
        if user_id not in subscribed_users:
            subscribed_users.append(user_id)
            save_subscribed_users(subscribed_users)
            await update.message.reply_text("You have successfully subscribed to the daily quote!")
        else:
            await update.message.reply_text("You are already subscribed.")
    
    elif command == "unsubscribe":
        subscribed_users = load_subscribed_users()
        if user_id in subscribed_users:
            subscribed_users.remove(user_id)
            save_subscribed_users(subscribed_users)
            await update.message.reply_text("You have successfully unsubscribed from the daily quote.")
        else:
            await update.message.reply_text("You are not subscribed to the daily quote.")
    
    elif command == "status":
        subscribed_users = load_subscribed_users()
        if user_id in subscribed_users:
            await update.message.reply_text("You are currently subscribed to the daily quote.")
        else:
            await update.message.reply_text("You are not subscribed to the daily quote. Use /quote subscribe to subscribe.")
    
    else:
        await update.message.reply_text(
            "Invalid command. Use:\n"
            "/quote subscribe - Subscribe to daily quote\n"
            "/quote unsubscribe - Unsubscribe from daily quote\n"
            "/quote status - Check your subscription status"
        )

async def send_daily_quote(app: Application) -> None:
    subscribed_users = load_subscribed_users()

    try:
        try:
            requests.get(QUOTE_API_URL, timeout=3)
        except requests.RequestException:
            pass

        await asyncio.sleep(120)

        response = requests.get(QUOTE_API_URL, timeout=5)
        if response.status_code == 200:
            quote_data = response.json()
            quote = quote_data.get("quote", "Stay motivated!")
            for user_id in subscribed_users:
                await app.bot.send_message(user_id, f"Good Morning!\n\nQuote of the Day:\n{quote}")
        else:
            for user_id in subscribed_users:
                await app.bot.send_message(user_id, "Couldn't fetch a quote today.")
    except Exception as e:
        logger.error(f"Error sending daily quote: {e}")
        for user_id in subscribed_users:
            await app.bot.send_message(user_id, "Oops! Something went wrong while fetching the quote.")

# wake up the API
async def wake_api(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = await update.message.reply_text("Waking up the API... This may take up to a minute.")
    
    async def ping_api():
        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(15):
                    async with session.get(JOKE_API_URL) as response:
                        if response.status == 200:
                            await message.edit_text("API is now awake!")
                            return
                    await asyncio.sleep(5)
            await message.edit_text("API did not wake up in time. Please try again later.")
        except Exception as e:
            await message.edit_text("Failed to ping the API. Please try again later.")

    asyncio.create_task(ping_api())

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wake", wake_api))
    app.add_handler(CommandHandler("joke", joke))
    app.add_handler(CommandHandler("quote", quote))
    app.add_handler(CommandHandler("note", note_handler))
    app.add_handler(CommandHandler("summary", summary)) 
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(MessageHandler(filters.Document.MimeType('application/pdf'), handle_pdf))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.run(send_daily_quote(app)),
        trigger='cron',
        hour=10,
        minute=13
    )
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()