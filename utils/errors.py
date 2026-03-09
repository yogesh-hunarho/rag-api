import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Codes — frontend should match on these
# ---------------------------------------------------------------------------

class ErrorCode:
    # Client errors
    INVALID_SESSION = "INVALID_SESSION"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    CHAPTER_NOT_UPLOADED = "CHAPTER_NOT_UPLOADED"
    CHAPTER_EMPTY = "CHAPTER_EMPTY"
    INVALID_PARAM = "INVALID_PARAM"
    FILE_ALREADY_UPLOADED = "FILE_ALREADY_UPLOADED"
    UNSUPPORTED_FILE = "UNSUPPORTED_FILE"

    # Gemini / LLM errors
    RATE_LIMIT = "RATE_LIMIT"
    TOKEN_LIMIT = "TOKEN_LIMIT"
    INVALID_API_KEY = "INVALID_API_KEY"
    LLM_BLOCKED = "LLM_BLOCKED"
    LLM_ERROR = "LLM_ERROR"
    INVALID_LLM_RESPONSE = "INVALID_LLM_RESPONSE"

    # Server errors
    VECTOR_STORE_ERROR = "VECTOR_STORE_ERROR"
    RETRIEVAL_ERROR = "RETRIEVAL_ERROR"
    FILE_IO_ERROR = "FILE_IO_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# Structured API Error
# ---------------------------------------------------------------------------

class APIError(HTTPException):
    """
    Structured HTTP error that returns a consistent JSON body.
    Frontend can check response.error.code to handle each case.
    """

    def __init__(self, status_code: int, code: str, message: str, retry: bool = False):
        self.error_code = code
        self.error_message = message
        self.retry = retry
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": code,
                    "status": status_code,
                    "message": message,
                    "retry": retry,
                }
            },
        )


# ---------------------------------------------------------------------------
# Gemini Error Classifier
# ---------------------------------------------------------------------------

def classify_gemini_error(exc: Exception) -> APIError:
    """
    Parse Gemini/Langchain exceptions and return a structured APIError.
    Gemini errors from langchain come as generic exceptions with HTTP status
    codes embedded in the error message string.
    """
    msg = str(exc).lower()
    original = str(exc)

    # 429 — Rate limit / quota exceeded
    if "429" in msg or "rate limit" in msg or "quota" in msg or "resource exhausted" in msg:
        logger.warning(f"Gemini rate limit hit: {original[:200]}")
        return APIError(
            status_code=429,
            code=ErrorCode.RATE_LIMIT,
            message="Gemini API rate limit exceeded. Please try again in a few seconds.",
            retry=True,
        )

    # Token limit exceeded
    if "token" in msg and ("limit" in msg or "exceed" in msg or "too long" in msg):
        logger.warning(f"Gemini token limit: {original[:200]}")
        return APIError(
            status_code=413,
            code=ErrorCode.TOKEN_LIMIT,
            message="Input text is too long for the model. Try uploading a shorter chapter.",
            retry=False,
        )

    # 401/403 — Invalid API key or permission denied
    if "401" in msg or "403" in msg or "api key" in msg or "permission" in msg or "unauthorized" in msg:
        logger.error(f"Gemini auth error: {original[:200]}")
        return APIError(
            status_code=401,
            code=ErrorCode.INVALID_API_KEY,
            message="Invalid or expired Gemini API key. Please check your configuration.",
            retry=False,
        )

    # Safety block
    if "blocked" in msg or "safety" in msg or "harm" in msg:
        logger.warning(f"Gemini safety block: {original[:200]}")
        return APIError(
            status_code=422,
            code=ErrorCode.LLM_BLOCKED,
            message="Content was blocked by Gemini safety filters. Try different chapter content.",
            retry=False,
        )

    # 503 / 500 — Gemini service unavailable
    if "503" in msg or "500" in msg or "unavailable" in msg or "internal" in msg:
        logger.error(f"Gemini service error: {original[:200]}")
        return APIError(
            status_code=503,
            code=ErrorCode.LLM_ERROR,
            message="Gemini service is temporarily unavailable. Please try again.",
            retry=True,
        )

    # Fallback — unknown LLM error
    logger.error(f"Unknown Gemini error: {original[:300]}")
    return APIError(
        status_code=502,
        code=ErrorCode.LLM_ERROR,
        message=f"AI generation failed: {original[:150]}",
        retry=True,
    )
