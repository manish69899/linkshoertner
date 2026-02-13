from dotenv import load_dotenv
load_dotenv()

import telebot
from telebot import types, apihelper
import config
import database
import random
import string
import time
import sys
import os
import re
import zipfile
import glob
# --- IMPORT KEEP ALIVE ---
from keep_alive import keep_alive
# --- IPv4 CONNECTION FIX (Network Hanging Solve) ---
import requests.packages.urllib3.util.connection as urllib3_cn
import socket
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family
# ---------------------------------------------------

# --- IMPORT UTILS ---
# Ensure utils folder is accessible
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
from utils import text_parser
from utils import fsub

# --- IMPORT SERVICES (NEW) ---
# Ye zaroori hai Ads aur Direct File logic ke liye
from services import monetization

# --- IMPORT CALLBACKS ---
import callbacks

# --- 1. SETUP ---
# Connection settings
apihelper.CONNECT_TIMEOUT = 30
apihelper.READ_TIMEOUT = 30

bot = telebot.TeleBot(config.BOT_TOKEN, threaded=True, num_threads=10)
database.init_db()

# --- REGISTER CALLBACKS ---
callbacks.register_callbacks(bot)

# --- 2. ASSETS ---
START_IMG = "https://i.ibb.co/WvvBJPLq/24180262-f124-43ef-996c-d917372978f2.jpg" 

# --- 3. UTILS & HELPERS ---

def generate_code():
    """Generates a unique 6-character code."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# Safe Send Function (Anti-Flood Engine)
def safe_send(chat_id, text, **kwargs):
    """
    Sends messages safely. If Telegram says 'Too Many Requests', 
    it waits and retries automatically.
    """
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 429:
            retry_time = e.result_json['parameters']['retry_after']
            time.sleep(retry_time)
            return safe_send(chat_id, text, **kwargs)
        else:
            print(f"Error sending message: {e}")

# Helper Function: Single File Save & Reply
def process_save(message, file_id, file_type, file_name, caption, is_silent=False):
    """
    Saves a single file to DB and sends a confirmation message.
    """
    code = generate_code()
    
    # Save to Database
    if database.save_file(code, file_id, file_type, caption, file_name):
        short_link = f"https://t.me/{config.BOT_USERNAME}?start={code}"
        
        # If not silent, send the Premium Success Message
        if not is_silent:
            success_text = (
                f"🎉 <b>File Secured Successfully!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📂 <b>File Name:</b>\n"
                f"<code>{file_name}</code>\n\n"
                f"🆔 <b>File Code:</b> <code>{code}</code>\n"
                f"📦 <b>Type:</b> {file_type.upper()}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔗 <b>Shareable Link:</b>\n"
                f"<code>{short_link}</code>"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={short_link}"))
            markup.add(types.InlineKeyboardButton("🗑 Delete", callback_data=f"del_{code}"))
            
            safe_send(message.chat.id, success_text, parse_mode="HTML", reply_markup=markup)
            
        return True, short_link, code
    return False, None, None


# --- HELPER: FILE DELIVERY SYSTEM (INSTANT + MONETIZED) ---
def deliver_file(chat_id, unique_code):
    """
    Code leta hai, aur Monetization Service ko pass karta hai.
    """
    # 1. Loading msg (Instant acknowledgment)
    try:
        loading_msg = bot.send_message(chat_id, "⚡ <b>Fetching Secure File...</b>", parse_mode="HTML")
    except:
        return # Agar user ne block kiya hai

    # 2. Database Fetch
    data = database.get_file_data(unique_code)

    if not data:
        if loading_msg:
            bot.edit_message_text("❌ <b>Link Invalid or Deleted.</b>", chat_id, loading_msg.message_id, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "❌ <b>Link Invalid or Deleted.</b>", parse_mode="HTML")
        return

    # 3. Clean up Loading Msg
    try:
        bot.delete_message(chat_id, loading_msg.message_id)
    except: pass

    # 4. HANDOVER TO MONETIZATION SERVICE
    # Ye service decide karegi ki File bhejni hai (Direct) ya Link (Ads)
    monetization.handle_delivery(bot, chat_id, data)


# --- 4. HANDLERS ---
# --- DONATE HANDLER (QR Code & UPI) ---
@bot.message_handler(commands=['donate'])
def handle_donate(message):
    try:
        # Yahan apna QR Code Image URL lagayein (Imgur link best hai)
        # Ya fir local file path bhi de sakte hain
        QR_IMAGE_URL = "https://i.ibb.co/rKrSGRTn/Acc.png" 
        
        upi_id = "cyloc@ibl" # Aapki UPI ID
        
        caption_text = (
            f"🙏 <b>Support Development!</b>\n\n"
            f"Agar aapko ye bot pasand aaya, to donate kar sakte hain.\n\n"
            f"🆔 <b>UPI ID:</b> <code>{upi_id}</code>\n"
            f"Scan QR to pay."
        )
        
        # QR Code Bhejo
        bot.send_photo(message.chat.id, QR_IMAGE_URL, caption=caption_text, parse_mode="HTML")
        
    except Exception as e:
        bot.reply_to(message, f"Donate Info: {upi_id}")


@bot.message_handler(commands=['backup'])
def handle_backup(message):
    if message.from_user.id != config.ADMIN_ID: return
    
    msg = bot.send_message(message.chat.id, "📦 <b>Creating full backup...</b>", parse_mode="HTML")
    
    zip_filename = f"backup_{int(time.time())}.zip"
    
    try:
        # Zip file banao
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # 1. Main Folder ki saari .db files dhoondo
            for db_file in glob.glob("*.db"):
                zipf.write(db_file)
                print(f"Added to backup: {db_file}")

            # 2. Services Folder ki saari .json files dhoondo (Limits/Rotation data)
            for json_file in glob.glob("services/*.json"):
                zipf.write(json_file)
                print(f"Added to backup: {json_file}")
                
        # Send Zip File
        if os.path.exists(zip_filename):
            with open(zip_filename, 'rb') as f:
                caption_text = (
                    f"🗃 <b>Full System Backup</b>\n"
                    f"📅 <b>Date:</b> {time.strftime('%d %b %Y')}\n"
                    f"📂 <b>Contains:</b> All Databases & User States\n\n"
                    f"♻️ <i>Reply with /restore to load this data.</i>"
                )
                bot.send_document(
                    message.chat.id, 
                    f, 
                    caption=caption_text, 
                    parse_mode='HTML'
                )
            # Send karne ke baad local zip delete kar do (Space bachane ke liye)
            os.remove(zip_filename)
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text("❌ Error: Could not create backup file.", message.chat.id, msg.message_id)

    except Exception as e:
        bot.reply_to(message, f"❌ Backup Failed: {e}")
        if os.path.exists(zip_filename): os.remove(zip_filename)


# --- SMART RESTORE COMMAND (Unzip & Overwrite) ---
@bot.message_handler(commands=['restore'])
def handle_restore_command(message):
    if message.from_user.id != config.ADMIN_ID: return
    
    # Check agar reply kiya hai kisi document par
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "⚠️ <b>How to Restore:</b>\n\n1. Upload or locate your <code>backup.zip</code> file.\n2. Reply to it with <code>/restore</code>.", parse_mode='HTML')
        return

    # Check extension (sirf zip ya db allow karein)
    file_name = message.reply_to_message.document.file_name
    if not (file_name.endswith('.zip') or file_name.endswith('.db')):
        bot.reply_to(message, "❌ Please reply to a valid <b>.zip</b> or <b>.db</b> file.")
        return

    status_msg = bot.reply_to(message, "♻️ <b>Processing Restore...</b>", parse_mode="HTML")

    try:
        # File Download karo
        file_info = bot.get_file(message.reply_to_message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Agar ZIP file hai (Full Restore)
        if file_name.endswith('.zip'):
            with open("temp_restore.zip", 'wb') as f:
                f.write(downloaded_file)
            
            # Unzip & Overwrite
            with zipfile.ZipFile("temp_restore.zip", 'r') as zip_ref:
                zip_ref.extractall(".") # Current folder me extract karega
            
            os.remove("temp_restore.zip")
            result_text = "✅ <b>Full System Restored!</b>\nAll databases and json files updated."

        # Agar sirf DB file hai (Single DB Restore - Purana method support)
        elif file_name.endswith('.db'):
            # Default DB name maan ke save kar rahe hain
            db_path = database.get_db_path() # files.db
            with open(db_path, 'wb') as f:
                f.write(downloaded_file)
            result_text = "✅ <b>Database File Restored!</b>"

        # Database Connection Refresh karo
        database.init_db()
        
        bot.edit_message_text(result_text, message.chat.id, status_msg.message_id, parse_mode="HTML")

    except Exception as e:
        bot.edit_message_text(f"❌ <b>Restore Failed:</b>\n<code>{e}</code>", message.chat.id, status_msg.message_id, parse_mode="HTML")


# --- ADMIN FILE LIST (PAGINATION) ---
@bot.message_handler(commands=['list', 'files'])
def handle_file_list(message):
    if message.from_user.id != config.ADMIN_ID:
        return
    try:
        # callbacks.py se list function call karo
        callbacks.send_file_list(bot, message.chat.id, 1)
    except Exception as e:
        print(f"List Error: {e}")
        bot.send_message(message.chat.id, "❌ Error loading list. Check logs.")

# --- DELETE COMMAND HANDLER ---
@bot.message_handler(regexp=r"^/delete_")
def handle_delete_link(message):
    if message.from_user.id != config.ADMIN_ID: return
    try:
        code = message.text.split('_')[1]
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE unique_code = ?", (code,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🗑 <b>File Deleted:</b> <code>{code}</code>", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "❌ Error deleting file.")

# --- CHAT JOIN REQUEST HANDLER ---
@bot.chat_join_request_handler()
def handle_join_request(message):
    """
    Jab user Invite Link se 'Request to Join' dabata hai.
    """
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        # Database me save karo
        if hasattr(database, 'add_join_request'):
            database.add_join_request(user_id, chat_id)
    except Exception as e:
        print(f"Join Request Error: {e}")

# --- ASSETS (Images Define Karein) ---
# Normal Welcome Image
#START_IMG = "https://i.ibb.co/Q3wGX148/1770870669463.png" 

# Access Denied / Force Sub Image
FORCE_IMG = "https://i.ibb.co/3yWGj0zr/IMG-20260213-022316-116.jpg"


# --- UPDATED START HANDLER ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        user_id = message.from_user.id
        text = message.text.split()
        
        # --- SCENARIO 1: User ne Link par Click kiya hai ---
        if len(text) > 1:
            unique_code = text[1]
            
            # --- FSUB CHECK START ---
            
            # 1. Check Multi-Channel Config
            if hasattr(config, 'FSUB_CHANNELS') and config.FSUB_CHANNELS:
                is_member = fsub.check_subscription(bot, user_id)
                
                if not is_member:

                    denied_text = (

                        "⚠️ <b>ᴘʟᴇᴀsᴇ ғᴏʟʟᴏᴡ ᴛʜɪs ʀᴜʟᴇs</b> ⚠️\n\n"
                        "ɪɴ ᴏʀᴅᴇʀ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ꜰɪʟᴇ/ᴍᴏᴠɪᴇ ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ ʏᴏᴜ.\n\n"
                        "👉 <b>ʏᴏᴜ ᴡɪʟʟ ʜᴀᴠᴇ ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ.</b>\n\n"
                        "ᴀғᴛᴇʀ ᴛʜᴀᴛ, ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ 'Try Again' ʙᴜᴛᴛᴏɴ.\n\n"
                        "✅ <i>I'll send you the file privately instantly!</i>"
                        )

                    markup = fsub.get_fsub_buttons(unique_code)
                    
                    # Yahan send_message ko send_photo me badal diya
                    bot.send_photo(message.chat.id, FORCE_IMG, caption=denied_text, parse_mode="HTML", reply_markup=markup)
                    return 
            
            # 2. Check Single Channel Config (Fallback)
            elif hasattr(config, 'FSUB_CHANNEL_ID') and config.FSUB_CHANNEL_ID:
                is_member = fsub.check_subscription(bot, user_id) 

                if not is_member:
                    denied_text = (
                        "🔒 <b>Access Denied!</b>\n\n"
                        "⚠️ You must join our channel to access this file."
                    )
                    markup = fsub.get_fsub_buttons(unique_code)
                    
                    # Yahan bhi send_photo laga diya
                    bot.send_photo(message.chat.id, FORCE_IMG, caption=denied_text, parse_mode="HTML", reply_markup=markup)
                    return 
            # --- FSUB CHECK END ---

            # Agar member hai, to file deliver karo
            deliver_file(message.chat.id, unique_code)

        # --- SCENARIO 2: Normal Welcome Message ---
        else:
            welcome_text = (
                f"👋 <b>Welcome {message.from_user.first_name}!</b>\n\n"
            )
# --- START MENU BUTTONS ---

# 👇 YE WALI LINE ADD KAREIN 👇
            markup.add(types.InlineKeyboardButton("📚 Share Material", callback_data="contribute")) 
            if user_id == config.ADMIN_ID:

                markup.add(types.InlineKeyboardButton("👑 Admin Dashboard", callback_data="stats"))           
            # Yahan Welcome Image Bhej rahe hain
            bot.send_photo(message.chat.id, START_IMG, caption=welcome_text, parse_mode="HTML", reply_markup=markup)

    except Exception as e:
        print(f"Start Error: {e}")
# --- HELP HANDLER ---
@bot.message_handler(commands=['help'])
def handle_help(message):
    try:
        text = (
            "❓ <b>Help & Guide</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "• Files are stored permanently.\n"
            "• Join our channel to access files without issues.\n\n"
            "👨‍💻 <b>Contact Admin/Any issue:</b> @coolegepyqbot"  # Yahan apna username daal dena
        )
        
        # Buttons
        markup = types.InlineKeyboardMarkup()
        # Agar config me channel link hai to button add karo
        if hasattr(config, 'FSUB_INVITE_LINK') and config.FSUB_INVITE_LINK:
            markup.add(types.InlineKeyboardButton("📢 Updates Channel", url=config.FSUB_INVITE_LINK))
        
        # Image ke sath bhejo (Professional Look)
        bot.send_photo(
            message.chat.id, 
            START_IMG,  # Ye wahi image hai jo start me use hoti hai
            caption=text, 
            parse_mode='HTML', 
            reply_markup=markup
        )
        
    except Exception as e:
        # Agar Image fail ho jaye to simple text bhejo
        bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

# --- MAIN UPLOAD HANDLER ---
@bot.message_handler(content_types=['text', 'document', 'photo', 'video', 'audio'])
def handle_content(message):
    
    if message.from_user.id != config.ADMIN_ID:
        return

    try:
        # --- A. MEDIA HANDLER ---
        if message.content_type == 'photo':
            f_id = message.photo[-1].file_id
            process_save(message, f_id, 'photo', "Image.jpg", message.caption)
            
        elif message.content_type == 'video':
            f_id = message.video.file_id
            name = message.video.file_name or "Video.mp4"
            process_save(message, f_id, 'video', name, message.caption)
            
        elif message.content_type == 'document':
            f_id = message.document.file_id
            name = message.document.file_name or "Document"
            process_save(message, f_id, 'document', name, message.caption)
            
        elif message.content_type == 'audio':
            f_id = message.audio.file_id
            name = message.audio.file_name or "Audio.mp3"
            process_save(message, f_id, 'document', name, message.caption)

        # --- B. SMART TEXT HANDLER ---
        elif message.content_type == 'text':
            raw_text = message.text
            status_msg = safe_send(message.chat.id, "⚙️ <b>Scanning text for links...</b>", parse_mode="HTML")

            parsed_items = text_parser.parse_forwarded_message(raw_text)

            if parsed_items and len(parsed_items) > 0:
                report_text = f"✅ <b>Smart Scan Completed</b>\n🔍 Found {len(parsed_items)} files.\n━━━━━━━━━━━━━━━━━━\n\n"
                
                count = 0
                for item in parsed_items:
                    name = item['name']
                    link = item['link']
                    success, short_link, code = process_save(message, link, 'url', name, "", is_silent=True)
                    
                    if success:
                        count += 1
                        report_text += (
                            f"📂 <b>{name}</b>\n"
                            f"🔗 <code>{short_link}</code>\n\n"
                        )
                
                report_text += "━━━━━━━━━━━━━━━━━━\n<i>⚡ Generated by Smart Parser</i>"
                bot.delete_message(message.chat.id, status_msg.message_id)
                safe_send(message.chat.id, report_text, parse_mode="HTML")

            else:
                single_link = re.search(r'(https?://\S+)', raw_text)
                if single_link:
                    bot.delete_message(message.chat.id, status_msg.message_id)
                    link = single_link.group(1)
                    process_save(message, link, 'url', "Shared Link", "")
                else:
                    bot.edit_message_text("❌ <b>No valid links found.</b>", message.chat.id, status_msg.message_id, parse_mode="HTML")

    except Exception as e:
        print(f"Handler Error: {e}")

# --- UPDATE CAPTION COMMAND ---

# --- CONTRIBUTE COMMAND ---
@bot.message_handler(commands=['contribute'])
def handle_contribution(message):
    # 1. Image URL (Community/Help Theme)
    CONTRIBUTE_IMG = "https://i.ibb.co/mrG6cLX0/happy-young-employees-giving-support-help-each-other-179970-676.jpg" 
    
    # 2. Aapka Contact Link (Jahan log file bhejenge)
    # ⚠️ Yahan apna Username (e.g., https://t.me/Aryan_Admin) jarur dalein
    SUBMISSION_LINK = "https://t.me/coolegepyqbot" 
    
    # 3. Caption Text
    text = (
        f"🤝 <b>Community Contribution</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📚 <b>Gyan Baantne Se Badhta Hai!</b>\n\n"
        f"Agar aapke paas koi bhi useful <b>Study Material, Notes, PYQs</b> ya <b>Books</b> hain, to please humare saath share karein.\n\n"
        f"🌟 <b>Kyun Share Karein?</b>\n"
        f"Aapka ek chhota sa contribution kisi <b>Junior</b> ya <b>Dost</b> ka pura semester bacha sakta hai. Aayiye mil kar sabki madad karein!\n\n"
        f"📤 <b>Kaise Bhejein?</b>\n"
        f"Niche button par click karke aap direct Admin ko file bhej sakte hain."
    )
    
    # 4. Button
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 Send Materials Here", url=SUBMISSION_LINK))
    
    # 5. Send Message
    try:
        bot.send_photo(message.chat.id, CONTRIBUTE_IMG, caption=text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)


@bot.message_handler(commands=['edit'])
def handle_edit_command(message):
    if message.from_user.id != config.ADMIN_ID: return
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ Usage: <code>/edit [code] [New Caption]</code>", parse_mode="HTML")
            return
        code, new_caption = parts[1], parts[2]
        if database.update_caption(code, new_caption):
            bot.reply_to(message, "✅ <b>Caption Updated!</b>", parse_mode="HTML")
        else:
            bot.reply_to(message, "❌ Invalid Code.", parse_mode="HTML")
    except: pass



# --- SET MENU COMMANDS (Start hone se pehle) ---
def set_default_commands():
    try:
        bot.set_my_commands([
            types.BotCommand("start", "🚀 Start Bot"),
            types.BotCommand("donate", "💸 Donate & Support"), # Ye add ho gaya
            types.BotCommand("help", "ℹ️ Help & Contact"),
            types.BotCommand("backup","☁️ Backup (Admin Only)" ),
            types.BotCommand("restore","♻️ Restore (Admin Only)")
            
        ])
        print("✅ Menu Commands Set Successfully.")
    except Exception as e:
        print(f"⚠️ Menu Error: {e}")

# Run setup
set_default_commands()

print("🔥 Bot Live: Safety On...")

# Render Server Start
keep_alive()

if __name__ == "__main__":
    try:
        # Loop hataya taaki KeyboardInterrupt sahi se catch ho
        bot.infinity_polling(timeout=90, long_polling_timeout=60, skip_pending=True)
    except KeyboardInterrupt:
        print("\n❌ Bot Stopped by User (Good Bye!)")
        sys.exit()
    except Exception as e:
        print(f"⚠️ Error: {e}")