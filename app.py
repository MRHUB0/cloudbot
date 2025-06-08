# app.py
import os
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# --- CONFIG ---
AZURE_OPENAI_ENDPOINT = "https://smartbotx.openai.azure.com/"  # ✅ Double-check this is your exact Azure OpenAI resource endpoint
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = "version0125"  # Your deployed model in Azure OpenAI

SEARCH_SERVICE = "smartbot-search"
SEARCH_INDEX = "smartbot-index"
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"

openai.api_type = "azure"
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = "2023-05-15"
openai.api_key = AZURE_OPENAI_KEY

# --- SEARCH FUNCTION ---
def search_documents(query, top_k=3):
    client = SearchClient(endpoint=SEARCH_ENDPOINT,
                          index_name=SEARCH_INDEX,
                          credential=AzureKeyCredential(SEARCH_API_KEY))
    results = client.search(search_text=query, top=top_k)
    return [r["content"] for r in results if "content" in r]

# --- GPT CALL ---
def ask_smartbot(question, context):
    prompt = f"""Use only the context below to answer the question.

Context:
{context}

Question: {question}
Answer:
"""
    response = openai.ChatCompletion.create(
        engine=DEPLOYMENT_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400
    )
    return response["choices"][0]["message"]["content"]

# --- STREAMLIT UI ---
st.set_page_config(page_title="SmartBot", layout="centered")
st.title("🤖 SmartBot")
st.markdown("Ask Torah, Herbs, HR, or anything from your data.")

user_input = st.text_input("Ask something:")

if user_input:
    with st.spinner("Thinking..."):
        context = "\n\n".join(search_documents(user_input))
        if not context:
            st.warning("No relevant data found.")
        else:
            response = ask_smartbot(user_input, context)
            st.success(response)
