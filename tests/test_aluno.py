import re
from datetime import date, timedelta

import pytest

from fitcontrol.extensions import db
from fitcontrol.models import MedidaBiometrica, SessaoTreino, Treino, Usuario

MARIA = "maria@fitcontrol.test"
PEDRO = "pedro@fitcontrol.test"


def _data_prevista(dias_semana, inicio=None, passo=-1):
    """Primeira data, a partir de hoje e no sentido do passo, em um dos dias informados."""
    data = inicio or date.today()
    while data.weekday() not in dias_semana:
        data += timedelta(days=passo)
    return data


def _treino(nome):
    return db.session.scalar(db.select(Treino).filter_by(nome=nome))


def _ids_itens(app, nome):
    with app.app_context():
        return [item.id for item in _treino(nome).itens]


def _sessao(nome, data):
    return db.session.scalar(
        db.select(SessaoTreino).filter_by(treino_id=_treino(nome).id, data=data)
    )


def _status(app, nome, data):
    with app.app_context():
        sessao = _sessao(nome, data)
        return sorted(m.status.value for m in sessao.exercicios) if sessao else []


@pytest.fixture
def maria(client, entrar):
    entrar(MARIA)
    return client


def _marcar(client, item_id, data, status="realizado"):
    return client.post(
        "/aluno/marcar",
        data={"item_id": item_id, "data": data.isoformat(), "status": status},
    )


def test_dia_mostra_exercicios_do_treino_previsto(maria):
    data = _data_prevista({0}, date.today())
    pagina = maria.get(f"/aluno/?dia={data.isoformat()}").text
    assert "Treino A" in pagina
    assert "Supino reto" in pagina
    assert "Banco reto, Barra" in pagina
    assert "Leg press" not in pagina


def test_cada_dia_mostra_seu_proprio_treino(maria):
    segunda = date.today() - timedelta(days=date.today().weekday())
    pagina = maria.get(f"/aluno/?dia={(segunda + timedelta(days=1)).isoformat()}").text
    assert "Treino B" in pagina
    assert "Supino reto" not in pagina


def test_domingo_nao_tem_treino(maria):
    segunda = date.today() - timedelta(days=date.today().weekday())
    domingo = segunda + timedelta(days=6)
    assert "Nenhum treino previsto" in maria.get(f"/aluno/?dia={domingo.isoformat()}").text


def test_data_invalida_cai_em_hoje(maria):
    assert maria.get("/aluno/?dia=nao-e-data").status_code == 200


def test_pagina_mostra_sete_dias_e_navega_entre_semanas(maria):
    pagina = maria.get("/aluno/").text
    assert len(re.findall(r'class="dia[ "]', pagina)) == 7
    anterior = (date.today() - timedelta(days=7)).isoformat()
    assert f"dia={anterior}" in pagina


def test_pagina_mostra_ultima_avaliacao(maria):
    ultima = date.today() - timedelta(days=30)
    pagina = maria.get("/aluno/").text
    assert "Última avaliação física" in pagina
    assert ultima.strftime("%d/%m/%Y") in pagina


def test_aluno_sem_avaliacao_ve_um_traco(client, entrar):
    entrar(PEDRO)
    pagina = client.get("/aluno/").text
    assert "Última avaliação física" in pagina
    assert "Peso" not in pagina


def test_avaliacao_mais_recente_aparece_mesmo_incompleta(app, client, entrar):
    with app.app_context():
        aluno = db.session.scalar(db.select(Usuario).filter_by(email=PEDRO)).aluno
        aluno.medidas.append(MedidaBiometrica(data=date(2026, 3, 9)))
        db.session.commit()
    entrar(PEDRO)
    assert "09/03/2026" in client.get("/aluno/").text


def _data_sem_sessao():
    """Segunda-feira passada, anterior às sessões do seed e prevista no Treino A."""
    return _data_prevista({0}, date.today() - timedelta(days=21))


def test_marcar_realizado_e_nao_realizado(app, maria):
    data = _data_sem_sessao()
    itens = _ids_itens(app, "Treino A")
    _marcar(maria, itens[0], data)
    _marcar(maria, itens[1], data, "nao_realizado")
    assert _status(app, "Treino A", data) == ["nao_realizado", "realizado"]


def test_trocar_a_marca_substitui_a_anterior(app, maria):
    data = _data_sem_sessao()
    item = _ids_itens(app, "Treino A")[0]
    _marcar(maria, item, data)
    _marcar(maria, item, data, "nao_realizado")
    assert _status(app, "Treino A", data) == ["nao_realizado"]


def test_repetir_a_marca_retira_e_apaga_sessao_vazia(app, maria):
    data = _data_sem_sessao()
    item = _ids_itens(app, "Treino A")[0]
    _marcar(maria, item, data)
    _marcar(maria, item, data)
    with app.app_context():
        assert _sessao("Treino A", data) is None


def test_marca_aparece_como_checkbox_marcado(app, maria):
    data = _data_sem_sessao()
    item = _ids_itens(app, "Treino A")[0]
    resposta = _marcar(maria, item, data)
    assert resposta.status_code == 302
    assert f"#item-{item}" in resposta.headers["Location"]
    pagina = maria.get(f"/aluno/?dia={data.isoformat()}").text
    bloco = pagina[pagina.index(f'id="item-{item}"') :]
    assert re.search(r'value="realizado"\s+role="checkbox" aria-checked="true"', bloco)


def test_sessao_conclui_com_tudo_marcado_e_conta_na_frequencia(app, maria):
    data = _data_sem_sessao()
    itens = _ids_itens(app, "Treino A")
    for item in itens[:-1]:
        _marcar(maria, item, data)
    with app.app_context():
        assert _sessao("Treino A", data).concluida_em is None
    _marcar(maria, itens[-1], data, "nao_realizado")
    with app.app_context():
        assert _sessao("Treino A", data).concluida_em is not None
        aluno = db.session.scalar(db.select(Usuario).filter_by(email=MARIA)).aluno
        assert data in aluno.dias_de_frequencia


def test_treino_inteiro_nao_realizado_nao_conta_na_frequencia(app, maria):
    data = _data_sem_sessao()
    for item in _ids_itens(app, "Treino A"):
        _marcar(maria, item, data, "nao_realizado")
    with app.app_context():
        assert _sessao("Treino A", data).concluida_em is None
        aluno = db.session.scalar(db.select(Usuario).filter_by(email=MARIA)).aluno
        assert data not in aluno.dias_de_frequencia


def test_desmarcar_reabre_a_sessao_concluida(app, maria):
    data = _data_sem_sessao()
    itens = _ids_itens(app, "Treino A")
    for item in itens:
        _marcar(maria, item, data)
    _marcar(maria, itens[0], data)
    with app.app_context():
        assert _sessao("Treino A", data).concluida_em is None


def test_nao_marca_dia_futuro(app, maria):
    data = _data_prevista({0}, date.today() + timedelta(days=1), passo=1)
    assert _marcar(maria, _ids_itens(app, "Treino A")[0], data).status_code == 400
    with app.app_context():
        assert _sessao("Treino A", data) is None


def test_dia_futuro_mostra_marcas_desabilitadas(maria):
    data = _data_prevista({0}, date.today() + timedelta(days=1), passo=1)
    pagina = maria.get(f"/aluno/?dia={data.isoformat()}").text
    assert "A marcação abre neste dia." in pagina
    assert re.search(r'aria-checked="false"\s+disabled', pagina)


def test_nao_marca_em_dia_sem_o_treino(app, maria):
    domingo = _data_prevista({6}, date.today())
    assert _marcar(maria, _ids_itens(app, "Treino A")[0], domingo).status_code == 400


def test_nao_marca_antes_da_criacao_do_treino(app, maria):
    data = _data_prevista({0}, date.today() - timedelta(days=120))
    assert _marcar(maria, _ids_itens(app, "Treino A")[0], data).status_code == 400


def test_nao_marca_exercicio_de_outro_aluno(app, maria):
    data = _data_prevista({0}, date.today())
    assert _marcar(maria, _ids_itens(app, "Treino Único")[0], data).status_code == 404
    with app.app_context():
        assert _sessao("Treino Único", data) is None


@pytest.mark.parametrize(
    "dados",
    [
        {},
        {"item_id": "abc", "data": "2026-01-05", "status": "realizado"},
        {"item_id": "999999", "data": "2026-01-05", "status": "realizado"},
    ],
)
def test_marcacao_sem_item_valido_retorna_404(maria, dados):
    assert maria.post("/aluno/marcar", data=dados).status_code == 404


@pytest.mark.parametrize("campo, valor", [("status", "talvez"), ("data", "ontem")])
def test_marcacao_com_valor_invalido_retorna_400(app, maria, campo, valor):
    dados = {
        "item_id": _ids_itens(app, "Treino A")[0],
        "data": _data_prevista({0}).isoformat(),
        "status": "realizado",
        campo: valor,
    }
    assert maria.post("/aluno/marcar", data=dados).status_code == 400


def test_outros_perfis_nao_marcam(app, client, entrar):
    entrar("giuseppe@fitcontrol.test")
    assert _marcar(client, _ids_itens(app, "Treino A")[0], date.today()).status_code == 403


def test_treino_excluido_some_da_semana_mas_a_frequencia_fica(app, maria):
    with app.app_context():
        treino = _treino("Treino A")
        aluno_id = treino.aluno_id
        antes = db.session.get(type(treino.aluno), aluno_id).dias_de_frequencia
        treino.ativo = False
        db.session.commit()
    segunda = date.today() - timedelta(days=date.today().weekday())
    assert "Supino reto" not in maria.get(f"/aluno/?dia={segunda.isoformat()}").text
    with app.app_context():
        aluno = db.session.scalar(db.select(Usuario).filter_by(email=MARIA)).aluno
        assert aluno.dias_de_frequencia == antes
