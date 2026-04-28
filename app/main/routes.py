from __future__ import annotations

from flask import redirect, render_template, request, send_file, session, url_for
from pathlib import Path

from app.main import main_bp
from app.utils.auth_helpers import current_user, role_home
from app.utils import login_required
from config import UPLOAD_DIR

                                
from app import STARTUP_ERROR, PUBLIC_SERVICES, OWNER_QUICK_PROMPTS

def get_chat_messages(scope: str) -> list[dict[str, str]]:
    from app import CHAT_SEED
    key = f"chat_{scope}"
    if key not in session:
        session[key] = list(CHAT_SEED)
        session.modified = True
    return list(session[key])

@main_bp.route("/")
def public_page():
    if STARTUP_ERROR:
        return render_template("error.html", error_message=STARTUP_ERROR), 500
    
    user = current_user()
    if user:
        return redirect(role_home(user.get("role", "owner")))
    
    return render_template(
        "main/public.html",
        services=PUBLIC_SERVICES,
        chat_messages=get_chat_messages("public"),
        quick_prompts=OWNER_QUICK_PROMPTS,
        active_auth=request.args.get("auth", ""),
    )

@main_bp.route("/dashboard")
def dashboard_redirect():
    user = current_user()
    if not user:
        return redirect(url_for("main.public_page"))
    return redirect(role_home(user.get("role", "owner")))

@main_bp.route("/toggle-theme", methods=["POST"])
def toggle_theme():
    session["dark_mode"] = not bool(session.get("dark_mode", False))
    target = request.form.get("next") or request.referrer or url_for("main.dashboard_redirect")
    return redirect(target)

@main_bp.route("/uploads/<path:filename>")
@login_required("owner", "groomer", "staff", "admin")
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_DIR, Path(filename).name, as_attachment=True)
