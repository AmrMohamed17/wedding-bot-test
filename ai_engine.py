import os
import streamlit as st
import google.generativeai as genai
from datetime import datetime
from database import check_availability, add_booking, get_info, get_full_knowledge_base

# --- CONFIGURATION ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_HARDCODED_KEY")

genai.configure(api_key=API_KEY)

# --- GLOBAL MEMORY ---
active_sessions = {}

# --- TOOLS ---
def tool_check_availability(date_str: str, time_slot: str):
    return check_availability(date_str, time_slot)

# UPDATED TOOL: Handles validation return codes
def tool_book_date(date_str: str, time_slot: str, name: str, phone: str, package_name: str, total_price: str, details_summary: str):
    
    result = add_booking(date_str, time_slot, name, phone, package_name, total_price, details_summary)
    
    if result == "SUCCESS":
        deposit_key = f"Deposit_{time_slot}" 
        amount = get_info(deposit_key)
        return f"SUCCESS: Booking recorded. Total Deal: {total_price} EGP. Deposit Required: {amount} EGP within 48 hours."
    elif result == "PAST_DATE_ERROR":
        return "ERROR: Cannot book a date in the past or today. Please ask user for a future date."
    else:
        return "Booking Failed. System Error."

def tool_get_general_info(key: str):
    return get_info(key)

tools = [tool_check_availability, tool_book_date, tool_get_general_info]

# --- MAIN FUNCTION ---
def get_bot_response(user_message, user_phone):
    global active_sessions
    
    today = datetime.now().strftime("%Y-%m-%d")
    knowledge_base = get_full_knowledge_base()
    
    # --- UPDATED PERSONA ---
    nour_instruction = f"""
    You are 'Nour', the Sales Assistant for 'Pictures Hall' (قاعة بيكتشرز) in Mansoura.
    Current Date: {today}.
    
    📚 KNOWLEDGE BASE:
    {knowledge_base}
    
    🛑 STRICT RULES (DO NOT BREAK):
    
    1. **UNKNOWN INFO:** 
       - If user asks about something NOT in the Knowledge Base, DO NOT GUESS.
       - Say: "For this specific detail, please contact the administration directly: {get_info('Admin_Phone')}".
       
    2. **CAPACITY LIMIT:** 
       - Max capacity is **400 Guests**.
       - If > 400, say: "Our hall capacity is 400. For larger numbers, please contact the administration."
       
    3. **DATE VALIDATION:**
       - **Future Dates Only:** You CANNOT book today or past dates. If user asks for {today} or before, refuse politely.
       
    4. **DATA VALIDATION:**
       - **Name:** Full Name (3 parts).
       - **Phone:** Valid Egypt format (01xxxxxxxxx).
       
    5. **BOOKING & PRICING:**
       - Calculate **Total Price** (Package + Extras).
       - Create a **Details Summary**.
       - Use `tool_book_date` with all fields.
       
    6. **TONE:** Professional, Egyptian Arabic, Polite. No "Habiby".
    """

    if user_phone not in active_sessions:
        try:
            model = genai.GenerativeModel(
                model_name='models/gemini-2.5-flash', # Keeping your preferred model
                tools=tools,
                system_instruction=nour_instruction
            )
            active_sessions[user_phone] = model.start_chat(enable_automatic_function_calling=True)
        except Exception as e:
            print(f"Error: {e}")
            return "عذرًا، حدث خطأ أثناء تشغيل النظام."
    
    chat_session = active_sessions[user_phone]
    try:
        response = chat_session.send_message(user_message)
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        del active_sessions[user_phone]
        return "عذرًا، حدث خطأ تقني. يرجى المحاولة مرة أخرى."