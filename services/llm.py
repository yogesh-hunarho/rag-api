import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature=0.3, top_p=0.9, max_tokens=10000):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        response_mime_type="application/json"
    )


def get_llm_for_mindmap():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0, 
        top_p=0.1, 
        max_tokens=2000,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
