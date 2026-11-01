from datetime import date, timedelta

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from .auth import perfil_obrigatorio
from .extensions import db
from .models import (
    DIAS_SEMANA,
    Perfil,
    SessaoExercicio,
    SessaoTreino,
    StatusExercicio,
    Treino,
    TreinoExercicio,
)

bp = Blueprint("aluno", __name__, url_prefix="/aluno")


def _ler_data(texto):
    try:
        return date.fromisoformat(texto or "")
    except ValueError:
        return None


def _montar_dia(aluno, data, sessoes):
    """Reúne os treinos previstos para a data, com a marcação de cada exercício."""
    treinos, total, marcados = [], 0, 0
    for treino in aluno.treinos_ativos:
        if not treino.ocorre_em(data):
            continue
        sessao = sessoes.get((treino.id, data))
        marcas = {m.exercicio_id: m.status for m in sessao.exercicios} if sessao else {}
        itens = [(item, marcas.get(item.exercicio_id)) for item in treino.itens]
        total += len(itens)
        marcados += sum(status is not None for _, status in itens)
        treinos.append({"treino": treino, "itens": itens})
    return {
        "data": data,
        "nome": DIAS_SEMANA[data.weekday()],
        "treinos": treinos,
        "total": total,
        "marcados": marcados,
    }


@bp.get("/")
@perfil_obrigatorio(Perfil.ALUNO)
def inicio():
    aluno = current_user.aluno
    hoje = date.today()
    dia = _ler_data(request.args.get("dia")) or hoje
    segunda = dia - timedelta(days=dia.weekday())
    datas = [segunda + timedelta(days=i) for i in range(7)]

    consulta = (
        db.select(SessaoTreino)
        .join(Treino)
        .where(Treino.aluno_id == aluno.id, SessaoTreino.data.between(datas[0], datas[-1]))
    )
    sessoes = {(s.treino_id, s.data): s for s in db.session.scalars(consulta)}
    semana = [_montar_dia(aluno, data, sessoes) for data in datas]

    return render_template(
        "aluno/inicio.html",
        aluno=aluno,
        hoje=hoje,
        semana=semana,
        selecionado=semana[dia.weekday()],
        semana_anterior=dia - timedelta(days=7),
        proxima_semana=dia + timedelta(days=7),
    )


@bp.post("/marcar")
@perfil_obrigatorio(Perfil.ALUNO)
def marcar():
    """Marca o exercício. Repetir a mesma marcação a retira."""
    item_id = request.form.get("item_id", type=int)
    item = db.session.get(TreinoExercicio, item_id) if item_id else None
    if item is None or item.treino.aluno_id != current_user.aluno.id:
        abort(404)

    data = _ler_data(request.form.get("data"))
    try:
        status = StatusExercicio(request.form.get("status"))
    except ValueError:
        abort(400)
    treino = item.treino
    if data is None or data > date.today() or not treino.ocorre_em(data):
        abort(400)

    sessao = db.session.scalar(db.select(SessaoTreino).filter_by(treino_id=treino.id, data=data))
    if sessao is None:
        sessao = SessaoTreino(treino=treino, data=data)
        db.session.add(sessao)

    marca = next((m for m in sessao.exercicios if m.exercicio_id == item.exercicio_id), None)
    if marca is None:
        sessao.exercicios.append(
            SessaoExercicio(exercicio_id=item.exercicio_id, status=status, carga_kg=item.carga_kg)
        )
    elif marca.status == status:
        sessao.exercicios.remove(marca)
    else:
        marca.status = status

    if sessao.exercicios:
        sessao.atualizar_conclusao()
    else:
        db.session.delete(sessao)

    try:
        db.session.commit()
    except IntegrityError:
        # Dois cliques seguidos: a primeira requisição já gravou a marcação.
        db.session.rollback()

    return redirect(url_for("aluno.inicio", dia=data.isoformat(), _anchor=f"item-{item_id}"))
