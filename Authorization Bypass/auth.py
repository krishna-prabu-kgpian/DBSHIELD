"""
Authorization utilities for role-based access control (RBAC).
Provides decorators and context managers for secure endpoint protection.
"""

from functools import wraps
from fastapi import HTTPException, Request
from typing import Optional, List, Callable


class AuthContext:
    """Holds current user's authentication information."""
    
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role.lower()
    
    def has_role(self, required_role: str) -> bool:
        """Check if user has the required role."""
        return self.role == required_role.lower()
    
    def has_any_role(self, required_roles: List[str]) -> bool:
        """Check if user has any of the required roles."""
        return self.role in [r.lower() for r in required_roles]
    
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    def is_instructor(self) -> bool:
        return self.role == "instructor"
    
    def is_student(self) -> bool:
        return self.role == "student"


def extract_auth_context(request: Request) -> Optional[AuthContext]:
    """
    Extract authentication context from request.
    
    In a real system, this would:
    1. Extract JWT token from Authorization header
    2. Validate token signature
    3. Extract claims (username, role)
    
    For this demo, we use custom headers.
    """
    username = request.headers.get("X-User")
    role = request.headers.get("X-Role")
    
    if not username or not role:
        return None
    
    return AuthContext(username, role)


def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator to enforce role-based access control.
    
    Usage:
        @require_role("instructor", "admin")
        def protected_endpoint(auth: AuthContext):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, request: Request = None, **kwargs):
            auth = extract_auth_context(request)
            
            if not auth:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required. Please provide X-User and X-Role headers."
                )
            
            if not auth.has_any_role(allowed_roles):
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}"
                )
            
            # Pass auth context to handler
            kwargs['auth'] = auth
            return await func(*args, request=request, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, request: Request = None, **kwargs):
            auth = extract_auth_context(request)
            
            if not auth:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required. Please provide X-User and X-Role headers."
                )
            
            if not auth.has_any_role(allowed_roles):
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}"
                )
            
            # Pass auth context to handler
            kwargs['auth'] = auth
            return func(*args, request=request, **kwargs)
        
        # Return async or sync based on function type
        if hasattr(func, '__call__'):
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
        return sync_wrapper
    
    return decorator


def check_data_ownership(requesting_user: str, target_user: str, 
                        allow_admin_override: bool = True) -> None:
    """
    Enforce that users can only access their own data.
    Admins can override if allow_admin_override is True.
    """
    # For real implementation, add is_admin check
    if requesting_user != target_user:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Users can only view their own data."
        )


class AuthorizationError(Exception):
    """Custom exception for authorization failures."""
    pass


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions."""
    pass
