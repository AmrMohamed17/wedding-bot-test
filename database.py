import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import streamlit as st
import json

# --- CONFIGURATION ---
SHEET_NAME = "Wedding_Hall_Database"
CACHE_TIMEOUT_MINUTES = 5

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

# --- CONNECT FUNCTION (CLOUD COMPATIBLE) ---
def connect_db():
    global client, sh
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    creds = None
    
    # 1. Try Cloud Secrets First (Wrapped in try-except to prevent crash)
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except (FileNotFoundError, KeyError):
        pass # Just ignore and fall back to local file
    
    # 2. If Cloud Secrets didn't work, try Local File
    if creds is None:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        except Exception as e:
            st.error(f"❌ Could not find credentials.json or Streamlit Secrets. Error: {e}")
            return None

    client = gspread.authorize(creds)
    sh = client.open(SHEET_NAME)
    return sh

# --- SMART REFRESH FUNCTION ---
def refresh_cache_if_needed():
    global db_cache, sh
    now = datetime.now()
    
    if (db_cache["last_updated"] is None) or \
       (now - db_cache["last_updated"] > timedelta(minutes=CACHE_TIMEOUT_MINUTES)):
        
        try:
            if sh is None: connect_db()
            
            db_cache["packages"] = sh.worksheet("Packages").get_all_records()
            db_cache["buffet"] = sh.worksheet("Buffet_Options").get_all_records()
            db_cache["extras"] = sh.worksheet("Extras").get_all_records()
            
            raw_info = sh.worksheet("General_Info").get_all_records()
            db_cache["info"] = {row['Key']: row['Value'] for row in raw_info}
            
            db_cache["last_updated"] = now
            
        except Exception as e:
            print(f"❌ Error refreshing DB: {e}")

# --- GETTERS ---
def get_full_knowledge_base():
    refresh_cache_if_needed()
    try:
        info_text = "--- 🏢 GENERAL INFO ---\n"
        for k, v in db_cache["info"].items():
            info_text += f"- {k}: {v}\n"
            
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
    except Exception as e:
        return f"Error: {e}"

def get_info(key):
    refresh_cache_if_needed()
    return db_cache["info"].get(key, "Not Found")

def check_availability(date_str, time_slot):
    if sh is None: connect_db()
    worksheet = sh.worksheet("Bookings")
    records = worksheet.get_all_records()
    for row in records:
        if str(row['Date']) == str(date_str) and row['Time_Slot'].lower() == time_slot.lower():
            if row['Status'] in ['Booked', 'Pending']:
                return "Booked"
    return "Available"

def add_booking(date, time_slot, name, phone, package_name, notes=""):
    try:
        if sh is None: connect_db()
        worksheet = sh.worksheet("Bookings")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([date, time_slot, "Pending", name, phone, package_name, notes, timestamp])
        return True
    except Exception as e:
        print(f"Error adding booking: {e}")
        return False