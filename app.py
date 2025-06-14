
import os
import json
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from firebase_admin import auth, credentials, initialize_app
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from rss_parser import fetch_rss_to_jsonl
from datetime import datetime

# --- Load Environment Variables ---
load_dotenv()
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "SmartBotX")
SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE", "smartbot-cheapsearch")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
SEARCH_INDEX_NATURE = "smartbot-index"
SEARCH_INDEX_TORAH = "torah-index"
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "userdata")

# --- Firebase Init ---
if not hasattr(st.session_state, "firebase_initialized"):
    cred_path = Path("firebase_admin.json")
    if cred_path.exists():
        cred = credentials.Certificate(str(cred_path))
        initialize_app(cred)
        st.session_state.firebase_initialized = True
    else:
        st.error("Firebase Admin SDK JSON not found.")
        st.stop()

# --- Azure OpenAI Client ---
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# --- Azure Blob Logging Function ---
def log_user_to_blob(user_data):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)

        try:
            container_client.create_container()
        except:
            pass

        log_blob_name = "user_log.txt"
        timestamp = datetime.utcnow().isoformat()
        new_entry = f"{timestamp} | {user_data['name']} | {user_data['email']} | {user_data['uid']}\n"

        try:
            existing_blob = container_client.get_blob_client(log_blob_name)
            current_data = existing_blob.download_blob().readall().decode()
        except:
            current_data = ""

        updated_data = current_data + new_entry
        container_client.upload_blob(name=log_blob_name, data=updated_data, overwrite=True)
    except Exception as e:
        st.error(f"⚠️ Failed to log user to Azure Blob: {e}")

# --- Token Verification via URL param ---
query_params = st.experimental_get_query_params()
if "token" in query_params:
    try:
        decoded = auth.verify_id_token(query_params["token"][0])
        st.session_state.user = {
            "name": decoded.get("name", "Guest"),
            "email": decoded.get("email"),
            "uid": decoded.get("uid")
        }
        log_user_to_blob(st.session_state.user)
    except Exception as e:
        st.error(f"Token verification failed: {e}")
        st.stop()

if "user" not in st.session_state:
    st.warning("🔒 Please sign in via Google: [Login Here](login.html)", icon="🔑")
    st.stop()

username = st.session_state.user["name"]

# --- Page Setup ---
st.set_page_config(page_title="METATRACES-AI", page_icon="🤖", layout="centered")
mode = st.radio("Choose Bot Mode", ["Nature’s Pleasure 🌿", "Torah 🕎"], horizontal=True)
SEARCH_INDEX = SEARCH_INDEX_NATURE if "Nature" in mode else SEARCH_INDEX_TORAH

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def search_documents(query, top_k=3):
    client_search = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX,
        credential=AzureKeyCredential(SEARCH_API_KEY)
    )
    results = client_search.search(search_text=query, top=top_k)
    contents = [r.get("content", "") or r.get("text", "") or str(r) for r in results]
    return contents

def ask_smartbot(question, context):
    prompt = f"""Use only the context below to answer the question.

Previous Q&A:
{context}

Current Question:
{question}
Answer:""" 
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400
    )
    return response.choices[0].message.content

# --- UI Header ---
if "Nature" in mode:
    st.title("🌿 Nature’s Pleasure Bot")
else:
    st.title("🕎 Torah SmartBot")

# --- Input & Response ---
user_input = st.chat_input("Ask me anything...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    context_blocks = search_documents(user_input, top_k=3)
    recent_history = [item["content"] for item in st.session_state.chat_history[-5:] if item["role"] == "user"]
    context = "\n\n".join(recent_history + context_blocks)[:10000]

    reply = ask_smartbot(user_input, context)
    st.session_state.chat_history.append({"role": "assistant", "content": reply})

# --- Display Chat ---
for entry in st.session_state.chat_history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
