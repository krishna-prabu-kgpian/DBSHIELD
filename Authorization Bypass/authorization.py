from fastapi import HTTPException, Request
from typing import Optional, List, Tuple

_verify_session_token = None

class AuthorizationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


def set_token_verifier(verify_func):
    global _verify_session_token
    _verify_session_token = verify_func


def extract_user_role_from_token(request: Request) -> Tuple[str, str]:
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

    if bypass_enabled:
        return
    
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

    if bypass_enabled:
        return

    if requesting_user != requested_user:
        raise AuthorizationError(
            detail=f"Access denied. {context} requires data ownership. "
                   f"You can only access your own data."
        )

def get_role_description(role: str) -> str:
    descriptions = {
        "student": "Student - Can search courses, enroll, view own grades",
        "instructor": "Instructor - Can manage courses, grades, and assignments",
        "admin": "Administrator - Can manage users and system configuration"
    }
    return descriptions.get(role.lower(), f"Unknown role: {role}")


RBAC_CONFIGURATION = {

    "/api/student/search-courses": ["student", "instructor", "admin"],
    "/api/student/view-grades": ["student", "instructor", "admin"],
    "/api/student/my-courses": ["student", "instructor", "admin"],
    "/api/student/enroll": ["student"],
    "/api/student/deregister": ["student"],
    

    "/api/instructor/admit-student": ["instructor", "admin"],
    "/api/instructor/remove-student": ["instructor", "admin"],
    "/api/instructor/assign-grade": ["instructor", "admin"],
    "/api/instructor/create-assignment": ["instructor", "admin"],
    "/api/instructor/create-course": ["instructor", "admin"],
    "/api/instructor/add-material": ["instructor", "admin"],
    

    "/api/admin/add-teacher": ["admin"],
    "/api/admin/delete-teacher": ["admin"],
    "/api/admin/add-student": ["admin"],
    "/api/admin/remove-student": ["admin"],
    "/api/admin/add-course": ["admin"],
    "/api/admin/delete-course": ["admin"],
    "/api/admin/action": ["admin"],
}

def get_required_roles_for_endpoint(endpoint_path: str) -> Optional[List[str]]:
    return RBAC_CONFIGURATION.get(endpoint_path)


def is_endpoint_protected(endpoint_path: str) -> bool:
    return endpoint_path in RBAC_CONFIGURATION
