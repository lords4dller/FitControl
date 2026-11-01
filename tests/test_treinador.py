import pytest
from werkzeug.datastructures import MultiDict

from fitcontrol.extensions import db
from fitcontrol.models import Exercicio, SessaoTreino, Treino, Usuario

GIUSEPPE = "giuseppe@fitcontrol.test"
ANA = "ana@fitcontrol.test"


def _aluno_id(app, email="maria@fitcontrol.test"):
    with app.app_context():
        return db.session.scalar(db.select(Usuario).filter_by(email=email)).aluno.id


def _exercicio_id(app, nome):
    with app.app_context():
        return db.session.scalar(db.select(Exercicio).filter_by(nome=nome)).id


def _treino_id(app, nome):
    with app.app_context():
        return db.session.scalar(db.select(Treino).filter_by(nome=nome)).id


def _formulario(exercicios, nome="Treino C", objetivo="Força", dias=("0", "3")):
    campos = [("nome", nome), ("objetivo", objetivo)]
    campos += [("dias", dia) for dia in dias]
    for exercicio_id, series, repeticoes, carga in exercicios:
        campos += [
            ("exercicio_id", str(exercicio_id)),
            ("series", str(series)),
            ("repeticoes", repeticoes),
            ("carga_kg", carga),
        ]
    return MultiDict(campos)


@pytest.fixture
def giuseppe(client, entrar):
    entrar(GIUSEPPE)
    return client


def test_painel_lista_alunos_com_acesso_aos_treinos(app, giuseppe):
    pagina = giuseppe.get("/treinador/").text
    assert "Maria Camole" in pagina
    assert f"/treinador/alunos/{_aluno_id(app)}/treinos" in pagina


def test_lista_de_treinos_mostra_dias_e_acoes(app, giuseppe):
    pagina = giuseppe.get(f"/treinador/alunos/{_aluno_id(app)}/treinos").text
    assert "Treino A" in pagina
    assert "Seg, Qua, Sex" in pagina
    assert "Editar" in pagina
    assert "Excluir" in pagina
    assert "Novo treino" in pagina


def test_formulario_de_novo_treino_abre(app, giuseppe):
    pagina = giuseppe.get(f"/treinador/alunos/{_aluno_id(app)}/treinos/novo").text
    assert 'name="exercicio_id"' in pagina
    assert "Supino reto" in pagina
    assert 'id="modelo-linha"' in pagina


def test_criar_treino(app, giuseppe):
    aluno_id = _aluno_id(app)
    supino = _exercicio_id(app, "Supino reto")
    prancha = _exercicio_id(app, "Prancha")
    resposta = giuseppe.post(
        f"/treinador/alunos/{aluno_id}/treinos/novo",
        data=_formulario([(supino, 4, "8-12", "22,5"), (prancha, 3, "30 s", "")]),
    )
    assert resposta.status_code == 302
    with app.app_context():
        treino = db.session.scalar(db.select(Treino).filter_by(nome="Treino C"))
        assert treino.aluno_id == aluno_id
        assert treino.treinador.usuario.email == GIUSEPPE
        assert treino.dias_semana == [0, 3]
        assert [i.exercicio.nome for i in treino.itens] == ["Supino reto", "Prancha"]
        assert [i.ordem for i in treino.itens] == [1, 2]
        assert treino.itens[0].carga_kg == 22.5
        assert treino.itens[0].series == 4
        assert treino.itens[1].carga_kg is None


def test_linhas_sem_exercicio_sao_ignoradas(app, giuseppe):
    supino = _exercicio_id(app, "Supino reto")
    resposta = giuseppe.post(
        f"/treinador/alunos/{_aluno_id(app)}/treinos/novo",
        data=_formulario([("", 3, "10", ""), (supino, 3, "10", "20")]),
    )
    assert resposta.status_code == 302
    with app.app_context():
        treino = db.session.scalar(db.select(Treino).filter_by(nome="Treino C"))
        assert len(treino.itens) == 1


@pytest.mark.parametrize(
    "ajuste, erro",
    [
        ({"nome": "  "}, "Informe o nome do treino"),
        ({"dias": ()}, "Escolha pelo menos um dia"),
        ({"dias": ("7", "x")}, "Escolha pelo menos um dia"),
        ({"linhas": [(0, 0, "10", "")]}, "de 1 a 99 séries"),
        ({"linhas": [(0, "x", "10", "")]}, "de 1 a 99 séries"),
        ({"linhas": [(0, 3, " ", "")]}, "informe as repetições"),
        ({"linhas": [(0, 3, "10", "-5")]}, "informe a carga"),
        ({"linhas": [(0, 3, "10", "abc")]}, "informe a carga"),
        ({"linhas": [(0, 3, "10", "nan")]}, "informe a carga"),
        ({"linhas": [(0, 3, "10", "inf")]}, "informe a carga"),
        ({"linhas": [(0, 3, "10", ""), (0, 3, "10", "")]}, "já foi incluído"),
        ({"linhas": [(999999, 3, "10", "")]}, "escolha um exercício do catálogo"),
        ({"linhas": [("abc", 3, "10", "")]}, "escolha um exercício do catálogo"),
        ({"linhas": []}, "Inclua pelo menos um exercício"),
    ],
)
def test_formulario_invalido_nao_grava_e_explica(app, giuseppe, ajuste, erro):
    supino = _exercicio_id(app, "Supino reto")
    linhas = [
        tuple(supino if campo == 0 and i == 0 else campo for i, campo in enumerate(linha))
        for linha in ajuste.get("linhas", [(supino, 3, "10", "20")])
    ]
    dados = _formulario(
        linhas, nome=ajuste.get("nome", "Treino C"), dias=ajuste.get("dias", ("0",))
    )
    resposta = giuseppe.post(f"/treinador/alunos/{_aluno_id(app)}/treinos/novo", data=dados)
    assert resposta.status_code == 400
    assert erro in resposta.text
    with app.app_context():
        assert db.session.scalar(db.select(Treino).filter_by(nome="Treino C")) is None


def test_erro_mantem_o_que_foi_digitado(app, giuseppe):
    supino = _exercicio_id(app, "Supino reto")
    resposta = giuseppe.post(
        f"/treinador/alunos/{_aluno_id(app)}/treinos/novo",
        data=_formulario([(supino, 3, "12", "20")], dias=()),
    )
    assert 'value="Treino C"' in resposta.text
    assert 'value="12"' in resposta.text
    assert f'value="{supino}" selected' in resposta.text


def test_formulario_de_edicao_vem_preenchido(app, giuseppe):
    pagina = giuseppe.get(f"/treinador/treinos/{_treino_id(app, 'Treino A')}/editar").text
    assert 'value="Treino A"' in pagina
    assert f'value="{_exercicio_id(app, "Supino reto")}" selected' in pagina
    assert 'name="dias" value="0" checked' in pagina
    assert 'name="dias" value="1" checked' not in pagina


def test_edicao_mostra_carga_com_virgula(app, giuseppe):
    with app.app_context():
        treino = db.session.scalar(db.select(Treino).filter_by(nome="Treino A"))
        treino.itens[0].carga_kg = 22.5
        treino_id = treino.id
        db.session.commit()
    assert 'value="22,5"' in giuseppe.get(f"/treinador/treinos/{treino_id}/editar").text


def test_editar_treino_altera_remove_e_inclui_exercicios(app, giuseppe):
    treino_id = _treino_id(app, "Treino A")
    supino = _exercicio_id(app, "Supino reto")
    rosca = _exercicio_id(app, "Rosca direta")
    resposta = giuseppe.post(
        f"/treinador/treinos/{treino_id}/editar",
        data=_formulario(
            [(rosca, 3, "12", "10"), (supino, 5, "5", "40")], nome="Treino A2", dias=("1",)
        ),
    )
    assert resposta.status_code == 302
    with app.app_context():
        treino = db.session.get(Treino, treino_id)
        assert treino.nome == "Treino A2"
        assert treino.dias_semana == [1]
        assert [i.exercicio.nome for i in treino.itens] == ["Rosca direta", "Supino reto"]
        assert treino.itens[1].series == 5
        assert treino.itens[1].carga_kg == 40


def test_excluir_treino_tira_de_uso_e_preserva_sessoes(app, giuseppe):
    treino_id = _treino_id(app, "Treino A")
    with app.app_context():
        sessoes = len(db.session.get(Treino, treino_id).sessoes)
    assert sessoes > 0
    resposta = giuseppe.post(f"/treinador/treinos/{treino_id}/excluir")
    assert resposta.status_code == 302
    pagina = giuseppe.get(f"/treinador/alunos/{_aluno_id(app)}/treinos").text
    assert "Treino A" not in pagina.replace("Treino A excluído", "")
    with app.app_context():
        assert db.session.get(Treino, treino_id).ativo is False
        contagem = db.session.scalar(
            db.select(db.func.count()).select_from(SessaoTreino).filter_by(treino_id=treino_id)
        )
        assert contagem == sessoes
    assert giuseppe.get(f"/treinador/treinos/{treino_id}/editar").status_code == 404


def test_excluir_nao_aceita_get(app, giuseppe):
    assert giuseppe.get(f"/treinador/treinos/{_treino_id(app, 'Treino A')}/excluir").status_code == 405


def test_treinador_nao_acessa_aluno_de_outro(app, client, entrar):
    entrar(ANA)
    aluno_id = _aluno_id(app)
    treino_id = _treino_id(app, "Treino A")
    assert client.get(f"/treinador/alunos/{aluno_id}/treinos").status_code == 404
    assert client.get(f"/treinador/alunos/{aluno_id}/treinos/novo").status_code == 404
    assert client.post(f"/treinador/alunos/{aluno_id}/treinos/novo").status_code == 404
    assert client.get(f"/treinador/treinos/{treino_id}/editar").status_code == 404
    assert client.post(f"/treinador/treinos/{treino_id}/editar").status_code == 404
    assert client.post(f"/treinador/treinos/{treino_id}/excluir").status_code == 404
    with app.app_context():
        assert db.session.get(Treino, treino_id).ativo is True


def test_aluno_nao_acessa_gestao_de_treinos(app, client, entrar):
    entrar("maria@fitcontrol.test")
    assert client.get(f"/treinador/alunos/{_aluno_id(app)}/treinos").status_code == 403
    treino_id = _treino_id(app, "Treino A")
    assert client.post(f"/treinador/treinos/{treino_id}/excluir").status_code == 403


def test_exercicio_desativado_some_do_novo_mas_fica_no_treino_existente(app, giuseppe):
    with app.app_context():
        db.session.scalar(db.select(Exercicio).filter_by(nome="Supino reto")).ativo = False
        db.session.commit()
    novo = giuseppe.get(f"/treinador/alunos/{_aluno_id(app)}/treinos/novo").text
    assert "Supino reto" not in novo
    edicao = giuseppe.get(f"/treinador/treinos/{_treino_id(app, 'Treino A')}/editar").text
    assert "Supino reto" in edicao
