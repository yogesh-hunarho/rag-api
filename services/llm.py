import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from utils.errors import classify_gemini_error, APIError, ErrorCode

load_dotenv()
logger = logging.getLogger(__name__)

llm_model = "gemini-2.5-flash-lite"

def get_llm(temperature=0.3, top_p=0.9, max_tokens=10000):
    return ChatGoogleGenerativeAI(
        model=llm_model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        response_mime_type="application/json"
    )


def get_llm_for_mindmap():
    return ChatGoogleGenerativeAI(
        model=llm_model,
        temperature=0.0,
        top_p=0.1,
        max_tokens=2000,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on rate limit or transient server errors."""
    msg = str(exc).lower()
    return any(keyword in msg for keyword in [
        "429", "rate limit", "quota", "resource exhausted",
        "503", "500", "unavailable", "internal",
        "timeout", "connection",
    ])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _invoke_with_retry(llm, prompt: str):
    """Internal: invoke LLM with retry on transient errors only."""
    return llm.invoke(prompt)


def invoke_llm(llm, prompt: str):
    """
    Invoke the LLM with retry + structured error handling.
    - Retries on 429/503 (up to 3 times with exponential backoff)
    - Converts all Gemini errors to structured APIError for frontend
    """
    logger.info("Invoking LLM...")
    try:
        response = _invoke_with_retry(llm, prompt)
        logger.info(f"LLM response received ({len(response.content)} chars)")
        return response
    except APIError:
        raise  # Already structured, pass through
    except Exception as exc:
        raise classify_gemini_error(exc)
