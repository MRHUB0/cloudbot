# app.py
import os
import streamlit as st
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# --- CONFIG ---
AZURE_OPENAI_ENDPOINT = "https://smartbotx.openai.azure.com/"  # ✅ Your OpenAI endpoint
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = "SmartBotX"  # ✅ Your OpenAI deployment name

SEARCH_SERVICE = "smartbot-cheapsearch"  # ✅ NEW Free-tier Search service name
SEARCH_INDEX = "smartbot-index"
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_KEY")  # or paste admin key for testing
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"

# --- INIT AZURE OPENAI CLIENT ---
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# --- SEARCH FUNCTION WITH DEBUGGING ---
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
            content = r.get("content", "")
            st.write("📄 Document snippet:", content[:100])  # Show preview
            contents.append(content)
        st.success(f"✅ Retrieved {len(contents)} document(s) from index.")
        return contents
    except Exception as e:
        st.error(f"❌ Search failed: {e}")
        return []

# --- GPT CALL ---
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

# --- STREAMLIT UI ---
st.set_page_config(page_title="SmartBot", layout="centered")
st.title("🤖 SmartBot")
st.markdown("Ask Torah, Herbs, HR, or anything from your data.")

user_input = st.text_input("Ask something:")

if user_input:
    with st.spinner("Thinking..."):
        context_blocks = search_documents(user_input)
        if not context_blocks:
            st.warning("⚠️ No relevant data found in search index.")

