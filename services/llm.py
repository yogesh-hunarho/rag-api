import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from utils.errors import classify_gemini_error, APIError, ErrorCode

load_dotenv()
logger = logging.getLogger(__name__)

llm_model = "gemini-2.5-flash-lite"

DEFAULT_HARD_CAP = int(os.getenv("LLM_MAX_TOKENS_HARD_CAP", "16000"))
MINDMAP_HARD_CAP = int(os.getenv("LLM_MINDMAP_MAX_TOKENS_HARD_CAP", "6000"))


def estimate_text_tokens(text: str) -> int:
    """
    Lightweight token estimate to avoid extra tokenizer dependency.
    Works reasonably for mixed English + Indic content.
    """
    if not text:
        return 0
    return max(1, int(len(text) / 3.8))


def resolve_max_tokens(
    prompt: str | None,
    base_max_tokens: int,
    *,
    hard_cap: int = DEFAULT_HARD_CAP,
    min_tokens: int = 512,
) -> int:
    """
    Determine output token cap from both static config and prompt size.
    - `base_max_tokens`: task default from config
    - `prompt`: full prompt (optional)
    - returns a bounded output cap
    """
    base = max(min_tokens, int(base_max_tokens))
    cap = max(base, int(hard_cap))

    if not prompt:
        return min(base, cap)

    prompt_tokens = estimate_text_tokens(prompt)
    # For larger prompts, allow proportionally larger outputs.
    ratio = 0.34 if prompt_tokens > 12000 else 0.30
    adaptive = int(prompt_tokens * ratio)

    return max(min_tokens, min(max(base, adaptive), cap))


def get_llm(temperature=0.3, top_p=0.9, max_tokens=10000, prompt: str | None = None):
    resolved_max_tokens = resolve_max_tokens(
        prompt=prompt,
        base_max_tokens=max_tokens,
        hard_cap=DEFAULT_HARD_CAP,
    )
    logger.info(
        "LLM config resolved: model=%s max_tokens=%d (base=%d)",
        llm_model,
        resolved_max_tokens,
        max_tokens,
    )
    return ChatGoogleGenerativeAI(
        model=llm_model,
        temperature=temperature,
        max_tokens=resolved_max_tokens,
        top_p=top_p,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        response_mime_type="application/json"
    )


def get_llm_for_mindmap(prompt: str | None = None):
    resolved_max_tokens = resolve_max_tokens(
        prompt=prompt,
        base_max_tokens=2000,
        hard_cap=MINDMAP_HARD_CAP,
        min_tokens=800,
    )
    logger.info(
        "LLM mindmap config resolved: model=%s max_tokens=%d",
        llm_model,
        resolved_max_tokens,
    )
    return ChatGoogleGenerativeAI(
        model=llm_model,
        temperature=0.0,
        top_p=0.1,
        max_tokens=resolved_max_tokens,
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
        meta = getattr(response, "response_metadata", {}) or {}
        usage = getattr(response, "usage_metadata", {}) or {}
        finish_reason = meta.get("finish_reason") or meta.get("stop_reason") or "unknown"
        logger.info(
            "LLM response received (%d chars) finish_reason=%s prompt_tokens=%s output_tokens=%s",
            len(response.content),
            finish_reason,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
        )
        if str(finish_reason).lower() in {"max_tokens", "length"}:
            logger.warning("LLM output may be truncated by max_tokens limit.")
        return response
    except APIError:
        raise  # Already structured, pass through
    except Exception as exc:
        raise classify_gemini_error(exc)
