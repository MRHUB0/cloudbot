# app.py
import os
import streamlit as st
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# --- CONFIG ---
AZURE_OPENAI_ENDPOINT = "https://smartbotx.openai.azure.com/"  # ✅ Confirm this matches your Azure OpenAI endpoint
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT_NAME = "version0125"  # This must be your deployment name in Azure

SEARCH_SERVICE = "smartbot-search"
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
    client_search = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX,
        credential=AzureKeyCredential(SEARCH_API_KEY)
    )
    results = client_search.search(search_text=query, top=top_k)
    return [r["content"] for r in results if "content" in r]

# --- GPT CALL ---
def ask_smartbot(question, context):
    prompt = f"""Use only the context below to answer the question.

Context:
{context}

Question: {question}
Answer:
"""
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=400
    )
    return response.choices[0].message.content

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
