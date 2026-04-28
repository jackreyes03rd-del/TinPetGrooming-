
from flask import Blueprint

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")

from app.owner import routes
