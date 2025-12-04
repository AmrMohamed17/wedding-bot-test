import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import streamlit as st

# --- CONFIGURATION ---
SHEET_NAME = "Wedding_Hall_Database"
CACHE_TIMEOUT_MINUTES = 1 # Reduced to 1 min for faster testing

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

# --- HELPER: NORMALIZE DATE ---
def parse_sheet_date(date_val):
    """
    Tries to understand the date. Prioritizes ISO (2026-04-10).
    """
    date_str = str(date_val).strip()
    formats = [
        "%Y-%m-%d",  # 2026-04-10 (Standard)
        "%d/%m/%Y",  # 10/04/2026 (Egypt)
        "%m/%d/%Y",  # 04/10/2026 (US)
        "%Y/%m/%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

# --- GETTERS ---
def get_full_knowledge_base():
    refresh_cache_if_needed()
    try:
        info_text = "--- 🏢 GENERAL INFO ---\n"
        for k, v in db_cache["info"].items():
            # Auto-Fix Phone Number in the Knowledge Base
            val = str(v)
            if k == "Admin_Phone" and val.isdigit() and len(val) == 10:
                val = "0" + val
            info_text += f"- {k}: {val}\n"
        
        pkg_text = "\n--- 📦 PACKAGES (BAQAT) ---\n"
        for p in db_cache["packages"]:
            pkg_text += f"• ID: {p['Package_ID']} | Name: {p['Name_Arabic']} | Season: {p['Season']} | Guests: {p['Guests']} | Price: {p['Price']} | Details: {p['Details']}\n"
        
        buffet_text = "\n--- 🍽️ BUFFET OPTIONS ---\n"
        for b in db_cache["buffet"]:
            buffet_text += f"• For Package {b['Package_ID']}: {b['Level_Name']} = {b['Price']} ({b['Items']})\n"
        
        extras_text = "\n--- ➕ EXTRAS ---\n"
        for e in db_cache["extras"]:
            extras_text += f"• {e['Item_Name']} ({e['Category']}): {e['Price']}\n"
            
        return info_text + pkg_text + buffet_text + extras_text
    except Exception:
        return "Error loading data."

def get_info(key):
    refresh_cache_if_needed()
    val = db_cache["info"].get(key, "Not Found")
    
    # AUTO-FIX: If phone number is missing the leading zero, add it back.
    if key == "Admin_Phone" and str(val).isdigit() and len(str(val)) == 10:
        return "0" + str(val)
        
    return val

def check_availability(target_date_str, time_slot):
    """
    Checks if a slot is blocked in the sheet.
    """
    try:
        # 1. Parse the AI's requested date
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        
        # 2. Check if it's in the past
        today_date = datetime.now().date()
        if target_date < today_date:
            return "PAST_DATE"

        # 3. Connect and Read Sheet
        if sh is None: connect_db()
        worksheet = sh.worksheet("Bookings")
        
        # Force get values as Displayed Strings (fixes some format issues)
        records = worksheet.get_all_records(value_render_option='FORMATTED_VALUE')
        
        print(f"🔎 CHECKING: {target_date} ({time_slot})") # Debug Log
        
        for row in records:
            sheet_date_obj = parse_sheet_date(row['Date'])
            
            # Debug Logic
            if sheet_date_obj:
                print(f"   -> Comparing with Sheet: {sheet_date_obj} ({row['Time_Slot']})")
                
                if sheet_date_obj == target_date and row['Time_Slot'].lower() == time_slot.lower():
                    print("   -> MATCH FOUND! BLOCKED.")
                    return "Booked"
                
        return "Available"
        
    except ValueError:
        return "INVALID_DATE_FORMAT"
    except Exception as e:
        print(f"Error: {e}")
        return "Available"