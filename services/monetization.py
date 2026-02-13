import json
import os
import requests
from telebot import types 

# --- CONFIGURATION ---
STATE_FILE = "services/rotation_state.json"

# --- SHORTENER APIs LIST (Rotation Logic) ---
# Maine aapki API Keys yahan set kar di hain screenshots ke hisaab se.
# {} ki jagah code automatically link bhar dega.
SHORTENER_APIS = [
    # 1. LinkShortify (Aapka API Key)
    "https://linkshortify.com/api?api=991f089abf70e628b906b8ed26ee96e5d4313f6b&url={}",
    
    # 2. GPLinks (Aapka API Key)
    "https://api.gplinks.com/api?api=d5014fa5a54f36579179453b3e791797aac5d483&url={}",
    
    # 3. IndianShortner (Aapka API Key)
    "https://indianshortner.com/api?api=3e4311d5582adc8253079214940703d9a809035d&url={}"
]

# --- STATE MANAGEMENT (User rotation yaad rakhne ke liye) ---
def get_state():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_state(data):
    # Ensure directory exists
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f: json.dump(data, f)
    except: pass

# --- CORE FUNCTION: GENERATE LINK ---
def get_smart_link(user_id, long_url):
    """
    Link ko Shortener API se convert karta hai.
    """
    # Agar API list khali hai, to original link de do
    if not SHORTENER_APIS:
        return long_url

    state = get_state()
    user_key = str(user_id)
    
    # Step 1: User ka current index nikalo (Default 0)
    current_index = state.get(user_key, 0)
    
    # Safety check
    if current_index >= len(SHORTENER_APIS):
        current_index = 0
        
    # Step 2: API URL Template Select karo
    api_url_template = SHORTENER_APIS[current_index]
    
    # Step 3: Link Shorten karo (Real Network Request)
    try:
        # URL format karo (Original link {} ki jagah jayega)
        request_url = api_url_template.format(long_url)
        
        # Request bhejo
        response = requests.get(request_url, timeout=10) # 10 sec timeout
        data = response.json()
        
        # --- RESPONSE HANDLING (Aapke Screenshot ke hisaab se) ---
        final_link = None
        
        # LinkShortify & Others return 'shortenedUrl' or 'link'
        if 'shortenedUrl' in data: 
            final_link = data['shortenedUrl']
        elif 'link' in data: 
            final_link = data['link']
        elif 'url' in data:
            final_link = data['url']
        
        if not final_link:
            # Agar JSON me link nahi mila to error raise karo
            print(f"⚠️ API Response Error: {data}")
            raise Exception("No link found in response")
            
    except Exception as e:
        print(f"⚠️ Shortener Error (Service {current_index + 1}): {e}")
        # Agar shortener fail hua, to Original Link hi de do taaki user phase na
        return long_url

    # Step 4: Next time ke liye Index Rotate karo (0 -> 1 -> 2 -> 0)
    next_index = (current_index + 1) % len(SHORTENER_APIS)
    state[user_key] = next_index
    save_state(state)
    
    return final_link

# --- MAIN HANDLER FUNCTION (Ye Function Missing Tha) ---
def handle_delivery(bot, chat_id, file_data):
    """
    Master Function: Decides Direct vs Ad-Link.
    Called by main.py and callbacks.py
    """
    file_id = file_data['file_id']
    f_type = file_data['file_type']
    caption = file_data['caption']
    f_name = file_data['file_name'] or "File"
    
    # Design Caption
    if caption:
        caption_text = f"<blockquote>💬 {caption}</blockquote>"
    else:
        caption_text = "<blockquote>ℹ️ <i>No description available.</i></blockquote>"

    final_caption = (
        f"📂 <b>{f_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{caption_text}\n"
        f"🔐 <b>Secured by ARYAN</b>"
    )

    # --- CASE 1: FILES (Direct Delivery - No Ads) ---
    if f_type in ['photo', 'video', 'document', 'audio']:
        markup = types.InlineKeyboardMarkup()
        # Add Share Button
        markup.add(types.InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url=https://t.me/{bot.get_me().username}"))
        
        try:
            if f_type == 'photo':
                bot.send_photo(chat_id, file_id, caption=final_caption, parse_mode='HTML', reply_markup=markup)
            elif f_type == 'video':
                bot.send_video(chat_id, file_id, caption=final_caption, parse_mode='HTML', reply_markup=markup)
            elif f_type == 'document':
                bot.send_document(chat_id, file_id, caption=final_caption, parse_mode='HTML', reply_markup=markup)
            elif f_type == 'audio':
                bot.send_audio(chat_id, file_id, caption=final_caption, parse_mode='HTML', reply_markup=markup)
        except Exception as e:
            print(f"File Send Error: {e}")
            bot.send_message(chat_id, "❌ Error sending file.")
        return

    # --- CASE 2: LINKS (Ad-Link Logic) ---
    if f_type == 'url':
        # Yahan upar wala 'get_smart_link' function call hoga
        short_link = get_smart_link(chat_id, file_id)
        
        text = (
            f"🔗 <b>Link Generated!</b>\n\n"
            f"📂 <b>Title:</b> {f_name}\n"
            f"👇 <b>Click to Open:</b>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 Open Link", url=short_link))
        
        bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)