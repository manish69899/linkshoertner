import os
import json

# --- SECURE CONFIGURATION ---

# 1. BOT TOKEN
# Render Environment Variable: BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 2. ADMIN ID
# Render Environment Variable: ADMIN_ID
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
except:
    print("⚠️ Admin ID not set correctly in Env Vars")
    ADMIN_ID = 0

# 3. BOT USERNAME
# Render Environment Variable: BOT_USERNAME
BOT_USERNAME = os.getenv("BOT_USERNAME")

# 4. FORCE SUBSCRIBE CHANNELS
# Render Environment Variable: FSUB_CHANNELS
# Hum wahan poora List JSON format mein daalenge
fsub_config = os.getenv("FSUB_CHANNELS")

if fsub_config:
    try:
        FSUB_CHANNELS = json.loads(fsub_config)
    except Exception as e:
        print(f"⚠️ JSON Config Error: {e}")
        FSUB_CHANNELS = []
else:
    FSUB_CHANNELS = []

# --- BACKWARD COMPATIBILITY (Old code support) ---
FSUB_CHANNEL_ID = None
FSUB_INVITE_LINK = None