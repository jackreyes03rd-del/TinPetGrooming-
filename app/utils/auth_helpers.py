from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import flash, g, jsonify, redirect, request, session, url_for, render_template

from app_types import UserRecord, UserRole

                                           
RouteHandler = TypeVar("RouteHandler", bound=Callable[..., Any])

                                 
SESSION_USER_KEY = "current_user_id"

def current_user() -> UserRecord | None:
    return getattr(g, "user", None)

def login_user(user: UserRecord) -> None:
    session[SESSION_USER_KEY] = user["id"]

def logout_user() -> None:
    session.pop(SESSION_USER_KEY, None)
    for key in list(session.keys()):
        if key.startswith("chat_"):
            session.pop(key, None)

def role_home(role: UserRole) -> str:
    if role == "owner":
        return url_for("owner.owner_portal")
    if role in {"groomer", "staff"}:
        return url_for("staff.staff_portal")
    return url_for("admin.admin_portal")

def login_required(*roles: UserRole) -> Callable[[RouteHandler], RouteHandler]:
    def decorator(func: RouteHandler) -> RouteHandler:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
                                      
            from app import STARTUP_ERROR
            if STARTUP_ERROR:
                return render_template("error.html", error_message=STARTUP_ERROR), 500
            
            user = current_user()
            
                                        
            if not user:
                                      
                if request.path.startswith('/api/'):
                    return jsonify({"success": False, "error": "Not authenticated"}), 401
                flash("Please log in first.", "error")
                return redirect(url_for("main.public_page"))
            
                                             
            if roles and user.get("role") not in roles:
                                      
                if request.path.startswith('/api/'):
                    return jsonify({"success": False, "error": "Unauthorized"}), 403
                return redirect(role_home(user.get("role", "owner")))
            
            return func(*args, **kwargs)
        
        return cast(RouteHandler, wrapper)
    
    return decorator
