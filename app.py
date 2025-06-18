import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import os
import json
import requests
from dotenv import load_dotenv
from openai import AzureOpenAI

# --- Load environment variables ---
load_dotenv()

# --- Firebase Initialization ---
firebase_json_raw = os.environ.get("FIREBASE_ADMIN_JSON")
if firebase_json_raw:
    try:
        firebase_json = json.loads(firebase_json_raw)
        firebase_json["private_key"] = firebase_json["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(firebase_json)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Failed to initialize Firebase: {e}")

# --- Azure OpenAI Setup ---
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

# --- Page Configuration ---
st.set_page_config(page_title="Nature's Pleasure Bot", page_icon="🌿")
st.title("🌿 Nature's Pleasure Bot")
st.markdown("Welcome! Ask about herbal remedies, upload an herb/fruit photo for ID, or explore RSS articles.")

# --- Token Authentication ---
query_params = st.query_params
token = query_params.get("token", [None])[0]

user_email = None
if token:
    try:
        decoded_token = auth.verify_id_token(token)
        user_email = decoded_token.get("email")
        st.success(f"✅ Logged in as {user_email}")
    except Exception as e:
        st.warning("⚠️ Invalid or expired token. Please refresh or try again.")
        st.stop()
else:
    login_popup = """
    <script>
      function openLoginPopup() {
        window.open("https://naturespleasuress.web.app/login.html", "_blank", "width=500,height=600");
      }
    </script>
    <button onclick="openLoginPopup()" style="padding: 10px 18px; font-size: 16px; cursor: pointer;">🔐 Sign in with Google</button>
    """
    st.warning("🔒 You are not logged in.")
    st.components.v1.html(login_popup, height=100)
    st.stop()

# --- Chat Input ---
user_input = st.chat_input("Ask me anything about herbs, teas, or healing...")
if user_input:
    st.write(f"🧠 You asked: {user_input}")

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
            st.success(reply)
        except Exception as e:
            st.error(f"🛑 OpenAI API Error: {e}")
    else:
        st.error("Missing Azure OpenAI configuration.")

# --- Image Upload for Plant ID ---
uploaded_file = st.file_uploader("Upload an herb or fruit photo for identification", type=["jpg", "png", "jpeg"])
if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
    st.info("🔍 Identifying plant...")

    plant_id_key = os.getenv("PLANT_ID")
    if not plant_id_key:
        st.error("❌ Plant ID API key is missing.")
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
                    st.success(f"🌱 Identified as: {name} ({sci})")
                else:
                    st.warning("Couldn't confidently identify the plant.")
            else:
                st.error(f"❌ Plant ID API call failed: {res.status_code}")
        except Exception as e:
            st.error(f"❌ Error during plant identification: {e}")