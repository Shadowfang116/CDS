"""
Canonical role definitions and normalization.
Single source of truth for RBAC role handling.
"""

from fastapi import HTTPException

# Canonical role names used throughout the application
CANONICAL_ROLES = {"Admin", "Reviewer", "Approver", "Viewer"}

# Map common variants/aliases to canonical roles
ROLE_ALIASES: dict[str, str] = {
    # Lowercase variants
    "admin": "Admin",
    "reviewer": "Reviewer",
    "approver": "Approver",
    "viewer": "Viewer",
    # Common alternatives
    "read_only": "Viewer",
    "read-only": "Viewer",
    "readonly": "Viewer",
    "maker": "Reviewer",
    "checker": "Approver",
}


def normalize_role(role: str | None) -> str:
    """
    Normalize a role string to its canonical form.
    
    Args:
        role: The role string to normalize (may be None, empty, or variant)
        
    Returns:
        Canonical role string (e.g., "Admin", "Reviewer")
        
    Raises:
        HTTPException 401: If role is missing/empty or unknown
    """
    if not role or not role.strip():
        raise HTTPException(status_code=401, detail="Invalid token: missing role")
    
    role_cleaned = role.strip()
    
    # Already canonical?
    if role_cleaned in CANONICAL_ROLES:
        return role_cleaned
    
    # Try alias lookup (case-insensitive)
    role_lower = role_cleaned.lower()
    if role_lower in ROLE_ALIASES:
        return ROLE_ALIASES[role_lower]
    
    # Unknown role
    raise HTTPException(
        status_code=401,
        detail=f"Role mapping invalid: '{role_cleaned}' is not a recognized role"
    )


def validate_role_for_creation(role: str | None) -> str:
    """
    Validate and normalize a role for user/token creation.
    Returns 400 error with helpful message for invalid roles.
    
    Args:
        role: The role string to validate
        
    Returns:
        Canonical role string
        
    Raises:
        HTTPException 400: If role is invalid (with list of allowed roles)
    """
    if not role or not role.strip():
        raise HTTPException(
            status_code=400,
            detail=f"Role is required. Allowed roles: {', '.join(sorted(CANONICAL_ROLES))}"
        )
    
    role_cleaned = role.strip()
    
    # Already canonical?
    if role_cleaned in CANONICAL_ROLES:
        return role_cleaned
    
    # Try alias lookup
    role_lower = role_cleaned.lower()
    if role_lower in ROLE_ALIASES:
        return ROLE_ALIASES[role_lower]
    
    # Unknown role - provide helpful error
    raise HTTPException(
        status_code=400,
        detail=f"Invalid role: '{role_cleaned}'. Allowed roles: {', '.join(sorted(CANONICAL_ROLES))}"
    )

