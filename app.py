import os
import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import json
import requests
from dotenv import load_dotenv
from openai import AzureOpenAI
import feedparser

# Load environment variables
load_dotenv()

# Firebase Initialization
firebase_json_raw = os.environ.get("FIREBASE_ADMIN_JSON")
if firebase_json_raw:
    try:
        firebase_json = json.loads(firebase_json_raw)
        firebase_json["private_key"] = firebase_json["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(firebase_json)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Firebase initialization failed: {e}")
        st.stop()

# Azure OpenAI Setup
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

# Page Configuration
st.set_page_config(page_title="Nature's Pleasure Bot", page_icon="🌿")
st.image("logo.jpg", width=150)
st.title("🌿 Nature's Pleasure Bot")
st.markdown("Ask about herbal remedies, upload a plant photo, or explore herbal news!")

# Session State
st.session_state.setdefault("guest", False)
st.session_state.setdefault("guest_question_count", 0)
st.session_state.setdefault("saved", [])

# Auth Handling
query_params = st.query_params
token = query_params.get("token", [None])[0]
user_email = None

if token:
    try:
        decoded_token = auth.verify_id_token(token)
        user_email = decoded_token.get("email")
        st.success(f"✅ Logged in as {user_email}")
    except:
        st.warning("⚠️ Invalid or expired token. Please refresh or log in again.")
        if st.button("Continue as Guest"):
            st.session_state["guest"] = True
        else:
            st.stop()
elif not st.session_state["guest"]:
    if st.button("Continue as Guest"):
        st.session_state["guest"] = True
    else:
        st.markdown("[🔐 Sign in with Google](login.html)")
        st.stop()

# Prompt Shortcuts
st.markdown("### 🌟 Try a Quick Prompt")
col1, col2 = st.columns(2)
with col1:
    if st.button("🌙 Herbs for Sleep"):
        st.session_state["preset_input"] = "What herbs help with sleep?"
    if st.button("🌼 Detox Tea Ideas"):
        st.session_state["preset_input"] = "Give me a detox tea recipe"
with col2:
    if st.button("🌿 Immunity Boosters"):
        st.session_state["preset_input"] = "Which herbs support the immune system?"
    if st.button("🧘 Stress Relief"):
        st.session_state["preset_input"] = "What teas help with stress and anxiety?"

# Chat Input
user_input = st.chat_input("Ask me anything about herbs, teas, or healing...")
if st.session_state.get("preset_input"):
    user_input = st.session_state.pop("preset_input")

if user_input:
    if st.session_state["guest"]:
        st.session_state["guest_question_count"] += 1
        if st.session_state["guest_question_count"] > 5:
            st.error("❌ Guest limit reached. Sign in for unlimited access.")
            st.stop()

    st.markdown(f"💬 **You asked:** {user_input}")

    if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and DEPLOYMENT_NAME:
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2023-05-15",
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        try:
            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": user_input}]
            )
            reply = response.choices[0].message.content
            st.markdown(f"🌱 **Bot replied:** {reply}")
            if st.button("❤️ Save this tip"):
                st.session_state["saved"].append(reply)
        except Exception as e:
            st.error(f"OpenAI Error: {e}")
    else:
        st.error("Azure OpenAI is not configured.")

# Image Upload
uploaded_file = st.file_uploader("Upload a plant photo", type=["jpg", "png", "jpeg"])
if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
    plant_id_key = os.getenv("PLANT_ID")
    if not plant_id_key:
        st.error("Missing Plant ID API key.")
    else:
        files = {"images": uploaded_file.getvalue()}
        headers = {"Api-Key": plant_id_key}
        try:
            res = requests.post("https://api.plant.id/v2/identify", headers=headers, files=files)
            if res.status_code == 200:
                result = res.json()
                if result.get("suggestions"):
                    suggestion = result["suggestions"][0]
                    name = suggestion.get("plant_name", "Unknown")
                    sci = suggestion.get("plant_details", {}).get("scientific_name", "Unknown")
                    st.success(f"🌿 Identified: {name} ({sci})")
                else:
                    st.warning("Couldn't confidently identify the plant.")
            else:
                st.error(f"API error: {res.status_code}")
        except Exception as e:
            st.error(f"Plant ID Error: {e}")

# Saved Tips
if st.session_state["saved"]:
    st.markdown("### ⭐ Your Saved Tips")
    for tip in st.session_state["saved"]:
        st.markdown(f"- {tip}")

# RSS Feed
st.markdown("### 📰 Herbal News")
feed = feedparser.parse("https://www.herbalgram.org/rss.aspx")
for entry in feed.entries[:3]:
    st.markdown(f"🔗 [{entry.title}]({entry.link})")