from telebot import types
import config
import database

def check_subscription(bot, user_id):
    """
    Checks if user is a member of ALL target channels.
    Supports Third-Party Channels (Promotion Mode).
    """
    
    # 1. Target Channels ki List nikalo
    targets = []
    
    # Priority: Multi-Channel List (Promotion ke liye ye best hai)
    if hasattr(config, 'FSUB_CHANNELS') and config.FSUB_CHANNELS:
        targets = config.FSUB_CHANNELS
    elif hasattr(config, 'FSUB_CHANNEL_ID') and config.FSUB_CHANNEL_ID:
        link = getattr(config, 'FSUB_INVITE_LINK', 'https://t.me/')
        targets = [{'id': config.FSUB_CHANNEL_ID, 'link': link}]
    
    # Agar koi channel set nahi hai, to jane do
    if not targets:
        return True

    # 2. Har Channel ko Check karo
    for channel in targets:
        chat_id = channel.get('id')
        
        # --- CHECK A: Kya User ne Request bheji hai? (Private Channel Support) ---
        if database.is_user_pending(user_id, chat_id):
            continue # Request pending hai, matlab user ne try kiya hai. Allow karo.

        # --- CHECK B: Kya User asli Member hai? ---
        try:
            member = bot.get_chat_member(chat_id, user_id)
            
            # Agar Member, Admin ya Creator hai -> PASS
            if member.status in ['member', 'administrator', 'creator']:
                continue 
            
            # Agar Left, Kicked, Restricted hai -> FAIL
            return False 
            
        except Exception as e:
            # --- ERROR HANDLING (Agar Bot Admin nahi hai) ---
            error_msg = str(e)
            
            if "chat not found" in error_msg.lower() or "bot was kicked" in error_msg.lower():
                print(f"⚠️ PROMOTION ERROR: Bot channel {chat_id} me ADMIN nahi hai!")
                print("👉 Client ko bolo Bot ko Admin banaye.")
            else:
                print(f"⚠️ Check Error for {chat_id}: {e}")
            
            # Kyunki hum check nahi kar paye, hum user ko 'Not Joined' maanege
            # Taaki wo Client ke channel pe jaye aur join kare
            return False

    # Agar loop pura chal gaya aur sab sahi hai
    return True

def get_fsub_buttons(unique_code):
    """
    Promotional Buttons generate karega.
    """
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    targets = []
    if hasattr(config, 'FSUB_CHANNELS') and config.FSUB_CHANNELS:
        targets = config.FSUB_CHANNELS
    elif hasattr(config, 'FSUB_CHANNEL_ID') and config.FSUB_CHANNEL_ID:
        link = getattr(config, 'FSUB_INVITE_LINK', 'https://t.me/')
        targets = [{'id': config.FSUB_CHANNEL_ID, 'link': link}]

    # Har Client ke channel ka button add karo
    for i, channel in enumerate(targets, 1):
        # Button Text: "📢 Join Channel 1", "📢 Join Sponsor Channel" etc.
        btn_text = f"📢 Join Channel {i}" 
        markup.add(types.InlineKeyboardButton(btn_text, url=channel.get('link')))
    
    # Try Again Button
    markup.add(types.InlineKeyboardButton("🔄 Try Again / Verify", callback_data=f"check_{unique_code}"))
    
    return markup