import os
import json
import streamlit as st
from pathlib import Path
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from rss_parser import fetch_rss_to_jsonl

# --- Azure Config ---
AZURE_OPENAI_ENDPOINT = "https://smartbotx.openai.azure.com/"
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = "SmartBotX"

SEARCH_SERVICE = "smartbot-cheapsearch"
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"

# --- UI Mode Switch ---
mode = st.radio("Choose Bot Mode", ["Nature’s Pleasure 🌿", "Torah 🕎"], horizontal=True)
SEARCH_INDEX = "torah-index" if "Torah" in mode else "smartbot-index"

# --- Initialize Azure OpenAI Client ---
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# --- Load Logo ---
logo_path = Path(__file__).parent / ("logo.jpg" if "Nature" in mode else "Torah.jfif")
if logo_path.exists():
    st.image(str(logo_path), width=120)

# --- Themed Header ---
if "Nature" in mode:
    st.markdown(
        "<div style='text-align:center;background-color:#1e1e1e;padding:15px;border-radius:10px;'>"
        "<h1 style='color:#91d18b;'>🌿 Nature’s Pleasure Bot</h1>"
        "<p style='color:#bbbbbb;'>Ask about herbs, teas, or holistic healing.</p>"
        "</div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<h1 style='text-align: center; color: #3b3b3b;'>🕎 Torah SmartBot</h1>"
        "<p style='text-align: center;'>Ask about scripture, Hebrew context, or Torah study.</p>",
        unsafe_allow_html=True
    )

# --- RSS Refresh Button for Nature ---
if "Nature" in mode:
    if st.button("🔄 Refresh Herbal Feeds"):
        with st.spinner("Fetching latest herbal knowledge..."):
            articles = fetch_rss_to_jsonl()
            st.success(f"✅ {len(articles)} herbal articles parsed and saved.")

# --- Search Function ---
def search_documents(query, top_k=3):
    st.info(f"🔍 Searching for: '{query}' in Azure Cognitive Search")
    try:
        client_search = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=SEARCH_INDEX,
            credential=AzureKeyCredential(AZURE_SEARCH_KEY)
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

# --- GPT Call ---
def ask_smartbot(question, context):
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

# --- Input Field and Bot Output ---
user_input = st.text_input("💬 Ask something:")

if user_input:
    with st.spinner("Thinking..."):
        context_blocks = search_documents(user_input, top_k=3)
        if not context_blocks:
            st.warning("⚠️ No relevant data found in search index.")
        else:
            joined_context = "\n\n".join(context_blocks[:3])
            safe_context = joined_context[:10000]
            answer = ask_smartbot(user_input, safe_context)
            st.markdown("### 🤖 SmartBot says:")
            st.write(answer)
