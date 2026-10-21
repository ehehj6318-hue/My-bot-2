# bot.py — Final Render HACK (Auto-Install Chromium + Flask)
import os
import re
import asyncio
import logging
import threading
import subprocess
import sys
from pathlib import Path
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes,
)
from playwright.async_api import async_playwright

# =================== CONFIG ===================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_NEW_TOKEN_HERE")
ALLOWED_USER_IDS = [8964939517]
# ==============================================

ALLOWED = set(ALLOWED_USER_IDS)
OUT_DIR = Path("./downloads")
OUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aadhaar-bot")

ASK_NUMBER, SOLVE_CAPTCHA, ASK_OTP = range(3)
SESSIONS = {}

# --- Dummy Flask Server (Render Port Fix) ---
web_app = Flask(__name__)
@web_app.route('/')
def health():
    return "Bot is running live!"
# --------------------------------------------

def allowed(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id in ALLOWED

async def guard(update: Update) -> bool:
    if not allowed(update):
        await update.effective_message.reply_text("Ye private bot hai. Access nahi hai.")
        return True
    return False

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await guard(update): return ConversationHandler.END
    await update.message.reply_text(
        "Chalo apna Aadhaar download karte hain.\n\n"
        "Step 1: Apna 12-digit Aadhaar number ya 10-digit Mobile number bhej.\n"
        "Cancel: /cancel"
    )
    return ASK_NUMBER

async def got_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await guard(update): return ConversationHandler.END
    num = update.message.text.strip().replace(" ", "")
    
    if not num.isdigit():
        await update.message.reply_text("Sirf digits bhej. Dobara:")
        return ASK_NUMBER
        
    if len(num) == 10:
        input_type = "mobile"
    elif len(num) == 12:
        input_type = "aadhaar"
    else:
        await update.message.reply_text("10-digit mobile ya 12-digit Aadhaar bhej. Dobara:")
        return ASK_NUMBER

    SESSIONS[update.effective_user.id] = {"query": num, "type": input_type}
    
    await update.message.reply_text("Browser khol raha hoon. Screenshot bhejunga, captcha solve karke batao.")
    asyncio.create_task(open_browser(update.effective_user.id, ctx))
    return SOLVE_CAPTCHA

async def open_browser(user_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    sess = SESSIONS[user_id]
    try:
        p_ctx = await async_playwright().start()
        
        # Cloud flags
        browser = await p_ctx.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        await page.goto("https://myaadhaar.uidai.gov.in", timeout=60000)
        await asyncio.sleep(3)

        if sess["type"] == "mobile":
            try: await page.get_by_role("link", name=re.compile("Mobile", re.I)).first.click(timeout=5000)
            except: pass
            for sel in ['input[id*="mobile" i]', 'input[name*="mobile" i]']:
                try: await page.fill(sel, sess["query"]); break
                except: continue
        else:
            try: await page.get_by_role("link", name=re.compile("Aadhaar Number", re.I)).first.click(timeout=5000)
            except: pass
            for sel in ['input[id*="aadhaar" i]', 'input[name*="aadhaar" i]']:
                try: await page.fill(sel, sess["query"]); break
                except: continue

        await asyncio.sleep(2)
        ss_path = OUT_DIR / f"captcha_{user_id}.png"
        await page.screenshot(path=str(ss_path))

        sess.update(page=page, browser=browser, p_ctx=p_ctx, ready=True)

        await ctx.bot.send_photo(
            chat_id=user_id,
            photo=open(ss_path, "rb"),
            caption="**Due to spammers, captcha verification required.**\n\nYe captcha solve karke yahan bhej."
        )
    except Exception as e:
        log.exception("Browser launch fail")
        sess["ready"] = False
        await ctx.bot.send_message(user_id, f"Browser launch fail: {e}")

async def solve_captcha(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await guard(update): return ConversationHandler.END
    captcha_text = update.message.text.strip()
    sess = SESSIONS.get(update.effective_user.id)

    if not sess or not sess.get("ready"):
        await update.message.reply_text("Browser ready nahi. /start se dobara.")
        return ConversationHandler.END

    try:
        page = sess["page"]
        for sel in ['input[id*="captcha" i]', 'input[name*="captcha" i]']:
            try: await page.fill(sel, captcha_text); break
            except: continue

        for name in ["Send OTP", "Get OTP", "Request OTP"]:
            try:
                await page.get_by_role("button", name=re.compile(name, re.I)).first.click(timeout=3000)
                break
            except: continue

        await update.message.reply_text("OTP phone pe aaya hoga. 6-digit OTP bhej.")
        return ASK_OTP
    except Exception as e:
        log.exception("captcha fill fail")
        await update.message.reply_text(f"Kuch toot gaya: {e}")
        return ConversationHandler.END

async def got_otp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await guard(update): return ConversationHandler.END
    otp = update.message.text.strip()
    if not (otp.isdigit() and len(otp) == 6):
        await update.message.reply_text("6-digit OTP chahiye. Dobara:")
        return ASK_OTP

    sess = SESSIONS.get(update.effective_user.id)
    page = sess.get("page") if sess else None
    if not page:
        await update.message.reply_text("Session gaya. /start se dobara.")
        return ConversationHandler.END

    try:
        for sel in ['input[id*="otp" i]', 'input[name*="otp" i]']:
            try: await page.fill(sel, otp); break
            except: continue

        for name in ["Verify", "Submit", "Verify OTP"]:
            try:
                await page.get_by_role("button", name=re.compile(name, re.I)).first.click(timeout=3000)
                break
            except: continue

        try:
            async with page.expect_download(timeout=120000) as dl:
                for name in ["Download", "Download Aadhaar"]:
                    try:
                        await page.get_by_role("button", name=re.compile(name, re.I)).first.click(timeout=3000)
                        break
                    except: continue
            d = await dl.value
            out = OUT_DIR / f"aadhaar_{update.effective_user.id}.pdf"
            await d.save_as(out)
            await update.message.reply_document(
                document=open(out, "rb"),
                filename="aadhaar.pdf",
                caption="Le tera eAadhaar. Password: area PIN ya jo tune set kiya tha.",
            )
        except Exception:
            await update.message.reply_text("Download button khud browser mein click kar.")
    except Exception as e:
        log.exception("otp flow fail")
        await update.message.reply_text(f"Kuch toot gaya: {e}")
    finally:
        try:
            if sess.get("browser"): await sess["browser"].close()
            if sess.get("p_ctx"): await sess["p_ctx"].stop()
        except: pass
        SESSIONS.pop(update.effective_user.id, None)

    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sess = SESSIONS.get(update.effective_user.id)
    if sess:
        try:
            if sess.get("browser"): await sess["browser"].close()
            if sess.get("p_ctx"): await sess["p_ctx"].stop()
        except: pass
        SESSIONS.pop(update.effective_user.id, None)
    await update.message.reply_text("Cancelled. /start se dobara.")
    return ConversationHandler.END

def main():
    # 1. Start Flask server FIRST (Render ko port dikhane ke liye)
    def run_server():
        port = int(os.environ.get("PORT", 10000))
        web_app.run(host="0.0.0.0", port=port)
    
    threading.Thread(target=run_server, daemon=True).start()
    log.info("Flask dummy server started. Port is open.")

    # 2. MAGIC HACK: Khud hi Chromium install karo
    try:
        log.info("Checking Playwright browser installation...")
        # Check if playwright command exists and install chromium
        result = subprocess.run(["playwright", "install", "chromium"], capture_output=True, text=True)
        if result.returncode == 0:
            log.info("Playwright Chromium successfully verified/installed!")
        else:
            log.error(f"Playwright install failed: {result.stderr}")
    except Exception as e:
        log.error(f"Could not run playwright install: {e}")

    # 3. Start Telegram Bot
    bot_app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_number)],
            SOLVE_CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, solve_captcha)],
            ASK_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    bot_app.add_handler(conv)
    log.info("Bot is now polling Telegram!")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
