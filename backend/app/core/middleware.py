"""D6: Security middleware for request processing + request context (request_id, timing)."""
import time
import uuid
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Set request_id (from header or new UUID), add X-Request-ID to response, log per-request line."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.time()
        try:
            response: Response = await call_next(request)
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error(
                "request.error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "latency_ms": latency_ms,
                },
                exc_info=True,
            )
            raise

        latency_ms = int((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        
        return response


class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit upload size for POST/PUT requests with Content-Length header."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Only check for methods that might have a body
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
                    if size > max_size:
                        from starlette.responses import JSONResponse
                        return JSONResponse(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            content={
                                "detail": f"Request body too large. Maximum allowed size: {settings.MAX_UPLOAD_SIZE_MB}MB"
                            }
                        )
                except ValueError:
                    pass  # Invalid content-length, let it pass to normal handling
        
        return await call_next(request)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and remove unsafe characters."""
    import re
    import os
    
    if not filename:
        return "unnamed_file"
    
    # Get just the filename without path
    filename = os.path.basename(filename)
    
    # Remove or replace unsafe characters
    # Keep only alphanumeric, dots, underscores, hyphens
    filename = re.sub(r'[^\w\.\-]', '_', filename)
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing dots or underscores
    filename = filename.strip('._')
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        name = name[:200-len(ext)]
        filename = name + ext
    
    # If empty after sanitization, use default
    if not filename:
        filename = "unnamed_file"
    
    return filename

