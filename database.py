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
    except Exception:
        return "Error loading data."

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

# --- UPDATED BOOKING FUNCTION ---
def add_booking(date, time_slot, name, phone, package_name, total_price, details):
    """
    Saves booking with separate Price and Details columns.
    Checks if date is in the future.
    """
    try:
        if sh is None: connect_db()
        
        # 1. DATE VALIDATION (No past bookings)
        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
        today_date = datetime.now().date()
        
        if booking_date <= today_date:
            print(f"❌ Attempted to book past/today date: {date}")
            return "PAST_DATE_ERROR"

        # 2. ADD ROW TO SHEET
        worksheet = sh.worksheet("Bookings")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # New Column Order: 
        # Date | Time | Status | Name | Phone | Package | Total_Price | Details | Timestamp
        row_data = [
            date, 
            time_slot, 
            "Pending", 
            name, 
            phone, 
            package_name, 
            total_price, 
            details, 
            timestamp
        ]
        
        worksheet.append_row(row_data)
        return "SUCCESS"
        
    except Exception as e:
        print(f"Error adding booking: {e}")
        return "SYSTEM_ERROR"