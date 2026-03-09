import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()
logger = logging.getLogger(__name__)


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    reraise=True,
)
def invoke_llm(llm, prompt: str):
    """Invoke the LLM with retry logic for transient failures (rate limits, network issues)."""
    logger.info("Invoking LLM...")
    response = llm.invoke(prompt)
    logger.info(f"LLM response received ({len(response.content)} chars)")
    return response
