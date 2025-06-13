
import os
import json
import requests
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from rss_parser import fetch_rss_to_jsonl

# --- Load environment variables ---
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

herbs = [
    "mint", "chamomile", "ginger", "turmeric", "lemon balm", "peppermint",
    "rosemary", "lavender", "echinacea", "dandelion", "fennel", "hibiscus",
    "licorice", "lemongrass", "nettle", "sage", "thyme", "valerian"
]

def detect_herb(text):
    for herb in herbs:
        if herb.lower() in text.lower():
            return herb
    return None

def fetch_herb_image(herb_name):
    if not PEXELS_API_KEY:
        st.warning("⚠️ Missing PEXELS_API_KEY environment variable.")
        return None
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": f"{herb_name} herb", "per_page": 1}
    try:
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
        data = response.json()
        if data["photos"]:
            return data["photos"][0]["src"]["medium"]
        return None
    except Exception as e:
        st.warning(f"Image fetch error: {e}")
        return None

def ask_smartbot(question, context, username):
    prompt = f"""Use only the context below to answer the question. Personalize the response for {username}.

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

def search_documents(query, top_k=3):
    try:
        client_search = SearchClient(
            endpoint=f"https://{SEARCH_SERVICE}.search.windows.net",
            index_name="torah-index" if "Torah" in st.session_state.mode else "smartbot-index",
            credential=AzureKeyCredential(SEARCH_API_KEY)
        )
        results = client_search.search(search_text=query, top=top_k)
        return [r.get("content", "") or r.get("text", "") or str(r) for r in results]
    except Exception as e:
        st.error(f"❌ Search error: {e}")
        return []

# --- Streamlit setup ---
st.set_page_config(page_title="METATRACES-AI", page_icon="🤖", layout="centered")

username = st.text_input("🧑 Your name (nickname or first name is fine):")
if not username:
    st.warning("Please enter your name to continue.")
    st.stop()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.session_state.mode = st.radio("Choose Bot Mode", ["Nature’s Pleasure 🌿", "Torah 🕎"], horizontal=True)

logo_path = Path(__file__).parent / ("logo.jpg" if "Nature" in st.session_state.mode else "Torah.jfif")
if logo_path.exists():
    st.image(str(logo_path), width=120)

if "Nature" in st.session_state.mode:
    st.markdown(
        f"<div style='text-align:center;background-color:#1e1e1e;padding:15px;border-radius:10px;'>"
        f"<h1 style='color:#91d18b;'>🌿 Nature’s Pleasure Bot</h1>"
        f"<p style='color:#bbbbbb;'>Welcome, {username}! Ask about herbs, teas, or holistic healing.</p>"
        f"</div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"<h1 style='text-align: center; color: #3b3b3b;'>🕎 Torah SmartBot</h1>"
        f"<p style='text-align: center;'>Welcome, {username}! Ask about scripture, history, or Hebrew context.</p>",
        unsafe_allow_html=True
    )

if "Nature" in st.session_state.mode:
    if st.button("🔄 Refresh Herbal Feeds"):
        with st.spinner("Fetching latest herbal knowledge..."):
            articles = fetch_rss_to_jsonl()
            st.write("📦 Parsed Articles:", articles[:3])
            st.success(f"✅ {len(articles)} herbal articles parsed.")

user_input = st.chat_input("Ask me anything...")
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

for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    else:
        st.chat_message("assistant").markdown(msg["content"])
        if "Nature" in st.session_state.mode:
            herb_detected = detect_herb(st.session_state.chat_history[-2]["content"])
            if herb_detected:
                image_url = fetch_herb_image(herb_detected)
                if image_url:
                    st.image(image_url, caption=f"{herb_detected.title()} Herb", use_container_width=True)
