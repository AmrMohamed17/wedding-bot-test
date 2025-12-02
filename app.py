import os
from flask import Flask, request, jsonify
from ai_engine import get_bot_response

app = Flask(__name__)

# --- CONFIGURATION ---
# This is a secret password Facebook will use to verify it's talking to YOU.
# You can change this to anything, e.g., "my_secret_password_123"
VERIFY_TOKEN = "pictures_hall_secret_token"

@app.route("/", methods=["GET"])
def home():
    return "Pictures Hall Bot is Running! 🚀"

# --- FACEBOOK WEBHOOK ENDPOINT ---
# This is where Facebook Messenger will send messages
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    
    # 1. VERIFICATION (Facebook checks if we are the right server)
    if request.method == "GET":
        token_sent = request.args.get("hub.verify_token")
        if token_sent == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid verification token", 403

    # 2. HANDLING MESSAGES (User sends a message)
    if request.method == "POST":
        data = request.get_json()
        
        # Facebook sends a complex JSON object. We need to extract the text.
        try:
            if data['object'] == 'page':
                for entry in data['entry']:
                    for event in entry['messaging']:
                        
                        # Check if it is a user message (text)
                        if 'message' in event and 'text' in event['message']:
                            sender_id = event['sender']['id'] # This acts as the Phone/User ID
                            user_text = event['message']['text']
                            
                            print(f"📩 Received from {sender_id}: {user_text}")
                            
                            # --- CALL THE AI BRAIN ---
                            bot_reply = get_bot_response(user_text, user_phone=sender_id)
                            
                            # --- TODO: SEND REPLY BACK TO FACEBOOK ---
                            # For now, we just print it to the terminal to test.
                            print(f"🤖 Bot Reply: {bot_reply}")
                            
                            # In the next step, we will add the code to send this text back to FB.
                            
        except Exception as e:
            print(f"Error parsing message: {e}")

        return "Message Received", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)