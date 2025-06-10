import os
import streamlit as st
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# --- CONFIG ---
AZURE_OPENAI_ENDPOINT = "https://smartbotx.openai.azure.com/"
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = "SmartBotX"

SEARCH_SERVICE = "smartbot-cheapsearch"
SEARCH_INDEX = "smartbot-index"
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"

# --- INIT AZURE OPENAI CLIENT ---
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

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
                    import json
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
        context_blocks = search_documents(user_input, top_k=3)
        if not context_blocks:
            st.warning("⚠️ No relevant data found in search index.")
        else:
            # --- Token-safe trimming ---
            joined_context = "\n\n".join(context_blocks[:3])  # Limit to top 3 chunks
            safe_context = joined_context[:10000]  # Approx. 2500–3000 tokens

            answer = ask_smartbot(user_input, safe_context)
            st.markdown("### 🤖 SmartBot says:")
            st.write(answer)
