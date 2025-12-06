import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import streamlit as st

# --- CONFIGURATION ---
SHEET_NAME = "Wedding_Hall_Database"
CACHE_TIMEOUT_MINUTES = 1

# --- GLOBAL VARIABLES ---
client = None
sh = None
db_cache = {
    "packages": [],
    "buffet": [],
    "extras": [],
    "info": {},
    "last_updated": None
}

# --- CONNECT FUNCTION ---
def connect_db():
    global client, sh
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = None
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except (FileNotFoundError, KeyError):
        pass 
    if creds is None:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        except Exception:
            return None
    client = gspread.authorize(creds)
    sh = client.open(SHEET_NAME)
    return sh

# --- SMART REFRESH ---
def refresh_cache_if_needed():
    global db_cache, sh
    now = datetime.now()
    if (db_cache["last_updated"] is None) or (now - db_cache["last_updated"] > timedelta(minutes=CACHE_TIMEOUT_MINUTES)):
        try:
            if sh is None: connect_db()
            db_cache["packages"] = sh.worksheet("Packages").get_all_records()
            db_cache["buffet"] = sh.worksheet("Buffet_Options").get_all_records()
            db_cache["extras"] = sh.worksheet("Extras").get_all_records()
            raw_info = sh.worksheet("General_Info").get_all_records()
            db_cache["info"] = {row['Key']: row['Value'] for row in raw_info}
            db_cache["last_updated"] = now
        except Exception as e:
            print(f"Error refreshing DB: {e}")

# --- HELPER: UNIVERSAL DATE PARSER ---
def parse_sheet_date(date_val):
    try:
        s = str(date_val).strip().replace('/', '-').replace('.', '-').replace('\\', '-')
        parts = s.split('-')
        if len(parts) != 3: return None
        y, m, d = 0, 0, 0
        if len(parts[0]) == 4: y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts[2]) == 4: d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        else: return None
        return datetime(y, m, d).date()
    except Exception: return None

# --- GETTERS ---
def get_full_knowledge_base():
    refresh_cache_if_needed()
    try:
        # 1. General Info
        info_text = "--- 🏢 GENERAL INFO ---\n"
        for k, v in db_cache["info"].items():
            val = str(v)
            if k == "Admin_Phone" and val.isdigit() and len(val) == 10:
                val = "0" + val
            info_text += f"- {k}: {val}\n"
        
        # 2. Packages (Verified Columns)
        pkg_text = "\n--- 📦 PACKAGES (BAQAT) ---\n"
        for p in db_cache["packages"]:
            # Use .get() to avoid crashing if column is missing
            pid = p.get('Package_ID', 'N/A')
            name = p.get('Name_Arabic', 'N/A')
            season = p.get('Season', 'N/A')
            guests = p.get('Guests', 'N/A')
            price = p.get('Price', 'N/A')
            details = p.get('Details', 'N/A')
            tier = p.get('Display_Tier', 'Primary') # Default to Primary if missing
            img = p.get('Image_URL', '')            # Default to empty if missing
            
            if str(img).strip() == "": 
                img = "None"
            
            pkg_text += f"• ID: {pid} | Name: {name} | Season: {season} | Guests: {guests} | Price: {price} | Tier: {tier} | Image: {img} | Details: {details}\n"
        
        # 3. Buffet
        buffet_text = "\n--- 🍽️ BUFFET OPTIONS ---\n"
        for b in db_cache["buffet"]:
            buffet_text += f"• For Package {b['Package_ID']}: {b['Level_Name']} = {b['Price']} ({b['Items']})\n"
        
        # 4. Extras
        extras_text = "\n--- ➕ EXTRAS ---\n"
        for e in db_cache["extras"]:
            extras_text += f"• {e['Item_Name']} ({e['Category']}): {e['Price']}\n"
            
        return info_text + pkg_text + buffet_text + extras_text
    except Exception as e:
        print(f"Error loading KB: {e}")
        return "Error loading data."

def get_info(key):
    refresh_cache_if_needed()
    val = db_cache["info"].get(key, "Not Found")
    if key == "Admin_Phone" and str(val).isdigit() and len(str(val)) == 10: return "0" + str(val)
    return val

def check_availability(target_date_str, time_slot):
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        if target_date < datetime.now().date(): return "PAST_DATE"
        
        if sh is None: connect_db()
        worksheet = sh.worksheet("Bookings")
        records = worksheet.get_all_records()
        
        for row in records:
            sheet_date = parse_sheet_date(row['Date'])
            if sheet_date:
                # Direct Match
                if sheet_date == target_date and row['Time_Slot'].lower() == time_slot.lower(): return "Booked"
        return "Available"
    except ValueError: return "INVALID_DATE_FORMAT"
    except Exception as e: return "Available"