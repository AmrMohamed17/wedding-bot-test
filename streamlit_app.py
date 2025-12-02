import streamlit as st
from ai_engine import get_bot_response

# --- PAGE SETUP ---
st.set_page_config(page_title="Pictures Hall Bot Test", page_icon="💍")

st.title("💍 Pictures Hall Bot - Test Mode")
st.markdown("Test your bot in a real chat interface. Arabic works perfectly here! ✅")

# --- SESSION STATE (Memory) ---
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
    # We use a fixed ID "WebUser" so the bot remembers context during this test
    response = get_bot_response(prompt, user_phone="WebUser_01")

    # 3. Show Bot Message
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})