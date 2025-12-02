import os
import streamlit as st
import google.generativeai as genai
from datetime import datetime
from database import check_availability, add_booking, get_info, get_full_knowledge_base

# --- CONFIGURATION ---
API_KEY = st.secrets["GEMINI_API_KEY"]


genai.configure(api_key=API_KEY)

# --- GLOBAL MEMORY ---
active_sessions = {}

# --- TOOLS ---
def tool_check_availability(date_str: str, time_slot: str):
    return check_availability(date_str, time_slot)

# UPDATED TOOL: Accepts Price and Details
def tool_book_date(date_str: str, time_slot: str, name: str, phone: str, package_name: str, total_price: str, details_summary: str):
    success = add_booking(date_str, time_slot, name, phone, package_name, total_price, details_summary)
    if success:
        deposit_key = f"Deposit_{time_slot}" 
        amount = get_info(deposit_key)
        return f"SUCCESS: Booking recorded. Total Deal: {total_price}. Deposit Required: {amount} EGP within 48 hours."
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
    
    # --- THE UPDATED PERSONA WITH NEW RULES ---
    nour_instruction = f"""
    You are 'Nour', the Sales Assistant for 'Pictures Hall' (قاعة بيكتشرز) in Mansoura.
    Current Date: {today}.
    
    📚 KNOWLEDGE BASE:
    {knowledge_base}
    
    🛑 STRICT RULES (DO NOT BREAK):
    
    1. **UNKNOWN INFO:** 
       - If user asks about something NOT in the Knowledge Base (e.g., Hairdresser, Car Rental), DO NOT GUESS.
       - Say: "For this specific detail, please contact the administration directly: {get_info('Admin_Phone')}".
       
    2. **CAPACITY LIMIT:** 
       - Max capacity is **400 Guests**.
       - If user asks for > 400 (e.g., 500, 600), DO NOT proceed with booking.
       - Say: "Our hall capacity is 400. For larger numbers, please contact the administration: {get_info('Admin_Phone')}".
       
    3. **DATA VALIDATION (Before Booking):**
       - **Name:** Must be **Full Name (3 parts)** (e.g., Ahmed Mohamed Ali). If user sends "Ahmed", ask for full name.
       - **Phone:** Must be valid Egyptian format (11 digits, starts with 010, 011, 012, 015). If wrong, ask for correct number.
       
    4. **BOOKING PROCESS:**
       - Step A: Confirm Date, Time (Day/Night), and Package.
       - Step B: Ask for Extras (Buffet upgrades, Zaffa, Meals).
       - Step C: **CALCULATE TOTAL PRICE.** (Base Package + Extras).
       - Step D: Summarize the deal to the user: "Your booking: [Package] + [Extras]. Total Price: [X] EGP. Do you confirm?"
       - Step E: Only if they say "Yes/Confirm", use `tool_book_date`.
       
    5. **TONE:** Professional, Egyptian Arabic, Polite. No "Habiby".
    """

    if user_phone not in active_sessions:
        try:
            model = genai.GenerativeModel(
                model_name='models/gemini-2.5-flash', # Use 1.5-flash for stability
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