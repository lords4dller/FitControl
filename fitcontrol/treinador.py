import math
from itertools import zip_longest

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .auth import perfil_obrigatorio
from .extensions import db
from .models import DIAS_SEMANA, Aluno, Exercicio, GrupoMuscular, Perfil, Treino, TreinoExercicio

bp = Blueprint("treinador", __name__, url_prefix="/treinador")

CARGA_MAXIMA_KG = 1000
SERIES_MAXIMAS = 99


def _aluno_do_treinador(aluno_id):
    aluno = db.session.get(Aluno, aluno_id)
    if aluno is None or aluno.treinador_id != current_user.treinador.id:
        abort(404)
    return aluno


def _treino_do_treinador(treino_id):
    treino = db.session.get(Treino, treino_id)
    if treino is None or not treino.ativo:
        abort(404)
    _aluno_do_treinador(treino.aluno_id)
    return treino


def _exercicios_disponiveis(treino=None):
    """Catálogo ativo, mais os exercícios desativados que já estão no treino."""
    ids_atuais = [item.exercicio_id for item in treino.itens] if treino else []
    consulta = (
        db.select(Exercicio)
        .join(GrupoMuscular)
        .where(Exercicio.ativo | Exercicio.id.in_(ids_atuais))
        .order_by(GrupoMuscular.nome, Exercicio.nome)
    )
    return db.session.scalars(consulta).all()


def _ler_carga(texto):
    """Devolve (carga, válida). Carga vazia é aceita, como em exercícios de peso corporal."""
    texto = texto.strip().replace(",", ".")
    if not texto:
        return None, True
    try:
        carga = float(texto)
    except ValueError:
        return None, False
    return carga, math.isfinite(carga) and 0 <= carga <= CARGA_MAXIMA_KG


def _ler_itens(form, ids_permitidos, erros):
    """Lê as linhas de exercícios, ignorando as que não têm exercício escolhido."""
    linhas, itens, vistos = [], [], set()
    campos = zip_longest(
        form.getlist("exercicio_id"),
        form.getlist("series"),
        form.getlist("repeticoes"),
        form.getlist("carga_kg"),
        fillvalue="",
    )
    for exercicio_id, series, repeticoes, carga in campos:
        linhas.append(
            {
                "exercicio_id": exercicio_id,
                "series": series,
                "repeticoes": repeticoes,
                "carga_kg": carga,
            }
        )
        if not exercicio_id:
            continue
        numero = len(itens) + 1
        chave = int(exercicio_id) if exercicio_id.isdecimal() else None
        if chave not in ids_permitidos:
            erros.append(f"Exercício {numero}: escolha um exercício do catálogo.")
            continue
        if chave in vistos:
            erros.append(f"Exercício {numero}: já foi incluído neste treino.")
        vistos.add(chave)
        if not series.isdecimal() or not 1 <= int(series) <= SERIES_MAXIMAS:
            erros.append(f"Exercício {numero}: informe de 1 a {SERIES_MAXIMAS} séries.")
        repeticoes = repeticoes.strip()
        if not repeticoes or len(repeticoes) > 20:
            erros.append(f"Exercício {numero}: informe as repetições, como 10 ou 8-12.")
        carga_kg, carga_valida = _ler_carga(carga)
        if not carga_valida:
            erros.append(f"Exercício {numero}: informe a carga em kg, entre 0 e {CARGA_MAXIMA_KG}.")
        itens.append(
            {
                "exercicio_id": chave,
                "series": series,
                "repeticoes": repeticoes,
                "carga_kg": carga_kg,
            }
        )
    if not itens and not erros:
        erros.append("Inclua pelo menos um exercício.")
    return linhas, itens


def _ler_formulario(form, exercicios):
    erros = []
    nome = form.get("nome", "").strip()
    objetivo = form.get("objetivo", "").strip()
    if not nome or len(nome) > 120:
        erros.append("Informe o nome do treino, com até 120 caracteres.")
    if len(objetivo) > 200:
        erros.append("O objetivo deve ter até 200 caracteres.")

    dias = [int(d) for d in form.getlist("dias") if d.isdecimal() and int(d) < len(DIAS_SEMANA)]
    if not dias:
        erros.append("Escolha pelo menos um dia da semana.")

    linhas, itens = _ler_itens(form, {e.id for e in exercicios}, erros)
    dados = {"nome": nome, "objetivo": objetivo, "dias": dias, "linhas": linhas}
    return dados, itens, erros


def _salvar(treino, dados, itens):
    treino.nome = dados["nome"]
    treino.objetivo = dados["objetivo"] or None
    treino.definir_dias(dados["dias"])

    # Reaproveita as linhas existentes: o histórico e os demais campos continuam válidos.
    atuais = {item.exercicio_id: item for item in treino.itens}
    novos = []
    for ordem, valores in enumerate(itens, start=1):
        item = atuais.get(valores["exercicio_id"]) or TreinoExercicio(
            exercicio_id=valores["exercicio_id"]
        )
        item.ordem = ordem
        item.series = int(valores["series"])
        item.repeticoes = valores["repeticoes"]
        item.carga_kg = valores["carga_kg"]
        novos.append(item)
    treino.itens = novos


def _dados_do_treino(treino):
    return {
        "nome": treino.nome,
        "objetivo": treino.objetivo or "",
        "dias": treino.dias_semana,
        "linhas": [
            {
                "exercicio_id": str(item.exercicio_id),
                "series": item.series,
                "repeticoes": item.repeticoes,
                "carga_kg": "" if item.carga_kg is None else f"{item.carga_kg:g}".replace(".", ","),
            }
            for item in treino.itens
        ],
    }


def _formulario(aluno, exercicios, dados, treino=None, status=200):
    return (
        render_template(
            "treinador/treino_form.html",
            aluno=aluno,
            treino=treino,
            exercicios=exercicios,
            dados=dados,
            dias_semana=DIAS_SEMANA,
        ),
        status,
    )


@bp.get("/")
@perfil_obrigatorio(Perfil.TREINADOR)
def inicio():
    alunos = sorted(current_user.treinador.alunos, key=lambda aluno: aluno.usuario.nome)
    return render_template("treinador/inicio.html", alunos=alunos)


@bp.get("/alunos/<int:aluno_id>/treinos")
@perfil_obrigatorio(Perfil.TREINADOR)
def treinos(aluno_id):
    aluno = _aluno_do_treinador(aluno_id)
    return render_template("treinador/treinos.html", aluno=aluno, dias_semana=DIAS_SEMANA)


@bp.route("/alunos/<int:aluno_id>/treinos/novo", methods=["GET", "POST"])
@perfil_obrigatorio(Perfil.TREINADOR)
def novo_treino(aluno_id):
    aluno = _aluno_do_treinador(aluno_id)
    exercicios = _exercicios_disponiveis()

    if request.method == "GET":
        return _formulario(aluno, exercicios, {"dias": [], "linhas": [{}]})

    dados, itens, erros = _ler_formulario(request.form, exercicios)
    if erros:
        for erro in erros:
            flash(erro, "erro")
        return _formulario(aluno, exercicios, dados, status=400)

    treino = Treino(aluno=aluno, treinador=current_user.treinador)
    _salvar(treino, dados, itens)
    db.session.add(treino)
    db.session.commit()
    flash(f"{treino.nome} criado para {aluno.usuario.nome}.", "sucesso")
    return redirect(url_for("treinador.treinos", aluno_id=aluno.id))


@bp.route("/treinos/<int:treino_id>/editar", methods=["GET", "POST"])
@perfil_obrigatorio(Perfil.TREINADOR)
def editar_treino(treino_id):
    treino = _treino_do_treinador(treino_id)
    exercicios = _exercicios_disponiveis(treino)

    if request.method == "GET":
        return _formulario(treino.aluno, exercicios, _dados_do_treino(treino), treino)

    dados, itens, erros = _ler_formulario(request.form, exercicios)
    if erros:
        for erro in erros:
            flash(erro, "erro")
        return _formulario(treino.aluno, exercicios, dados, treino, status=400)

    _salvar(treino, dados, itens)
    db.session.commit()
    flash(f"{treino.nome} atualizado.", "sucesso")
    return redirect(url_for("treinador.treinos", aluno_id=treino.aluno_id))


@bp.post("/treinos/<int:treino_id>/excluir")
@perfil_obrigatorio(Perfil.TREINADOR)
def excluir_treino(treino_id):
    """Tira o treino de uso. As sessões já feitas continuam na frequência do aluno."""
    treino = _treino_do_treinador(treino_id)
    treino.ativo = False
    db.session.commit()
    flash(f"{treino.nome} excluído.", "sucesso")
    return redirect(url_for("treinador.treinos", aluno_id=treino.aluno_id))
