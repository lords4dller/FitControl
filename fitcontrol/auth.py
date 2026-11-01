from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import Perfil, Usuario

bp = Blueprint("auth", __name__)

PAGINA_INICIAL = {
    Perfil.ADMIN: "admin.inicio",
    Perfil.TREINADOR: "treinador.inicio",
    Perfil.ALUNO: "aluno.inicio",
}


def perfil_obrigatorio(*perfis):
    """Restringe a rota aos perfis informados."""

    def decorador(view):
        @wraps(view)
        @login_required
        def protegida(*args, **kwargs):
            if current_user.perfil not in perfis:
                abort(403)
            return view(*args, **kwargs)

        return protegida

    return decorador


def destino_seguro(destino):
    """Aceita apenas caminhos internos, evitando redirecionamento para outro site."""
    if not destino or not destino.startswith("/") or destino.startswith("//"):
        return None
    if "\\" in destino:
        return None
    partes = urlsplit(destino)
    return None if partes.scheme or partes.netloc else destino


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = db.session.scalar(db.select(Usuario).filter_by(email=email))

        if usuario and usuario.verificar_senha(senha) and login_user(usuario):
            destino = destino_seguro(request.args.get("next"))
            return redirect(destino or url_for("inicio"))

        # Mensagem única para não revelar se o e-mail existe ou se a conta está inativa.
        flash("E-mail ou senha incorretos.", "erro")

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
