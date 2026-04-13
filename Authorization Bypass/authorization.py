"""
AuthorizationBypass Integration Module
=======================================

This module provides authorization checking functions that can be integrated
into the main app.py to demonstrate authorization bypass vulnerabilities and 
their prevention.

When ENABLE_AUTHORIZATION_BYPASS = True:
  - Authorization checks are SKIPPED (vulnerable behavior)
  - Any authenticated user can call ANY endpoint
  - This is for DEMONSTRATION PURPOSES ONLY

When ENABLE_AUTHORIZATION_BYPASS = False:
  - Authorization checks are ENFORCED (secure behavior)
  - User role must match endpoint requirements
  - Implements proper role-based access control (RBAC)

Usage in app.py:
    from Authorization_Bypass.authorization import (
        check_role_requirement,
        extract_user_role_from_token
    )

    ENABLE_AUTHORIZATION_BYPASS = True/False

    @app.post("/api/instructor/admit-student")
    def instructor_admit_student(payload: AdmitStudentPayload, request: Request):
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["instructor"], ENABLE_AUTHORIZATION_BYPASS)
        # ... rest of endpoint logic
"""

from fastapi import HTTPException, Request
from typing import Optional, List, Tuple

# Token verification will be set at runtime
_verify_session_token = None


class AuthorizationError(HTTPException):
    """Authorization-specific HTTP exception."""
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


def set_token_verifier(verify_func):
    """
    Set the token verification function at runtime.
    This is called by app.py during initialization.
    """
    global _verify_session_token
    _verify_session_token = verify_func


def extract_user_role_from_token(request: Request) -> Tuple[str, str]:
    """
    Extract user information from Bearer token in Authorization header.
    
    ✅ SECURE: User must have logged in with username/password to get token.
    The token proves their identity - prevents header spoofing.
    
    Token is obtained from POST /api/login response.
    
    Args:
        request: The FastAPI Request object
    
    Returns:
        Tuple of (username, role)
    
    Raises:
        HTTPException 401: If Bearer token is missing or invalid
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Missing or invalid Authorization header. Format: Bearer <token>"
        )
    
    token = auth_header.replace("Bearer ", "").strip()
    
    if not _verify_session_token:
        raise HTTPException(
            status_code=500,
            detail="Token verification not initialized"
        )
    
    # Verify token is valid and get user info
    user_data = _verify_session_token(token)
    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please login again."
        )
    
    username = user_data.get("username")
    role = user_data.get("role")
    
    if not username or not role:
        raise HTTPException(status_code=401, detail="Malformed token")
    
    return username, role.lower()


def check_role_requirement(
    user_role: str,
    required_roles: List[str],
    bypass_enabled: bool = False,
    context: str = "This resource"
) -> None:
    """
    Check if user's role matches the endpoint requirement.
    
    Args:
        user_role: The user's actual role (from token/headers)
        required_roles: List of roles allowed to access this endpoint
        bypass_enabled: If True, skip authorization (VULNERABLE - for demo only)
        context: Description of what resource is being accessed (for error message)
    
    Returns:
        None if authorization passes
    
    Raises:
        AuthorizationError: If role doesn't match and bypass is disabled
    
    Examples:
        # Allow only instructors to access endpoint
        check_role_requirement(role, ["instructor"], ENABLE_AUTHORIZATION_BYPASS)
        
        # Allow instructors or admins
        check_role_requirement(role, ["instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS)
        
        # Secure version - always checks
        check_role_requirement(role, ["instructor"], False)
    """
    
    # BYPASS MODE: Skip authorization check (VULNERABLE)
    if bypass_enabled:
        return
    
    # SECURE MODE: Enforce authorization
    user_role_lower = user_role.lower()
    required_roles_lower = [r.lower() for r in required_roles]
    
    if user_role_lower not in required_roles_lower:
        raise AuthorizationError(
            detail=f"Access denied. {context} requires role(s): {', '.join(required_roles)}. "
                   f"Your role: {user_role}"
        )


def check_data_ownership(
    requesting_user: str,
    requested_user: str,
    bypass_enabled: bool = False,
    context: str = "This resource"
) -> None:
    """
    Check if user is trying to access their own data only.
    
    CRITICAL SECURITY CHECK: Prevents students from viewing/modifying other students' data.
    
    Args:
        requesting_user: The user making the request
        requested_user: The user whose data is being accessed
        bypass_enabled: If True, skip check (VULNERABLE - for demo only)
        context: Description of data being accessed
    
    Returns:
        None if check passes
    
    Raises:
        AuthorizationError: If user is trying to access someone else's data
    
    Examples:
        # Student can only view their own grades
        check_data_ownership(username, payload.student_username, bypass_enabled)
    """
    
    # BYPASS MODE: Skip data ownership check (VULNERABLE)
    if bypass_enabled:
        return
    
    # SECURE MODE: Enforce data ownership
    if requesting_user != requested_user:
        raise AuthorizationError(
            detail=f"Access denied. {context} requires data ownership. "
                   f"You can only access your own data."
        )


def get_role_description(role: str) -> str:
    """Get human-readable description of a role."""
    descriptions = {
        "student": "Student - Can search courses, enroll, view own grades",
        "instructor": "Instructor - Can manage courses, grades, and assignments",
        "admin": "Administrator - Can manage users and system configuration"
    }
    return descriptions.get(role.lower(), f"Unknown role: {role}")


# Authorization endpoints mapping
# This table shows which roles can access which endpoints

RBAC_CONFIGURATION = {
    # Student endpoints (public search, own data view)
    "/api/student/search-courses": ["student", "instructor", "admin"],
    "/api/student/view-grades": ["student", "instructor", "admin"],
    "/api/student/my-courses": ["student", "instructor", "admin"],
    "/api/student/enroll": ["student"],
    "/api/student/deregister": ["student"],
    
    # Instructor endpoints
    "/api/instructor/admit-student": ["instructor", "admin"],
    "/api/instructor/remove-student": ["instructor", "admin"],
    "/api/instructor/assign-grade": ["instructor", "admin"],
    "/api/instructor/create-assignment": ["instructor", "admin"],
    "/api/instructor/create-course": ["instructor", "admin"],
    "/api/instructor/add-material": ["instructor", "admin"],
    
    # Admin endpoints
    "/api/admin/add-teacher": ["admin"],
    "/api/admin/delete-teacher": ["admin"],
    "/api/admin/add-student": ["admin"],
    "/api/admin/remove-student": ["admin"],
    "/api/admin/add-course": ["admin"],
    "/api/admin/delete-course": ["admin"],
    "/api/admin/action": ["admin"],
}


def get_required_roles_for_endpoint(endpoint_path: str) -> Optional[List[str]]:
    """
    Get the list of roles required to access an endpoint.
    
    Args:
        endpoint_path: The API endpoint path (e.g., "/api/instructor/admit-student")
    
    Returns:
        List of allowed roles, or None if endpoint is public
    """
    return RBAC_CONFIGURATION.get(endpoint_path)


def is_endpoint_protected(endpoint_path: str) -> bool:
    """Check if an endpoint has role-based access control."""
    return endpoint_path in RBAC_CONFIGURATION
