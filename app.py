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
load_dotenv()  # Safe for local testing; Azure will override in App Service

# --- CONFIG ---
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# --- INIT AZURE OPENAI CLIENT ---
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# --- Herb name detection list ---
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
            if isinstance(raw_content, dict):
                text = raw_content.get("text", "") or raw_content.get("content", "")
            elif isinstance(raw_content, str):
                try:
                    maybe_dict = json.loads(raw_content)
                    text = maybe_dict.get("text", "") or maybe_dict.get("content", raw_content)
                except:
                    text = raw_content
            else:
                text = str(raw_content)

            st.write("📄 Document snippet:", text[:100])
            contents.append(text)

        st.success(f"✅ Retrieved {len(contents)} document(s) from index.")
        return contents

    except Exception as e:
        st.error(f"❌ Search failed: {e}")
        return []

# --- GPT CALL ---
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

# --- STREAMLIT UI SETUP ---
st.set_page_config(
    page_title="METATRACES-AI",
    page_icon="🤖",
    layout="centered"
)

# --- User Login ---
username = st.text_input("👤 Enter your name to personalize your session:")
if not username:
    st.stop()

# --- Mode Switcher ---
mode = st.radio("Choose Bot Mode", ["Nature’s Pleasure 🌿", "Torah 🕎"], horizontal=True)

# --- Load Correct Logo ---
logo_path = Path(__file__).parent / ("logo.jpg" if "Nature" in mode else "Torah.jfif")
if logo_path.exists():
    st.image(str(logo_path), width=120)

# --- Themed Header ---
if "Nature" in mode:
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

# --- RSS Refresh (Only for Nature) ---
if "Nature" in mode:
    if st.button("🔄 Refresh Herbal Feeds"):
        with st.spinner("Fetching latest herbal knowledge..."):
            articles = fetch_rss_to_jsonl()
            st.success(f"✅ {len(articles)} herbal articles parsed and saved.")

# --- Chat UI ---
user_input = st.text_input("💬 Ask me anything:")
if user_input:
    st.session_state["last_question"] = user_input
    with st.spinner("Thinking..."):
        context_blocks = search_documents(user_input, top_k=3)
        if not context_blocks:
            st.warning("⚠️ No relevant data found in search index.")
        else:
            joined_context = "\n\n".join(context_blocks)
            safe_context = joined_context[:10000]
            answer = ask_smartbot(user_input, safe_context, username)
            st.markdown("### 🤖 SmartBot says:")
            st.write(answer)

            if "Nature" in mode:
                herb_detected = detect_herb(user_input)
                if herb_detected:
                    image_url = fetch_herb_image(herb_detected)
                    if image_url:
                        st.image(image_url, caption=f"{herb_detected.title()} Herb", use_column_width=True)
