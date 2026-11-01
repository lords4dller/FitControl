import pytest

from fitcontrol.extensions import db
from fitcontrol.models import Perfil, Treinador, Treino, Usuario

ADMIN = "admin@fitcontrol.test"


def _usuario(email):
    return db.session.scalar(db.select(Usuario).filter_by(email=email))


def _aluno_id(app, email):
    with app.app_context():
        return _usuario(email).aluno.id


def _treinador_id(app, email):
    with app.app_context():
        return _usuario(email).treinador.id


@pytest.fixture
def admin(client, entrar):
    entrar(ADMIN)
    return client


def _aluno_valido(**campos):
    return {
        "nome": "Bruna Lima",
        "email": "Bruna@FitControl.test",
        "senha": "senha-forte",
        "data_nascimento": "2001-02-03",
        "sexo": "Feminino",
        "telefone": "11 99999-0000",
        **campos,
    }


def test_painel_oferece_os_menus(admin):
    pagina = admin.get("/admin/").text
    assert "/admin/alunos/novo" in pagina
    assert "/admin/treinadores/novo" in pagina
    assert 'href="/admin/treinadores"' in pagina


def test_cadastrar_aluno_com_treinador_e_dados_separados(app, admin):
    treinador_id = _treinador_id(app, "ana@fitcontrol.test")
    resposta = admin.post(
        "/admin/alunos/novo", data=_aluno_valido(treinador_id=treinador_id)
    )
    assert resposta.status_code == 302
    with app.app_context():
        usuario = _usuario("bruna@fitcontrol.test")
        assert usuario.perfil == Perfil.ALUNO
        assert usuario.aluno.treinador_id == treinador_id
        assert usuario.aluno.dados_pessoais.telefone == "11 99999-0000"
        assert usuario.aluno.dados_pessoais.data_nascimento.year == 2001


def test_aluno_cadastrado_consegue_entrar(admin, app):
    admin.post("/admin/alunos/novo", data=_aluno_valido())
    admin.post("/logout")
    admin.post("/login", data={"email": "bruna@fitcontrol.test", "senha": "senha-forte"})
    assert admin.get("/aluno/").status_code == 200


def test_treinador_cadastrado_consegue_entrar_e_comeca_sem_alunos(admin):
    resposta = admin.post(
        "/admin/treinadores/novo",
        data={
            "nome": "Carlos Souza",
            "email": "carlos@fitcontrol.test",
            "senha": "senha-forte",
            "cref": "123456-G/SP",
            "especialidade": "Funcional",
        },
    )
    assert resposta.status_code == 302
    assert "Carlos Souza" in admin.get("/admin/treinadores").text
    admin.post("/logout")
    admin.post("/login", data={"email": "carlos@fitcontrol.test", "senha": "senha-forte"})
    assert "Nenhum aluno vinculado" in admin.get("/treinador/").text


@pytest.mark.parametrize(
    "campos, erro",
    [
        ({"nome": " "}, "Informe o nome"),
        ({"email": "sem-arroba"}, "e-mail válido"),
        ({"email": "maria@fitcontrol.test"}, "Já existe uma conta"),
        ({"email": "MARIA@fitcontrol.test"}, "Já existe uma conta"),
        ({"senha": "curta"}, "pelo menos 8"),
        ({"data_nascimento": "31/12/2000"}, "data de nascimento válida"),
        ({"data_nascimento": "2999-01-01"}, "não pode estar no futuro"),
        ({"sexo": "Inventado"}, "opção de sexo"),
        ({"treinador_id": "999999"}, "treinador da lista"),
        ({"telefone": "1" * 21}, "Telefone"),
    ],
)
def test_cadastro_invalido_nao_grava(app, admin, campos, erro):
    resposta = admin.post("/admin/alunos/novo", data=_aluno_valido(**campos))
    assert resposta.status_code == 400
    assert erro in resposta.text
    with app.app_context():
        assert _usuario("bruna@fitcontrol.test") is None


def test_erro_mantem_campos_mas_nao_a_senha(admin):
    resposta = admin.post("/admin/alunos/novo", data=_aluno_valido(telefone="1" * 21))
    assert 'value="Bruna Lima"' in resposta.text
    assert "senha-forte" not in resposta.text


def test_lista_mostra_aluno_sem_treinador(admin):
    pagina = admin.get("/admin/alunos").text
    assert "Lucas Ferreira" in pagina
    assert "Sem treinador" in pagina


def test_atribuir_treinador_a_aluno_sem_treinador(app, admin):
    lucas = _aluno_id(app, "lucas@fitcontrol.test")
    ana = _treinador_id(app, "ana@fitcontrol.test")
    resposta = admin.post(
        f"/admin/alunos/{lucas}/treinador", data={"treinador_id": ana}, follow_redirects=True
    )
    assert "Lucas Ferreira agora treina com Ana Ribeiro." in resposta.text
    with app.app_context():
        assert _usuario("lucas@fitcontrol.test").aluno.treinador_id == ana


def test_mudar_de_treinador_transfere_a_gestao_dos_treinos(app, admin, client):
    maria = _aluno_id(app, "maria@fitcontrol.test")
    ana = _treinador_id(app, "ana@fitcontrol.test")
    with app.app_context():
        treino_id = db.session.scalar(db.select(Treino).filter_by(nome="Treino A")).id
    admin.post(
        f"/admin/alunos/{maria}/treinador", data={"treinador_id": ana}, follow_redirects=True
    )

    admin.post("/logout")
    client.post("/login", data={"email": "giuseppe@fitcontrol.test", "senha": "fitcontrol123"})
    assert "Maria Camole" not in client.get("/treinador/").text
    assert client.get(f"/treinador/treinos/{treino_id}/editar").status_code == 404

    client.post("/logout")
    client.post("/login", data={"email": "ana@fitcontrol.test", "senha": "fitcontrol123"})
    assert "Maria Camole" in client.get("/treinador/").text
    assert client.get(f"/treinador/treinos/{treino_id}/editar").status_code == 200


def test_mudar_de_treinador_mantem_o_autor_do_treino(app, admin):
    maria = _aluno_id(app, "maria@fitcontrol.test")
    admin.post(
        f"/admin/alunos/{maria}/treinador",
        data={"treinador_id": _treinador_id(app, "ana@fitcontrol.test")},
    )
    with app.app_context():
        treino = db.session.scalar(db.select(Treino).filter_by(nome="Treino A"))
        assert treino.treinador.usuario.email == "giuseppe@fitcontrol.test"


def test_remover_treinador_deixa_aluno_sem_treinador(app, admin):
    maria = _aluno_id(app, "maria@fitcontrol.test")
    admin.post(f"/admin/alunos/{maria}/treinador", data={"treinador_id": ""})
    with app.app_context():
        assert _usuario("maria@fitcontrol.test").aluno.treinador_id is None


def test_nao_atribui_treinador_inexistente_ou_inativo(app, admin):
    maria = _aluno_id(app, "maria@fitcontrol.test")
    original = _treinador_id(app, "giuseppe@fitcontrol.test")
    with app.app_context():
        _usuario("ana@fitcontrol.test").ativo = False
        inativo = db.session.scalar(
            db.select(Treinador).join(Usuario).filter(Usuario.email == "ana@fitcontrol.test")
        ).id
        db.session.commit()
    for treinador_id in (inativo, 999999, "abc"):
        resposta = admin.post(
            f"/admin/alunos/{maria}/treinador",
            data={"treinador_id": treinador_id},
            follow_redirects=True,
        )
        assert "Escolha um treinador da lista." in resposta.text
    with app.app_context():
        assert _usuario("maria@fitcontrol.test").aluno.treinador_id == original


def test_atribuir_em_aluno_inexistente_retorna_404(admin):
    assert admin.post("/admin/alunos/999999/treinador").status_code == 404


def test_atribuir_nao_aceita_get(app, admin):
    maria = _aluno_id(app, "maria@fitcontrol.test")
    assert admin.get(f"/admin/alunos/{maria}/treinador").status_code == 405


@pytest.mark.parametrize("email", ["giuseppe@fitcontrol.test", "maria@fitcontrol.test"])
@pytest.mark.parametrize(
    "rota", ["/admin/alunos", "/admin/alunos/novo", "/admin/treinadores", "/admin/treinadores/novo"]
)
def test_area_administrativa_e_exclusiva_do_admin(client, entrar, email, rota):
    entrar(email)
    assert client.get(rota).status_code == 403
    if rota.endswith("/novo"):
        assert client.post(rota).status_code == 403


def test_treinador_nao_troca_aluno_de_professor(app, client, entrar):
    maria = _aluno_id(app, "maria@fitcontrol.test")
    entrar("giuseppe@fitcontrol.test")
    resposta = client.post(f"/admin/alunos/{maria}/treinador", data={"treinador_id": ""})
    assert resposta.status_code == 403
    with app.app_context():
        assert _usuario("maria@fitcontrol.test").aluno.treinador_id is not None
