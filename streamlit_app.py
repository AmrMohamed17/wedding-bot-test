import streamlit as st
import uuid
from ai_engine import get_bot_response

# --- PAGE SETUP ---
st.set_page_config(page_title="Pictures Hall Bot Test", page_icon="💍")

st.title("💍 Pictures Hall Bot - Test")
st.markdown("Test your bot in a real chat interface. Arabic works perfectly here! ✅")

# --- SESSION STATE & UNIQUE ID GENERATION ---
# 1. Check if this user has a Unique ID. If not, generate one.
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) # Generates a random ID like '9b1deb4d-3b7d...'
    
# 2. Initialize Chat History for this specific user
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- DISPLAY CHAT HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- USER INPUT ---
if prompt := st.chat_input("اكتب رسالتك هنا..."):
    # 1. Show User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Get Bot Response
    # CRITICAL FIX: We pass the Unique Session ID, not a hardcoded name.
    with st.spinner("جاري الكتابة..."):
        response = get_bot_response(prompt, user_phone=st.session_state.session_id)

    # 3. Show Bot Message
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})