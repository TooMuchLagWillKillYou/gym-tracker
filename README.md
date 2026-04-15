# 🏋️ Gym Weight Tracker — Telegram Bot

A Telegram bot that logs your gym lifts directly into a Google Sheet.
Fast to use between sets, and your data lives in your Google Drive.

---

## What It Looks Like

**In Telegram:**
```
You:  /log bench 80,85,90 8,8,6 felt strong
Bot:  ✅ Bench Press logged!
        Set 1: 80 kg × 8 reps
        Set 2: 85 kg × 8 reps
        Set 3: 90 kg × 6 reps
      🏆 Max: 90 kg
      📊 Volume: 1870 kg
      📅 2026-04-15 18:30
```

**In Google Sheets:**

| Date       | Time  | Exercise    | Sets | Weights (kg)  | Reps   | Max Weight | Total Volume | Notes       |
|------------|-------|-------------|------|---------------|--------|------------|--------------|-------------|
| 2026-04-15 | 18:30 | Bench Press | 3    | 80, 85, 90    | 8, 8, 6| 90         | 1870         | felt strong |

---

## Setup Guide

### Step 1: Create the Telegram Bot (2 min)

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. "My Gym Tracker") and username (e.g. `my_gym_tracker_bot`)
4. **Copy the API token** — you'll need it later

### Step 2: Set Up Google Sheets API (5 min)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g. "Gym Tracker")
3. Enable these APIs:
   - **Google Sheets API** → [Enable here](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
   - **Google Drive API** → [Enable here](https://console.cloud.google.com/apis/library/drive.googleapis.com)
4. Create a **Service Account**:
   - Go to **IAM & Admin → Service Accounts**
   - Click **Create Service Account**
   - Name it (e.g. "gym-bot")
   - Skip the optional permissions steps
   - Click **Done**
5. Create a key:
   - Click on your new service account
   - Go to the **Keys** tab
   - **Add Key → Create New Key → JSON**
   - Download the JSON file — this is your `credentials.json`
6. **Copy the service account email** (looks like `gym-bot@project-name.iam.gserviceaccount.com`)

### Step 3: Create and Share the Google Sheet (1 min)

1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet
2. Name it whatever you like (e.g. "Gym Log")
3. **Share it** with your service account email (from step 2.6) — give it **Editor** access
4. **Copy the Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_YOUR_SHEET_ID/edit
   ```

### Step 4: Get Your Telegram User ID (1 min)

This locks the bot so only you can use it:

1. Open Telegram, search for **@userinfobot**
2. Send it any message
3. It replies with your user ID (a number like `123456789`)

### Step 5: Deploy on Railway (free tier, 5 min)

1. Push the project files to a **GitHub repo**:
   ```
   gym-tracker-bot/
   ├── gym_tracker_bot.py
   ├── requirements.txt
   ├── Procfile
   └── README.md
   ```
   ⚠️ Do NOT commit `credentials.json` to GitHub!

2. Go to [railway.app](https://railway.app) and sign in with GitHub

3. Click **New Project → Deploy from GitHub Repo** and select your repo

4. Go to your project's **Variables** tab and add:

   | Variable                 | Value                                  |
   |--------------------------|----------------------------------------|
   | `TELEGRAM_BOT_TOKEN`     | Your token from Step 1                 |
   | `GOOGLE_SHEET_ID`        | Your sheet ID from Step 3              |
   | `GOOGLE_CREDENTIALS_JSON`| Paste the **entire contents** of your `credentials.json` file |
   | `ALLOWED_USER_ID`        | Your Telegram user ID from Step 4      |

5. Railway will auto-deploy. Check the logs to confirm the bot is running.

> **Note on Railway's free tier:** it gives you 500 hours/month of execution,
> which is enough for a lightweight bot like this. If you hit the limit, 
> [Render](https://render.com) and [Fly.io](https://fly.io) offer similar free tiers.

---

## Bot Commands

| Command                        | Description                          |
|--------------------------------|--------------------------------------|
| `/start`                       | Welcome message                      |
| `/log`                         | Guided step-by-step logging          |
| `/log bench 80,85,90 8,8,6`   | Quick log: exercise, weights, reps   |
| `/log bench 80,85,90 8,8,6 notes here` | Quick log with notes        |
| `/history`                     | Last 10 entries                      |
| `/today`                       | Today's session + total volume       |
| `/exercises`                   | All tracked exercises                |
| `/help`                        | Show commands                        |
| `/cancel`                      | Cancel guided logging                |

### Two Ways to Log

**Quick (one message):**
```
/log deadlift 120,130,140 5,5,3 grip gave out
```

**Guided (the bot asks each field):**
```
You:  /log
Bot:  🏋️ What exercise did you do?
You:  bench
Bot:  💪 Bench — What weights? (kg, commas)
You:  80, 85, 90
Bot:  Got 3 sets. How many reps?
You:  8, 8, 6
Bot:  📝 Any notes? (or - to skip)
You:  felt strong today
Bot:  ✅ Bench Press logged! ...
```

---

## Files in This Project

| File                  | What it does                                              |
|-----------------------|-----------------------------------------------------------|
| `gym_tracker_bot.py`  | The bot — all logic in one file                           |
| `requirements.txt`    | Python dependencies                                       |
| `Procfile`            | Tells Railway how to run the bot                          |
| `credentials.json`    | Your Google service account key (do NOT commit to GitHub) |

---

## Tips

- Weights are just numbers — use kg or lbs, just be consistent.
- **Total Volume** = sum of (weight × reps) per set. Great for tracking progressive overload.
- Up to 8 sets per exercise entry.
- The `/today` command shows your whole session at a glance with total volume.
- You can open your Google Sheet anytime to make charts, spot trends, etc.
