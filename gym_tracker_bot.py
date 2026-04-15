"""
Gym Weight Tracker — Telegram Bot + Google Sheets
===================================================
Send your lifting data via Telegram, and it gets logged straight
to a Google Sheet in your Drive.

Usage in Telegram:
  /start                — Welcome message
  /log                  — Interactive logging (step by step)
  /log bench 80,85,90 8,8,6          — Quick log (exercise weights reps)
  /log bench 80,85,90 8,8,6 felt great  — With notes
  /history              — Last 10 entries
  /exercises            — List all tracked exercises
  /today                — Show today's session
  /help                 — Show commands
"""

import os
import json
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
GOOGLE_CREDS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID", "")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

ASK_EXERCISE, ASK_WEIGHTS, ASK_REPS, ASK_NOTES = range(4)

# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_gc = None
_sheet = None

HEADERS = ["Date", "Time", "Exercise", "Sets", "Weights (kg)",
           "Reps", "Max Weight", "Total Volume", "Notes"]


def get_sheet():
    global _gc, _sheet
    if _sheet is not None:
        return _sheet

    if GOOGLE_CREDS_JSON:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=SCOPES)

    _gc = gspread.authorize(creds)
    spreadsheet = _gc.open_by_key(SHEET_ID)

    try:
        _sheet = spreadsheet.worksheet("Gym Log")
    except gspread.WorksheetNotFound:
        _sheet = spreadsheet.add_worksheet(title="Gym Log", rows=1000, cols=len(HEADERS))

    if not _sheet.row_values(1):
        _sheet.update("A1", [HEADERS])
        _sheet.format("A1:I1", {
            "backgroundColor": {"red": 0.184, "green": 0.329, "blue": 0.588},
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "fontFamily": "Arial", "fontSize": 11,
            },
            "horizontalAlignment": "CENTER",
        })
        _sheet.freeze(rows=1)

    logger.info("Connected to Google Sheet: %s", SHEET_ID)
    return _sheet


def reconnect_sheet():
    global _gc, _sheet
    _gc = None
    _sheet = None
    return get_sheet()


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def parse_numbers(text: str) -> list[float]:
    tokens = text.replace(",", " ").split()
    nums = []
    for t in tokens:
        try:
            nums.append(float(t))
        except ValueError:
            continue
    return nums


def append_entry(exercise: str, weights: list[float],
                 reps: list[int], notes: str = "") -> dict:
    now = datetime.now()
    num_sets = len(weights)
    max_weight = max(weights) if weights else 0
    total_volume = sum(
        w * (reps[i] if i < len(reps) else 0)
        for i, w in enumerate(weights)
    )

    weights_str = ", ".join(f"{w:g}" for w in weights)
    reps_str = ", ".join(str(r) for r in reps)

    row = [
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M"),
        exercise.title(),
        num_sets,
        weights_str,
        reps_str,
        f"{max_weight:g}",
        f"{total_volume:g}",
        notes,
    ]

    try:
        sheet = get_sheet()
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception:
        logger.warning("Reconnecting to Google Sheets…")
        sheet = reconnect_sheet()
        sheet.append_row(row, value_input_option="USER_ENTERED")

    return {
        "exercise": exercise.title(),
        "sets": num_sets,
        "weights": weights,
        "reps": reps,
        "max_w": max_weight,
        "volume": total_volume,
        "notes": notes,
        "date": now.strftime("%Y-%m-%d %H:%M"),
    }


def get_recent_entries(n: int = 10) -> list[list[str]]:
    try:
        all_rows = get_sheet().get_all_values()
    except Exception:
        all_rows = reconnect_sheet().get_all_values()
    data_rows = all_rows[1:]
    return data_rows[-n:] if data_rows else []


def get_today_entries() -> list[list[str]]:
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        all_rows = get_sheet().get_all_values()
    except Exception:
        all_rows = reconnect_sheet().get_all_values()
    return [r for r in all_rows[1:] if r and r[0] == today]


def get_exercises() -> list[str]:
    try:
        all_rows = get_sheet().get_all_values()
    except Exception:
        all_rows = reconnect_sheet().get_all_values()
    exercises = set()
    for row in all_rows[1:]:
        if row and len(row) >= 3 and row[2]:
            exercises.add(row[2])
    return sorted(exercises)


# ---------------------------------------------------------------------------
# Auth check
# ---------------------------------------------------------------------------
def is_authorized(update: Update) -> bool:
    if not ALLOWED_USER_ID:
        return True
    return str(update.effective_user.id) == ALLOWED_USER_ID


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------
def _format_entry_summary(entry: dict) -> str:
    sets_detail = []
    for i, w in enumerate(entry["weights"]):
        r = entry["reps"][i] if i < len(entry["reps"]) else "?"
        sets_detail.append(f"  Set {i+1}: {w:g} kg × {r} reps")
    sets_str = "\n".join(sets_detail)

    text = (
        f"✅ *{entry['exercise']}* logged!\n\n"
        f"{sets_str}\n\n"
        f"🏆 Max: *{entry['max_w']:g}* kg\n"
        f"📊 Volume: *{entry['volume']:g}* kg\n"
        f"🔢 Sets: {entry['sets']}"
    )
    if entry["notes"]:
        text += f"\n📝 {entry['notes']}"
    text += f"\n📅 {entry['date']}"
    return text


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "🏋️ *Gym Weight Tracker*\n\n"
        "Log your lifts and I'll save them to your Google Sheet.\n\n"
        "*Quick log:*\n"
        "`/log bench 80,85,90 8,8,6`\n"
        "`/log squat 100,110,120 5,5,5 new belt`\n\n"
        "*Step-by-step:*\n"
        "Just type `/log` and I'll ask you each field.\n\n"
        "Type /help for all commands.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "📋 *Commands*\n\n"
        "*Log weights (quick):*\n"
        "`/log bench 80,85,90 8,8,6`\n"
        "`/log bench 80,85,90 8,8,6 felt strong`\n\n"
        "*Log weights (guided):*\n"
        "`/log` → I'll ask step by step\n\n"
        "*View data:*\n"
        "`/history` — Last 10 entries\n"
        "`/today` — Today's session\n"
        "`/exercises` — All tracked exercises\n\n"
        "*Format:*\n"
        "Weights & reps: separate with commas or spaces\n"
        "Example: `80,85,90` or `80 85 90`",
        parse_mode="Markdown",
    )


# --- Quick /log (one-liner) ---
async def cmd_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return ConversationHandler.END

    args = ctx.args or []
    if not args:
        await update.message.reply_text("🏋️ What exercise did you do?")
        return ASK_EXERCISE

    exercise = args[0]
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: `/log bench 80,85,90 8,8,6 [notes]`",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    weights = parse_numbers(args[1])

    # Check if arg[2] contains numbers (reps) or is part of notes
    reps = []
    notes_start = 2
    if len(args) >= 3 and parse_numbers(args[2]):
        reps = [int(r) for r in parse_numbers(args[2])]
        notes_start = 3
    notes = " ".join(args[notes_start:]) if len(args) > notes_start else ""

    if not weights:
        await update.message.reply_text(
            "⚠️ Couldn't read weights. Use: `80,85,90`", parse_mode="Markdown"
        )
        return ConversationHandler.END

    while len(reps) < len(weights):
        reps.append(0)

    entry = append_entry(exercise, weights, reps, notes)
    await update.message.reply_text(
        _format_entry_summary(entry), parse_mode="Markdown"
    )
    return ConversationHandler.END


# --- Interactive /log conversation ---
async def ask_exercise_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return ConversationHandler.END
    ctx.user_data["exercise"] = update.message.text.strip()
    await update.message.reply_text(
        f"💪 *{ctx.user_data['exercise'].title()}*\n\n"
        "What weights did you use? (kg, separated by commas)\n"
        "Example: `80, 85, 90`",
        parse_mode="Markdown",
    )
    return ASK_WEIGHTS


async def ask_weights_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    weights = parse_numbers(update.message.text)
    if not weights:
        await update.message.reply_text(
            "⚠️ Send numbers separated by commas, e.g. `80, 85, 90`",
            parse_mode="Markdown",
        )
        return ASK_WEIGHTS
    ctx.user_data["weights"] = weights
    await update.message.reply_text(
        f"Got {len(weights)} sets.\n\n"
        "How many reps per set? (same order)\n"
        "Example: `8, 8, 6`\n\n"
        "Or send `0` to skip reps.",
        parse_mode="Markdown",
    )
    return ASK_REPS


async def ask_reps_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "0":
        reps = [0] * len(ctx.user_data["weights"])
    else:
        reps = [int(r) for r in parse_numbers(text)]
    while len(reps) < len(ctx.user_data["weights"]):
        reps.append(0)
    ctx.user_data["reps"] = reps
    await update.message.reply_text(
        "📝 Any notes? (e.g. _felt strong_, _lower back tight_)\n\n"
        "Or send `-` to skip.",
        parse_mode="Markdown",
    )
    return ASK_NOTES


async def ask_notes_received(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    notes = update.message.text.strip()
    if notes == "-":
        notes = ""
    entry = append_entry(
        ctx.user_data["exercise"],
        ctx.user_data["weights"],
        ctx.user_data["reps"],
        notes,
    )
    await update.message.reply_text(
        _format_entry_summary(entry), parse_mode="Markdown"
    )
    ctx.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Cancelled. Send /log to start again.")
    return ConversationHandler.END


# --- View commands ---
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = get_recent_entries(10)
    if not entries:
        await update.message.reply_text("No entries yet. Start with /log!")
        return
    lines = ["📊 *Recent Entries*\n"]
    for r in entries:
        exercise = r[2] if len(r) > 2 else "?"
        weights = r[4] if len(r) > 4 else ""
        reps = r[5] if len(r) > 5 else ""
        date = r[0] if r else ""
        lines.append(f"*{date}* — {exercise}\n  W: {weights}  R: {reps}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = get_today_entries()
    if not entries:
        await update.message.reply_text("No entries today. Hit the gym! 💪")
        return
    lines = ["🗓 *Today's Session*\n"]
    total_volume = 0
    for r in entries:
        exercise = r[2] if len(r) > 2 else "?"
        weights = r[4] if len(r) > 4 else ""
        reps = r[5] if len(r) > 5 else ""
        volume = float(r[7]) if len(r) > 7 and r[7] else 0
        total_volume += volume
        time_str = r[1] if len(r) > 1 else ""
        notes = r[8] if len(r) > 8 and r[8] else ""
        line = f"*{time_str}* — {exercise}\n  W: {weights}  R: {reps}"
        if notes:
            line += f"\n  📝 {notes}"
        lines.append(line)
    lines.append(f"\n📊 *Total volume today: {total_volume:g} kg*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_exercises(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    exercises = get_exercises()
    if not exercises:
        await update.message.reply_text("No exercises tracked yet.")
        return
    listing = "\n".join(f"• {e}" for e in exercises)
    await update.message.reply_text(
        f"🏋️ *Tracked Exercises*\n\n{listing}", parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN environment variable.")
        raise SystemExit(1)
    if not SHEET_ID:
        print("ERROR: Set GOOGLE_SHEET_ID environment variable.")
        raise SystemExit(1)

    get_sheet()
    logger.info("Google Sheets connected. Bot starting…")

    app = ApplicationBuilder().token(TOKEN).build()

    log_conv = ConversationHandler(
        entry_points=[CommandHandler("log", cmd_log)],
        states={
            ASK_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_exercise_received)],
            ASK_WEIGHTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_weights_received)],
            ASK_REPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_reps_received)],
            ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_notes_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(log_conv)
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("exercises", cmd_exercises))

    logger.info("Bot polling…")
    app.run_polling()


if __name__ == "__main__":
    main()
