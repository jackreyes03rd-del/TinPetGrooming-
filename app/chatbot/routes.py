from __future__ import annotations

from flask import jsonify, redirect, request, session, url_for

from app.chatbot import chatbot_bp
from app.chatbot.bot import generate_response
from app.utils.auth_helpers import current_user
from app_types import UserRecord
import app.models as db

                      
from app import CHAT_SEED

def get_chat_messages(scope: str) -> list[dict[str, str]]:
    key = f"chat_{scope}"
    if key not in session:
        session[key] = list(CHAT_SEED)
        session.modified = True
    return list(session[key])

def send_chat_message(scope: str, question: str, user: UserRecord | None) -> dict[str, str] | None:
    if not question.strip():
        return None
    
    key = f"chat_{scope}"
    messages = get_chat_messages(scope)
    answer, topic = generate_response(question, history=messages, audience=scope)
    
    user_message = {"role": "user", "content": question}
    assistant_message = {"role": "assistant", "content": answer}
    
    messages.append(user_message)
    messages.append(assistant_message)
    session[key] = messages
    session.modified = True
    
    db.log_chat(user["id"] if user else None, question, answer, topic)
    return assistant_message

@chatbot_bp.route("/chat/<scope>", methods=["POST"])
def chat(scope: str):
    allowed = {"public", "owner", "staff", "admin"}
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
                    
    if scope not in allowed:
        if wants_json:
            return jsonify({"ok": False, "error": "Unknown chat scope."}), 404
        return redirect(url_for("main.public_page"))
    
                                                
    user = current_user()
    if scope != "public" and not user:
        if wants_json:
            return jsonify({
                "ok": False,
                "error": "Please log in first.",
                "redirect_url": url_for("main.public_page")
            }), 401
        return redirect(url_for("main.public_page"))
    
                            
    question = request.form.get("question", "").strip() or request.form.get("prompt", "").strip()
    
                                         
    if wants_json and not question:
        return jsonify({"ok": False, "error": "Message cannot be empty."}), 400
    
                     
    if question:
        assistant_message = send_chat_message(scope, question, user)
        if wants_json:
            return jsonify({
                "ok": True,
                "assistant_message": assistant_message,
                "messages": get_chat_messages(scope),
            })
    
                                    
    target = request.form.get("next") or request.referrer or url_for("main.public_page")
    return redirect(target)
