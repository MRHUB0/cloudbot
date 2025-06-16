import os
import json
import streamlit as st
from pathlib import Path
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from rss_parser import fetch_rss_to_jsonl
from firebase_admin import auth, credentials, initialize_app
from azure.storage.blob import BlobServiceClient

# --- CONFIG ---
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
FIREBASE_JSON = os.getenv("FIREBASE_ADMIN_JSON")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "userdata")

# --- FIREBASE INIT ---
if not FIREBASE_JSON:
    st.error("❌ Firebase config missing from environment.")
    st.stop()

try:
    cred = credentials.Certificate(json.loads(FIREBASE_JSON.replace("\\n", "\n")))
    initialize_app(cred)
except Exception as e:
    st.error(f"❌ Failed to initialize Firebase: {e}")
    st.stop()

# --- AZURE OPENAI CLIENT ---
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# --- BLOB STORAGE CLIENT ---
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)

# --- SEARCH FUNCTION ---
def search_documents(query, top_k=3):
    st.info(f"🔍 Searching for: '{query}' in Azure Cognitive Search")
    try:
        client_search = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX,
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )
        results = client_search.search(search_text=query, top=top_k)
        contents = []
        for r in results:
            raw_content = r.get("content", "") or r.get("text", "") or str(r)
            try:
                maybe_dict = json.loads(raw_content)
                text = maybe_dict.get("text", "") or maybe_dict.get("content", raw_content)
            except:
                text = raw_content
            contents.append(text)
        return contents
    except Exception as e:
        st.error(f"❌ Search failed: {e}")
        return []

# --- GPT CALL ---
def ask_smartbot(question, context, username):
    prompt = f"""Use only the context below to answer the question.

Context:
{context}

Question: {question}
Answer:
"""
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"❌ GPT call failed: {e}")
        return "Sorry, I couldn't process your request right now."

# --- SAVE TO BLOB STORAGE ---
def save_user_log(username, question):
    try:
        blob_client = container_client.get_blob_client(f"{username}.txt")
        if blob_client.exists():
            old = blob_client.download_blob().readall().decode()
            new = old + f"\n{question}"
        else:
            new = question
        blob_client.upload_blob(new, overwrite=True)
    except Exception as e:
        st.warning(f"⚠️ Could not save user log: {e}")

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Nature’s Pleasure Bot", page_icon="🌿")

# --- Load Google Sign-In token ---
token = st.query_params.get("token")
if not token:
    st.warning("🔒 Please log in first.")
    st.stop()

try:
    decoded_token = auth.verify_id_token(token)
    username = decoded_token.get("name") or decoded_token.get("email") or "guest"
except Exception as e:
    st.error(f"❌ Invalid login: {e}")
    st.stop()

st.success(f"✅ Welcome, {username}")

# --- UI Header ---
st.markdown("<h1 style='text-align:center;'>🌿 Nature’s Pleasure Herbal SmartBot</h1>", unsafe_allow_html=True)

# --- Refresh RSS ---
if st.button("🔄 Refresh Herbal Feeds"):
    with st.spinner("Fetching RSS feeds..."):
        articles = fetch_rss_to_jsonl()
        st.success(f"✅ {len(articles)} articles saved.")

# --- Chat Input ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.chat_input("Ask me anything about herbs or tea...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.spinner("Thinking..."):
        context_blocks = search_documents(user_input, top_k=3)
        if not context_blocks:
            bot_reply = "⚠️ No relevant data found in search index."
        else:
            safe_context = "\n\n".join(context_blocks)[:10000]
            bot_reply = ask_smartbot(user_input, safe_context, username)
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
    save_user_log(username, user_input)

# --- Display Chat ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
