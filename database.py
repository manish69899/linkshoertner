import sqlite3
import threading

DB_NAME = "files.db"
db_lock = threading.Lock()

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Files Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unique_code TEXT UNIQUE,
                file_id TEXT,
                file_type TEXT,
                caption TEXT,
                file_name TEXT,
                views INTEGER DEFAULT 0
            )
        ''')
        
        # Join Requests Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS join_requests (
                user_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (user_id, channel_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database Initialized Successfully.")

# --- FILE FUNCTIONS ---
def save_file(unique_code, file_id, file_type, caption, file_name):
    with db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO files (unique_code, file_id, file_type, caption, file_name) VALUES (?, ?, ?, ?, ?)",
                (unique_code, file_id, file_type, caption, file_name)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"DB Error: {e}")
            return False

def get_file_data(unique_code):
    with db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # View badhao
            cursor.execute("UPDATE files SET views = views + 1 WHERE unique_code = ?", (unique_code,))
            conn.commit()
            
            # Data laao
            cursor.execute("SELECT file_id, file_type, caption, file_name, views FROM files WHERE unique_code = ?", (unique_code,))
            data = cursor.fetchone()
            conn.close()
            
            if data:
                return {
                    'file_id': data[0],
                    'file_type': data[1],
                    'caption': data[2],
                    'file_name': data[3],
                    'views': data[4]
                }
            return None
        except:
            return None

def update_caption(unique_code, new_caption):
    with db_lock:
        try:
            conn = get_connection()
            conn.execute("UPDATE files SET caption = ? WHERE unique_code = ?", (new_caption, unique_code))
            conn.commit()
            conn.close()
            return True
        except: return False

# --- LIST & DELETE LOGIC ---

def get_files_by_page(page, per_page=10):
    """Admin List ke liye data lata hai"""
    with db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Total files count karo
            cursor.execute("SELECT COUNT(*) FROM files")
            total = cursor.fetchone()[0]
            
            # Pagination Logic
            offset = (page - 1) * per_page
            cursor.execute("SELECT unique_code, file_name, views, file_type FROM files ORDER BY id DESC LIMIT ? OFFSET ?", (per_page, offset))
            files = cursor.fetchall()
            conn.close()
            
            result = []
            for f in files:
                result.append({
                    'unique_code': f[0],
                    'file_name': f[1],
                    'views': f[2],
                    'file_type': f[3]
                })
            return result, total
        except Exception as e:
            print(f"List Fetch Error: {e}")
            return [], 0

def delete_file(unique_code):
    """File delete karta hai"""
    with db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE unique_code = ?", (unique_code,))
            conn.commit()
            conn.close()
            return True
        except:
            return False

# --- JOIN REQUEST FUNCTIONS ---

def add_join_request(user_id, channel_id):
    with db_lock:
        try:
            conn = get_connection()
            conn.execute("INSERT OR IGNORE INTO join_requests (user_id, channel_id) VALUES (?, ?)", (user_id, channel_id))
            conn.commit()
            conn.close()
        except: pass

def is_user_pending(user_id, channel_id):
    with db_lock:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM join_requests WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except: return False

# --- BACKUP HELPERS ---
def get_db_path():
    """Returns the path of the database file"""
    return DB_NAME