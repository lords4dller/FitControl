from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def ativar_chaves_estrangeiras(conexao, _registro):
    """O SQLite só aplica chaves estrangeiras se isso for pedido em cada conexão."""
    cursor = conexao.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
