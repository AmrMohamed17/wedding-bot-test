import os
import streamlit as st
import google.generativeai as genai
from datetime import datetime
from database import check_availability, get_info, get_full_knowledge_base

# --- CONFIGURATION ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_HARDCODED_KEY")

genai.configure(api_key=API_KEY)

active_sessions = {}

# --- TOOLS ---
# Only 2 Tools now! No booking tool.
def tool_check_availability(date_str: str, time_slot: str):
    return check_availability(date_str, time_slot)

def tool_get_general_info(key: str):
    return get_info(key)

tools = [tool_check_availability, tool_get_general_info]

# --- MAIN FUNCTION ---
def get_bot_response(user_message, user_phone):
    global active_sessions
    
    today = datetime.now().strftime("%Y-%m-%d")
    knowledge_base = get_full_knowledge_base()
    admin_phone = get_info('Admin_Phone')
    
    # --- UPDATED PERSONA (Referral Mode) ---
    nour_instruction = f"""
    You are 'Nour', the Sales Assistant for 'Pictures Hall' (قاعة بيكتشرز).
    Current Date: {today}.
    
    📚 KNOWLEDGE BASE:
    {knowledge_base}
    
    🛑 STRICT RULES:
    
    1. **NO BOOKING:** You CANNOT create bookings yourself. You are "Read Only".
    2. **CHECKING AVAILABILITY:**
       - If user asks for a date, ask "Day or Night?"
       - Use `tool_check_availability`.
       - **IF AVAILABLE:** Say: "The date is available! 🎉 To finalize the booking, please contact the administration at: {admin_phone}".
       - **IF BOOKED:** Say: "Sorry, this day is already booked."
       - **IF PAST:** Say: "We cannot check past dates."
       
    3. **PRICING:** 
       - You can calculate prices and explain packages fully.
       - But when they say "Okay, book it", refer them to the Admin Phone {admin_phone}.
       
    4. **CAPACITY:** Max 400.
    5. **TONE:** Professional, Egyptian Arabic.
    6. **PHONE NUMBERS:** Always provide the Admin Phone {admin_phone} with the first 0 (e.g. 0100xxx) for bookings.
    """

    if user_phone not in active_sessions:
        try:
            model = genai.GenerativeModel(
                model_name='models/gemini-2.5-flash',
                tools=tools,
                system_instruction=nour_instruction
            )
            active_sessions[user_phone] = model.start_chat(enable_automatic_function_calling=True)
        except Exception as e:
            return "عذرًا، حدث خطأ أثناء تشغيل النظام."
    
    chat_session = active_sessions[user_phone]
    try:
        response = chat_session.send_message(user_message)
        return response.text
    except Exception as e:
        del active_sessions[user_phone]
        return "عذرًا، حدث خطأ تقني."