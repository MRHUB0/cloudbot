import streamlit as st
import firebase_admin
from firebase_admin import credentials
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Firebase Initialization ---
firebase_json_raw = os.environ.get("FIREBASE_ADMIN_JSON")

if not firebase_json_raw:
    st.error("❌ Firebase config missing from environment.")
else:
    try:
        firebase_json = json.loads(firebase_json_raw)
        firebase_json["private_key"] = firebase_json["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(firebase_json)

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Failed to initialize Firebase: {e}")

# --- Streamlit UI ---
st.set_page_config(page_title="Nature's Pleasure Bot", page_icon="🌿")
st.title("🌿 Nature's Pleasure Bot")

st.markdown("Welcome! Ask about herbal remedies, upload an herb/fruit photo for ID, or explore RSS articles.")

# Placeholder for rest of the app logic
user_input = st.chat_input("Ask me anything...")
if user_input:
    st.write(f"You said: {user_input}")
    # Here, plug into RAG or OpenAI response logic

# Optional: Upload image for plant ID
uploaded_file = st.file_uploader("Upload an herb or fruit photo for identification", type=["jpg", "png", "jpeg"])
if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
    st.info("🔍 Processing image with Plant ID API...")

    plant_id_key = os.getenv("PLANT_ID")
    if not plant_id_key:
        st.error("Plant ID API key is missing in environment variables.")
    else:
        files = {"images": uploaded_file.getvalue()}
        headers = {"Api-Key": plant_id_key}
        res = requests.post("https://api.plant.id/v2/identify", headers=headers, files=files)

        if res.status_code == 200:
            result = res.json()
            if result.get("suggestions"):
                suggestion = result["suggestions"][0]
                st.success(f"Identified as: {suggestion['plant_name']} ({suggestion['plant_details']['scientific_name']})")
            else:
                st.warning("Couldn't confidently identify the plant.")
        else:
            st.error("Failed to query Plant ID API.")
