import shutil

import pytest

from fitcontrol import create_app
from fitcontrol.cli import SENHA_DEMO, popular_demo
from fitcontrol.extensions import db


def _configuracao(caminho):
    return {
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{caminho}",
    }


def _encerrar(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture(scope="session")
def banco_modelo(tmp_path_factory):
    """Popula o banco uma vez: calcular o hash das senhas a cada teste é lento."""
    caminho = tmp_path_factory.mktemp("modelo") / "modelo.db"
    app = create_app(_configuracao(caminho))
    with app.app_context():
        db.create_all()
        popular_demo()
    _encerrar(app)
    return caminho


@pytest.fixture
def app(tmp_path, banco_modelo):
    caminho = tmp_path / "teste.db"
    shutil.copy(banco_modelo, caminho)
    app = create_app(_configuracao(caminho))
    yield app
    _encerrar(app)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def entrar(client):
    def _entrar(email, senha=SENHA_DEMO, url="/login"):
        return client.post(url, data={"email": email, "senha": senha})

    return _entrar
