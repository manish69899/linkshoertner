import re

# --- CONFIGURATION ---
# Common Video, Audio, Document Extensions
VIDEO_EXT = r"mkv|mp4|avi|mov|flv|wmv|webm|m4v"
AUDIO_EXT = r"mp3|flac|wav|m4a|aac|ogg"
DOC_EXT   = r"pdf|zip|rar|7z|apk|exe|iso|txt|docx|xlsx|epub|ppt|pptx"
IMAGE_EXT = r"jpg|jpeg|png|webp|heic|bmp"  # <--- YE ADD KIYA HAI

# Sabko jod kar ek bada pattern
ALL_EXTS = f"{VIDEO_EXT}|{AUDIO_EXT}|{DOC_EXT}"

def parse_forwarded_message(text):
    """
    Universal Parser (Upgraded):
    1. Handles Telegram Deep Links (t.me/bot?start=...)
    2. Handles Multi-line formats (Name on one line, Value on next).
    3. Cleans HTML tags like <code>, <b>, and quotes.
    4. Auto-detects 'File Name:' labels.
    """
    results = []
    if not text: return []

    # --- STRATEGY 1: STRUCTURED REPORTS (Smart Multi-line Parser) ---
    # Ye logic messages ko line-by-line padhta hai aur context yaad rakhta hai.
    
    lines = text.split('\n')
    current_name = None
    expecting_name_next_line = False # Flag to track if name is on next line
    
    # Regex to identify Labels (e.g. "File Name:", "📂 Name")
    name_label_pattern = re.compile(fr"(?:File Name|Name|Title|📂|📁|📄|📝)\s*[:\-]?\s*(.*)", re.IGNORECASE)
    
    # Regex to identify Links (e.g. "Link:", "🔗")
    link_label_pattern = re.compile(r"(?:File Link|Shareable Link|Link|URL|🔗|✅|👉)\s*[:\-]?\s*(\(?https?://\S+)", re.IGNORECASE)
    
    # Regex for ANY raw URL (Backup)
    raw_url_pattern = re.compile(r"(https?://\S+)")

    for line in lines:
        original_line = line.strip()
        if not original_line: continue

        # --- CLEANING STEP ---
        # HTML tags aur quotes hatao taaki regex confuse na ho
        # e.g. "<code>'Movie.mkv'</code>" -> "Movie.mkv"
        clean_text = re.sub(r'<[^>]+>', '', original_line) # Remove <b>, <code>, etc.
        clean_text = clean_text.strip().strip("'").strip('"') # Remove quotes ' "

        # 1. CHECK IF WE ARE WAITING FOR A NAME (Multi-line Case)
        if expecting_name_next_line:
            if clean_text: # Agar line khali nahi hai
                current_name = clean_text
                expecting_name_next_line = False # Reset flag
                continue
            else:
                # Agar khali line hai to skip karo, flag abhi bhi True rahega
                continue

        # 2. CHECK FOR FILE NAME LABEL
        name_match = name_label_pattern.search(clean_text)
        if name_match:
            potential_value = name_match.group(1).strip()
            
            # Agar Label ke saath hi naam likha hai (Single Line)
            if len(potential_value) > 2:
                current_name = potential_value
            else:
                # Agar Label akela hai (e.g. "📂 File Name:"), to naam agli line pe hoga
                expecting_name_next_line = True
            continue 

        # 3. CHECK FOR LINK
        # Pehle Label wala link dhundo (Strong Match)
        link_match = link_label_pattern.search(clean_text)
        
        # Agar Label nahi mila, to Raw URL dhundo (Weak Match)
        if not link_match:
            raw_link_match = raw_url_pattern.search(clean_text)
            if raw_link_match and current_name:
                link_match = raw_link_match

        # Agar Link mil gaya
        if link_match:
            url = link_match.group(1).strip()
            # Bracket fix
            if url.endswith(')'): url = url[:-1]
            
            # Agar humare paas 'current_name' hai, to result banao
            if current_name:
                results.append({'name': current_name, 'link': url})
                current_name = None # Reset for next file
                continue
            
    # Agar Strategy 1 se results mil gaye, to return karo
    if results:
        # Duplicate removal logic
        unique_results = []
        seen_links = set()
        for res in results:
            if res['link'] not in seen_links:
                unique_results.append(res)
                seen_links.add(res['link'])
        return unique_results


    # --- STRATEGY 2: UNSTRUCTURED TEXT / FORWARDED POSTS (BACKUP) ---
    # Agar upar wala fail hua (format match nahi kiya), to ye backup chalega.
    
    # 1. Find Valid Links
    link_pattern = r'(https?://\S+)'
    found_links = re.findall(link_pattern, text)

    if not found_links: return []

    # 2. Find Names (Emoji or Extension based)
    name_pattern_emoji = fr"(?:📂|📁|📄)\s*(.*?\.({ALL_EXTS}))"
    name_pattern_simple = fr"(?:\s|^)(.*?\.({ALL_EXTS}))(?:\s|$)"

    raw_names = re.findall(name_pattern_emoji, text, re.IGNORECASE)
    if not raw_names:
        raw_names = re.findall(name_pattern_simple, text, re.IGNORECASE)

    clean_names = []
    for item in raw_names:
        if isinstance(item, tuple): name = item[0]
        else: name = item
        # Basic cleanup
        name = re.sub(r'<[^>]+>', '', name).strip("'").strip('"').strip()
        if len(name) > 2 and 'http' not in name:
            clean_names.append(name)

    # 3. Pairing Logic
    count = min(len(found_links), len(clean_names))
    for i in range(count):
        results.append({
            'name': clean_names[i],
            'link': found_links[i]
        })
    
    # Leftover Links (Name generate karo)
    if len(found_links) > len(clean_names):
        for i in range(len(clean_names), len(found_links)):
            link = found_links[i]
            if '@' in link: continue 
            
            results.append({
                'name': get_clean_filename_from_link(link),
                'link': link
            })

    return results

def get_clean_filename_from_link(link):
    """
    Smart Name Generator for Unknown Links
    """
    try:
        # Case A: Telegram Start Link
        if 'start=' in link:
            return f"Secured_File_{link.split('start=')[-1][:5]}"
        
        # Case B: Direct URL
        name_part = link.split('/')[-1]
        name_part = re.sub(r'[^\w\-\.]', '_', name_part) # Special chars hatao
        if len(name_part) > 20: name_part = name_part[:20]
        
        return f"File_{name_part}"
    except:
        return "Secured_File"