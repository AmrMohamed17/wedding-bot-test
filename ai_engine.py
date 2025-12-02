import os
import streamlit as st
import google.generativeai as genai
from datetime import datetime
from database import check_availability, add_booking, get_info, get_full_knowledge_base

# --- CONFIGURATION ---
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=API_KEY)

active_sessions = {}


def tool_check_availability(date_str: str, time_slot: str):
    return check_availability(date_str, time_slot)

def tool_book_date(date_str: str, time_slot: str, name: str, phone: str, package_name: str):
    success = add_booking(date_str, time_slot, name, phone, package_name)
    if success:
        deposit_key = f"Deposit_{time_slot}" 
        amount = get_info(deposit_key)
        return f"SUCCESS: Booking recorded. Deposit: {amount} EGP within 48 hours."
    else:
        return "Booking Failed. System Error."

def tool_get_general_info(key: str):
    return get_info(key)

# Only 3 tools now!
tools = [tool_check_availability, tool_book_date, tool_get_general_info]

# --- MAIN FUNCTION ---
def get_bot_response(user_message, user_phone):
    global active_sessions
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. FETCH FULL KNOWLEDGE (The "Cheat Sheet")
    # This grabs ALL your packages, extras, and info as one big text block.
    knowledge_base = get_full_knowledge_base()
    
    # 2. THE PERSONA
    nour_instruction = f"""
    You are 'Nour', the Sales Assistant for 'Pictures Hall' (قاعة بيكتشرز) in Mansoura.
    Current Date: {today}.
    
    📚 YOUR KNOWLEDGE BASE (STRICT FACTS):
    {knowledge_base}
    
    🛑 INSTRUCTIONS:
    1. **Strict Accuracy:** You MUST use the data above. Do not invent prices.
    2. **Tone:** Egyptian Arabic (عامية مهذبة). Professional & Welcoming. NO 'Habiby/Ro7y'.
    3. **Packages:** 
       - If user asks generally "What are your prices?", ask: "When is the date?" and "How many guests?" first.
       - If they specify date/guests, look at the KNOWLEDGE BASE above and recommend the matching package.
    4. **Booking:** Use `tool_book_date`. Mention Deposit (48hrs).
    5. **Availability:** Ask "Day or Night?" -> Use `tool_check_availability`.
    6. **Extras:** You can upsell extras from the list (e.g., Zaffa, Meals) if appropriate.
    
    SEASONS:
    - Summer: Months 3-10.
    - Winter: Months 12, 1, 2.
    """

    # 3. Session Management
    if user_phone not in active_sessions:
        try:
            model = genai.GenerativeModel(
                model_name='models/gemini-2.5-flash',
                tools=tools,
                system_instruction=nour_instruction
            )
            active_sessions[user_phone] = model.start_chat(enable_automatic_function_calling=True)
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    # 4. Chat
    chat_session = active_sessions[user_phone]
    try:
        response = chat_session.send_message(user_message)
        return response.text
    except Exception as e:
        del active_sessions[user_phone]
        return "عذرًا، حدث خطأ تقني. يرجى المحاولة مرة أخرى."