import pytest

from fitcontrol import create_app
from fitcontrol.auth import destino_seguro
from fitcontrol.extensions import db
from fitcontrol.models import Usuario

ADMIN = "admin@fitcontrol.test"
TREINADOR = "giuseppe@fitcontrol.test"
ALUNO = "maria@fitcontrol.test"


@pytest.mark.parametrize(
    "email, destino",
    [(ADMIN, "/admin/"), (TREINADOR, "/treinador/"), (ALUNO, "/aluno/")],
)
def test_login_leva_cada_perfil_a_sua_pagina(client, entrar, email, destino):
    assert entrar(email).status_code == 302
    resposta = client.get("/", follow_redirects=False)
    assert resposta.headers["Location"] == destino
    assert client.get(destino).status_code == 200


def test_email_ignora_maiusculas_e_espacos(client, entrar):
    entrar("  MARIA@FitControl.test ")
    assert client.get("/aluno/").status_code == 200


def test_senha_errada_mostra_erro_e_nao_autentica(client, entrar):
    resposta = entrar(ALUNO, senha="errada")
    assert resposta.status_code == 200
    assert "E-mail ou senha incorretos." in resposta.text
    assert client.get("/aluno/").status_code == 302


def test_email_desconhecido_tem_a_mesma_resposta(entrar):
    assert "E-mail ou senha incorretos." in entrar("ninguem@fitcontrol.test").text


def test_usuario_inativo_nao_entra(app, client, entrar):
    with app.app_context():
        db.session.scalar(db.select(Usuario).filter_by(email=ALUNO)).ativo = False
        db.session.commit()
    assert "E-mail ou senha incorretos." in entrar(ALUNO).text
    assert client.get("/aluno/").status_code == 302


@pytest.mark.parametrize("rota", ["/admin/", "/treinador/", "/aluno/"])
def test_visitante_vai_para_o_login(client, rota):
    resposta = client.get(rota)
    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith("/login")


@pytest.mark.parametrize(
    "email, rota",
    [
        (ALUNO, "/admin/"),
        (ALUNO, "/treinador/"),
        (TREINADOR, "/admin/"),
        (TREINADOR, "/aluno/"),
        (ADMIN, "/treinador/"),
        (ADMIN, "/aluno/"),
    ],
)
def test_perfil_nao_acessa_area_de_outro(client, entrar, email, rota):
    entrar(email)
    resposta = client.get(rota)
    assert resposta.status_code == 403
    assert "Você não tem acesso" in resposta.text


def test_login_respeita_next_interno(entrar):
    resposta = entrar(ALUNO, url="/login?next=/aluno/")
    assert resposta.headers["Location"] == "/aluno/"


@pytest.mark.parametrize(
    "destino",
    ["https://malicioso.test", "//malicioso.test", "/\\malicioso.test", "javascript:alert(1)", ""],
)
def test_destino_externo_e_recusado(destino):
    assert destino_seguro(destino) is None


def test_login_ignora_next_externo(entrar):
    resposta = entrar(ALUNO, url="/login?next=https://malicioso.test")
    assert resposta.headers["Location"] == "/"


def test_logout_encerra_a_sessao(client, entrar):
    entrar(ALUNO)
    assert client.post("/logout").status_code == 302
    assert client.get("/aluno/").status_code == 302


def test_logout_nao_aceita_get(client, entrar):
    entrar(ALUNO)
    assert client.get("/logout").status_code == 405


def test_login_sem_token_csrf_e_recusado(tmp_path):
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}"}
    )
    resposta = app.test_client().post("/login", data={"email": ALUNO, "senha": "x"})
    assert resposta.status_code == 400
