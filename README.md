# HMT Watch Stock Bot 🕐

Alerts you whenever watches come in stock or restock on:
- **hmtwatches.in**
- **hmtwatches.store**

Also tracks 3 specific watches with priority alerts.

---

## How It Works

The bot scrapes both HMT sites every 15 minutes, compares against previous state, and fires alerts whenever something goes from "out of stock → in stock" or a new product appears.

---

## Option A — GitHub Actions (Recommended, 100% Free, No PC needed)

This runs in the cloud 24/7 for free. You get alerts via the **GitHub Actions log** (and optionally Telegram).

### Setup Steps

**1. Fork / create this repo on GitHub**
   - Go to [github.com](https://github.com) → New repository
   - Name it `hmt-stock-bot`, make it **private**
   - Upload all these files

**2. Enable GitHub Actions**
   - Go to your repo → Actions tab → click "I understand my workflows, go ahead"

**3. The workflow runs automatically every 15 minutes**
   - Go to Actions → "HMT Stock Checker" → see logs
   - Any in-stock alert will appear in the job output with 🔔 ALERT

**4. (Optional) Telegram notifications for real phone alerts**

   Create a Telegram bot:
   - Message `@BotFather` on Telegram → `/newbot` → copy the token
   - Message `@userinfobot` to get your chat ID

   Add secrets to GitHub:
   - Repo → Settings → Secrets and variables → Actions → New secret
   - Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
   - Uncomment the Telegram step in `.github/workflows/stock-checker.yml`

---

## Option B — Run Locally on Your PC

Get actual **desktop popup notifications** on Windows/Mac/Linux.

### Setup

```bash
# 1. Install Python 3.10+ if you haven't
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run once to test
python checker.py

# 4. Run in a loop (checks every 10 min, desktop popup on restock)
python run_local.py
```

### Make it start on boot (Windows)
1. Press `Win + R` → type `shell:startup` → Enter
2. Create a shortcut to: `pythonw run_local.py` pointing to this folder

### Make it start on boot (Mac)
Create a LaunchAgent plist in `~/Library/LaunchAgents/com.hmt.stockbot.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.hmt.stockbot</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/hmt-stock-bot/run_local.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>WorkingDirectory</key>
  <string>/path/to/hmt-stock-bot</string>
</dict>
</plist>
```
Then: `launchctl load ~/Library/LaunchAgents/com.hmt.stockbot.plist`

---

## Watched Products

| Watch | URL |
|-------|-----|
| HMT Watch #1 | https://www.hmtwatches.store/product/6297d606-55df-44a0-9d2c-7ed811bf8e27 |
| HMT Watch #2 | https://www.hmtwatches.store/product/2ab8780d-a5f3-4c87-8051-dfc691d1cb11 |
| HMT Watch #3 | https://www.hmtwatches.store/product/b8dd05e3-7936-4291-bcb4-1cea41b14cdf |

---

## File Structure

```
hmt-stock-bot/
├── checker.py              ← main scraper + alert logic
├── run_local.py            ← loop runner for local PC use
├── requirements.txt
├── stock_state.json        ← auto-generated, tracks previous state
└── .github/
    └── workflows/
        └── stock-checker.yml   ← GitHub Actions cron job
```

---

## Troubleshooting

- **No alerts appearing?** The site may use JavaScript rendering. If `checker.py` consistently shows `unknown` status, the site is JS-heavy. Solution: upgrade to `playwright` scraping (see below).
- **GitHub Actions not running?** Repos with no recent commits sometimes pause scheduled workflows. Just push any commit to re-activate.

### Upgrading to JS-rendered scraping (if needed)
```bash
pip install playwright
playwright install chromium
```
Then replace `fetch()` in `checker.py` with a Playwright headless browser call.
