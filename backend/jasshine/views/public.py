"""Página pública (landing)."""
from flask import Blueprint, render_template

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    return render_template("index.html")
