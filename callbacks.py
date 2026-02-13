import time
from telebot import types
import config
import database
from utils import fsub

# Agar aapne monetization service banayi hai to uncomment karein
# from services import monetization 

def register_callbacks(bot):
    """
    Registers all callback query handlers to the bot.
    """
    @bot.callback_query_handler(func=lambda call: call.data == 'contribute')
    def callback_contribute(call):
        try:
            # 1. Loading Stop
            bot.answer_callback_query(call.id)
            
            # 2. Image & Text
            CONTRIBUTE_IMG = "https://i.ibb.co/mrG6cLX0/happy-young-employees-giving-support-help-each-other-179970-676.jpg" 
            
            # ⚠️ Yahan apna Username daalna mat bhoolna
            SUBMISSION_LINK = "https://t.me/coolegepyqbot" 
            
            text = (
                f"🤝 <b>Community Contribution</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"📚 <b>Gyan Baantne Se Badhta Hai!</b>\n\n"
                f"Agar aapke paas koi bhi useful <b>Study Material</b> hai, to please share karein.\n\n"
                f"📤 <b>Kaise Bhejein?</b>\n"
                f"Niche button par click karke aap direct Admin ko file bhej sakte hain."
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📤 Send Materials Here", url=SUBMISSION_LINK))
            
            # Back Button (Optional)
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="home")) 
            
            # Purana message delete karke naya bhejo
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
                
            bot.send_photo(call.message.chat.id, CONTRIBUTE_IMG, caption=text, parse_mode="HTML", reply_markup=markup)
            
        except Exception as e:
            print(f"Contribute Callback Error: {e}")


    # --- 1. LIST NAVIGATION (Next/Prev) ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('list_'))
    def handle_list_callbacks(call):
        if call.from_user.id != config.ADMIN_ID:
            bot.answer_callback_query(call.id, "Admin Only!")
            return

        action = call.data.split('_')[1] # prev, next, close
        
        if action == "close":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return

        # Current Page nikalo (Error handling ke saath)
        try:
            current_page = int(call.data.split('_')[2])
        except:
            current_page = 1
        
        if action == "prev":
            new_page = max(1, current_page - 1) # Page 0 par na jaye
        elif action == "next":
            new_page = current_page + 1
        else:
            return

        # Naya page load karo
        # Hum message ID pass kar rahe hain taaki naya message na bheje, balki edit kare
        send_file_list(bot, call.message.chat.id, new_page, call.message.message_id)
        bot.answer_callback_query(call.id)


    # --- 2. DELETE BUTTON (Inside List) ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
    def handle_delete_callback(call):
        if call.from_user.id != config.ADMIN_ID:
            bot.answer_callback_query(call.id, "Access Denied!")
            return
        
        code = call.data.split('_')[1]
        
        # Database se delete karo
        if database.delete_file(code):
            bot.answer_callback_query(call.id, "✅ File Deleted Successfully!")
            
            # Agar ye list view ke andar se delete kiya gaya hai
            if call.message.text and "File Manager" in call.message.text:
                # Page refresh karo (Wahi page reload karo)
                # Page number nikalne ki koshish (Regex ya split se)
                try:
                    # Text format: "File Manager (Page 1/5)"
                    page_str = call.message.text.split('Page ')[1].split('/')[0]
                    current_page = int(page_str)
                except:
                    current_page = 1
                
                send_file_list(bot, call.message.chat.id, current_page, call.message.message_id)
            else:
                # Agar ye single file message tha (/start wala result)
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
        else:
            bot.answer_callback_query(call.id, "❌ Error: File not found or DB error.")


    # --- 3. JOIN CHECK BUTTON ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
    def handle_fsub_check(call):
        try:
            user_id = call.from_user.id
            code = call.data.split('_')[1] 

            # Check Membership (Multi-channel support)
            if (hasattr(config, 'FSUB_CHANNELS') and config.FSUB_CHANNELS) or \
               (hasattr(config, 'FSUB_CHANNEL_ID') and config.FSUB_CHANNEL_ID):
                is_member = fsub.check_subscription(bot, user_id)
            else:
                is_member = True

            if is_member:
                try: bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                # Instant Delivery
                deliver_file_internal(bot, call.message.chat.id, code)
            else:
                bot.answer_callback_query(call.id, "❌ You haven't joined yet!", show_alert=True)
        except Exception as e:
            print(f"Check Error: {e}")

    # --- 4. ADMIN STATS (FIXED DASHBOARD) ---
    @bot.callback_query_handler(func=lambda call: call.data == "stats")
    def handle_stats(call):
        if call.from_user.id != config.ADMIN_ID:
            bot.answer_callback_query(call.id, "Admin Only!")
            return
        
        try:
            # Database se stats nikalo
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(views) FROM files")
            stats = cursor.fetchone()
            conn.close()
            
            total_files = stats[0] if stats[0] else 0
            total_views = stats[1] if stats[1] else 0
            
            # New Caption Design
            text = (
                f"👑 <b>Admin Dashboard</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 <b>Total Files:</b> <code>{total_files}</code>\n"
                f"👁️ <b>Total Views:</b> <code>{total_views}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"<i>Real-time Database Statistics</i>"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats"))
            
            # Alert (Popup) bhi dikhao
            bot.answer_callback_query(call.id, "✅ Stats Updated!")
            
            # Message Update karo (Agar caption hai to caption, nahi to text)
            try:
                bot.edit_message_caption(caption=text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
            except:
                # Agar previous message me caption nahi tha (e.g. text message), to edit_text try karo
                try:
                    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
                except: pass
                
        except Exception as e:
            print(f"Stats Error: {e}")
            bot.answer_callback_query(call.id, "Error fetching stats!")


# --- SHARED FUNCTIONS ---

def send_file_list(bot, chat_id, page, msg_id=None):
    """
    Ye function Database se files fetch karke list banata hai.
    Intelligent Pagination ke sath.
    """
    per_page = 10 # Ek page par 10 files
    files, total_files = database.get_files_by_page(page, per_page)
    
    # Agar ye page khali hai (e.g. user ne saari files delete kar di), to pichle page par jao
    if not files and page > 1:
        send_file_list(bot, chat_id, page - 1, msg_id)
        return

    # Agar DB khali hai
    if not files and page == 1:
        text = "📂 <b>File Manager</b>\n━━━━━━━━━━━━━━━━━━\n❌ <b>Database Empty!</b>\nNo files found."
        try:
            if msg_id:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML")
            else:
                bot.send_message(chat_id, text, parse_mode="HTML")
        except: pass
        return

    # Total Pages Calculate karo
    total_pages = (total_files + per_page - 1) // per_page
    
    # --- Message Body ---
    text = f"🗄️ <b>File Manager</b> (Page {page}/{total_pages})\n"
    text += f"📊 <b>Total Files:</b> {total_files}\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n"

    for f in files:
        name = f['file_name'] if f['file_name'] else "Unknown"
        # Name ko short karo taaki list gandi na dikhe
        if len(name) > 30: name = name[:30] + "..."
        
        text += (
            f"📂 <b>{name}</b>\n"
            f"🆔 <code>{f['unique_code']}</code> | 👀 {f['views']}\n"
            f"🗑 <b>Delete:</b> /delete_{f['unique_code']}\n\n"
        )
    
    text += "━━━━━━━━━━━━━━━━━━"

    # --- Navigation Buttons ---
    markup = types.InlineKeyboardMarkup()
    row = []
    
    if page > 1:
        row.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"list_prev_{page}"))
    
    row.append(types.InlineKeyboardButton("❌ Close", callback_data="list_close"))
    
    if page < total_pages:
        row.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"list_next_{page}"))
    
    markup.add(*row)

    # --- Send/Edit Logic ---
    try:
        if msg_id:
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"List Send Error: {e}")
        # Agar edit fail ho (e.g. content same hai), to ignore karo


def deliver_file_internal(bot, chat_id, unique_code):
    """
    Callback delivery logic (Instant Fetch - No Wait)
    """
    try:
        # 1. Instant Fetching Message
        msg = bot.send_message(chat_id, "⚡ <b>Fetching...</b>", parse_mode="HTML")
        
        # 2. Get Data
        data = database.get_file_data(unique_code)
        
        if not data:
            bot.edit_message_text("❌ <b>Link Invalid or Deleted.</b>", chat_id, msg.message_id, parse_mode="HTML")
            return

        # Data Unpack
        file_id = data['file_id']
        file_type = data['file_type']
        caption = data['caption']
        file_name = data['file_name'] or "File"
        
        if caption: caption = f"<blockquote>💬 {caption}</blockquote>"
        else: caption = "<blockquote>ℹ️ <i>No description.</i></blockquote>"
        
        final_cap = (
            f"📂 <b>{file_name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👁️ Views: {data['views']+1}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{caption}\n"
            f"🔐 <b>Secured by ARYAN</b>"
        )
        
        # Buttons
        markup = types.InlineKeyboardMarkup()
        url = f"https://t.me/{config.BOT_USERNAME}?start={unique_code}"
        markup.add(types.InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={url}"))
        
        if hasattr(config, 'FSUB_INVITE_LINK') and config.FSUB_INVITE_LINK:
            markup.add(types.InlineKeyboardButton("📢 Join Channel", url=config.FSUB_INVITE_LINK))
        elif hasattr(config, 'FSUB_CHANNELS') and config.FSUB_CHANNELS:
            markup.add(types.InlineKeyboardButton("📢 Join Channel", url=config.FSUB_CHANNELS[0]['link']))

        # 3. Clean up Loading Msg
        try: bot.delete_message(chat_id, msg.message_id)
        except: pass

        # 4. Send File (Direct or via Monetization)
        # Note: Agar aapne services/monetization banaya hai, to niche wali line uncomment karein
        # from services import monetization
        # monetization.handle_delivery(bot, chat_id, data)
        
        # Fallback (Direct Send) - Agar monetization off hai
        if file_type == 'photo': bot.send_photo(chat_id, file_id, caption=final_cap, parse_mode="HTML", reply_markup=markup)
        elif file_type == 'video': bot.send_video(chat_id, file_id, caption=final_cap, parse_mode="HTML", reply_markup=markup)
        elif file_type == 'document': bot.send_document(chat_id, file_id, caption=final_cap, parse_mode="HTML", reply_markup=markup)
        elif file_type == 'url': bot.send_message(chat_id, f"🔗 <b>Link:</b>\n{file_id}", parse_mode="HTML", reply_markup=markup)
            
    except Exception as e:
        print(f"Deliver Error: {e}")

