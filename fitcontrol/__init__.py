import os
import secrets

from flask import Flask, redirect, render_template, url_for
from flask_login import current_user

from .extensions import csrf, db, login_manager
from .models import Perfil


MENU = {
    Perfil.ADMIN: [
        ("admin.inicio", "Painel"),
        ("admin.alunos", "Alunos"),
        ("admin.treinadores", "Treinadores"),
    ],
    Perfil.TREINADOR: [("treinador.inicio", "Meus alunos")],
    Perfil.ALUNO: [("aluno.inicio", "Minha semana")],
}


def formatar_numero(valor, unidade=""):
    """Formata no padrão brasileiro; medidas não informadas viram um traço."""
    if valor is None:
        return "—"
    return f"{valor:g}".replace(".", ",") + unidade


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        # Sem SECRET_KEY no ambiente, as sessões só duram até reiniciar o servidor.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI="sqlite:///"
        + os.path.join(app.instance_path, "fitcontrol.db"),
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Entre para acessar esta página."
    login_manager.login_message_category = "info"

    from . import admin, aluno, auth, cli, treinador

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(treinador.bp)
    app.register_blueprint(aluno.bp)
    cli.registrar(app)
    app.jinja_env.filters["numero"] = formatar_numero

    @app.route("/")
    def inicio():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return redirect(url_for(auth.PAGINA_INICIAL[current_user.perfil]))

    @app.context_processor
    def expor_menu():
        return {"menu": MENU[current_user.perfil] if current_user.is_authenticated else []}

    @app.errorhandler(403)
    def acesso_negado(_erro):
        return render_template("erro.html", codigo=403, mensagem="Você não tem acesso a esta página."), 403

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return render_template("erro.html", codigo=404, mensagem="Página não encontrada."), 404

    return app
