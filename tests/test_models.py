from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from fitcontrol.cli import popular_demo
from fitcontrol.extensions import db
from fitcontrol.models import (
    Agendamento,
    Aluno,
    Exercicio,
    MedidaBiometrica,
    Perfil,
    Treino,
    TreinoExercicio,
    Usuario,
)


@pytest.fixture
def contexto(app):
    with app.app_context():
        yield


def _aluno(email="maria@fitcontrol.test"):
    return db.session.scalar(db.select(Usuario).filter_by(email=email)).aluno


def test_senha_nao_fica_em_texto_puro(contexto):
    usuario = Usuario(nome="Teste", email="t@fitcontrol.test", perfil=Perfil.ALUNO)
    usuario.definir_senha("segredo")
    assert "segredo" not in usuario.senha_hash
    assert usuario.verificar_senha("segredo")
    assert not usuario.verificar_senha("outra")


def test_dados_pessoais_e_biometricos_ficam_em_tabelas_separadas(contexto):
    colunas = {
        tabela: {coluna["name"] for coluna in inspect(db.engine).get_columns(tabela)}
        for tabela in ("alunos", "dados_pessoais", "medidas_biometricas")
    }
    assert "data_nascimento" in colunas["dados_pessoais"]
    assert "peso_kg" in colunas["medidas_biometricas"]
    assert not colunas["alunos"] & {"data_nascimento", "telefone", "peso_kg"}


def test_treinador_tem_varios_alunos(contexto):
    maria = _aluno()
    pedro = _aluno("pedro@fitcontrol.test")
    assert maria.treinador is pedro.treinador
    assert len(maria.treinador.alunos) == 2
    assert _aluno("lucas@fitcontrol.test").treinador is None


def test_treino_e_composto_de_exercicios_com_aparelhos_e_grupo(contexto):
    treino = _aluno().treinos[0]
    supino = treino.itens[0].exercicio
    assert [item.ordem for item in treino.itens] == [1, 2, 3, 4]
    assert supino.grupo_muscular.nome == "Peito"
    assert {aparelho.nome for aparelho in supino.aparelhos} == {"Banco reto", "Barra"}


def test_aluno_ve_apenas_os_proprios_treinos(client, entrar):
    entrar("maria@fitcontrol.test")
    segunda = date.today() - timedelta(days=date.today().weekday())
    pagina = client.get(f"/aluno/?dia={segunda.isoformat()}").text
    assert "Treino A" in pagina
    assert "Treino Único" not in pagina


def test_treinador_ve_seus_alunos(client, entrar):
    entrar("giuseppe@fitcontrol.test")
    pagina = client.get("/treinador/").text
    assert "Maria Camole" in pagina
    assert "Pedro Almeida" in pagina


def test_frequencia_conta_dias_distintos_com_sessao_concluida(contexto):
    assert len(_aluno().dias_de_frequencia) == 3
    assert _aluno("pedro@fitcontrol.test").dias_de_frequencia == []


def test_medida_atual_e_a_mais_recente(contexto):
    medida = _aluno().medida_atual
    assert medida.peso_kg == 62.4
    assert medida.imc == 22.9


def test_imc_sem_altura_nao_quebra(contexto):
    assert MedidaBiometrica(peso_kg=70).imc is None


def test_numeros_usam_virgula_na_pagina_do_aluno(client, entrar):
    entrar("maria@fitcontrol.test")
    pagina = client.get("/aluno/").text
    assert "62,4 kg" in pagina
    assert "25,1%" in pagina


def test_avaliacao_incompleta_nao_derruba_a_pagina_do_aluno(app, client, entrar):
    with app.app_context():
        aluno = _aluno("pedro@fitcontrol.test")
        aluno.medidas.append(MedidaBiometrica(data=date.today()))
        db.session.commit()
    entrar("pedro@fitcontrol.test")
    resposta = client.get("/aluno/")
    assert resposta.status_code == 200
    assert "—" in resposta.text


def test_chave_estrangeira_e_aplicada(contexto):
    db.session.add(Treino(nome="Sem aluno", aluno_id=9999))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_email_e_unico(contexto):
    usuario = Usuario(nome="Duplicado", email="maria@fitcontrol.test", perfil=Perfil.ALUNO)
    usuario.definir_senha("x")
    db.session.add(usuario)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_series_precisam_ser_positivas(contexto):
    item = _aluno().treinos[0].itens[0]
    item.series = 0
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_agendamento_precisa_terminar_depois_de_comecar(contexto):
    maria = _aluno()
    agora = datetime.now()
    db.session.add(
        Agendamento(
            treinador=maria.treinador, aluno=maria, inicio=agora, fim=agora - timedelta(hours=1)
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_excluir_exercicio_em_uso_e_bloqueado(contexto):
    exercicio = db.session.scalar(db.select(Exercicio).filter_by(nome="Supino reto"))
    db.session.delete(exercicio)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_excluir_treino_sem_sessoes_remove_seus_itens(contexto):
    treino = _aluno("pedro@fitcontrol.test").treinos[0]
    db.session.delete(treino)
    db.session.commit()
    assert db.session.scalar(
        db.select(db.func.count()).select_from(TreinoExercicio).filter_by(treino_id=treino.id)
    ) == 0


def test_seed_com_reset_recria_os_dados(app):
    runner = app.test_cli_runner()
    assert "já tem dados" in runner.invoke(args=["seed"]).output
    assert "Banco pronto" in runner.invoke(args=["seed", "--reset"]).output
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(Aluno)) == 3
