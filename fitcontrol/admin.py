import re
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .auth import perfil_obrigatorio
from .extensions import db
from .models import (
    Aluno,
    DadosPessoais,
    Exercicio,
    Perfil,
    SessaoTreino,
    Treinador,
    Treino,
    Usuario,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")

EMAIL_VALIDO = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
SENHA_MINIMA = 8
SEXOS = ("Feminino", "Masculino", "Outro", "Prefiro não informar")


def _contar(consulta):
    return db.session.scalar(db.select(db.func.count()).select_from(consulta.subquery()))


def _treinadores_ativos():
    consulta = (
        db.select(Treinador)
        .join(Usuario)
        .where(Usuario.ativo)
        .order_by(Usuario.nome)
    )
    return db.session.scalars(consulta).all()


def _ler_texto(form, campo, rotulo, limite, erros):
    valor = form.get(campo, "").strip()
    if len(valor) > limite:
        erros.append(f"{rotulo}: use até {limite} caracteres.")
    return valor or None


def _ler_conta(form, erros):
    nome = form.get("nome", "").strip()
    email = form.get("email", "").strip().lower()
    senha = form.get("senha", "")

    if not nome or len(nome) > 120:
        erros.append("Informe o nome, com até 120 caracteres.")
    if len(email) > 254 or not EMAIL_VALIDO.fullmatch(email):
        erros.append("Informe um e-mail válido.")
    elif db.session.scalar(db.select(Usuario).filter_by(email=email)):
        erros.append("Já existe uma conta com este e-mail.")
    if len(senha) < SENHA_MINIMA:
        erros.append(f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres.")
    return {"nome": nome, "email": email, "senha": senha}


def _criar_usuario(conta, perfil):
    usuario = Usuario(nome=conta["nome"], email=conta["email"], perfil=perfil)
    usuario.definir_senha(conta["senha"])
    return usuario


def _ler_treinador_id(form, erros):
    """Devolve o id de um treinador ativo, ou None para deixar o aluno sem treinador."""
    valor = form.get("treinador_id", "")
    if not valor:
        return None
    ids_validos = {treinador.id for treinador in _treinadores_ativos()}
    if not valor.isdecimal() or int(valor) not in ids_validos:
        erros.append("Escolha um treinador da lista.")
        return None
    return int(valor)


def _ler_nascimento(form, erros):
    valor = form.get("data_nascimento", "")
    if not valor:
        return None
    try:
        nascimento = date.fromisoformat(valor)
    except ValueError:
        erros.append("Informe uma data de nascimento válida.")
        return None
    if nascimento > date.today():
        erros.append("A data de nascimento não pode estar no futuro.")
    return nascimento


def _mostrar_erros(erros):
    for erro in erros:
        flash(erro, "erro")


@bp.get("/")
@perfil_obrigatorio(Perfil.ADMIN)
def inicio():
    usuarios = db.session.scalars(db.select(Usuario).order_by(Usuario.nome)).all()
    totais = {
        "Treinadores": sum(u.perfil == Perfil.TREINADOR for u in usuarios),
        "Alunos": sum(u.perfil == Perfil.ALUNO for u in usuarios),
        "Exercícios": _contar(db.select(Exercicio).filter_by(ativo=True)),
        "Treinos ativos": _contar(db.select(Treino).filter_by(ativo=True)),
        "Sessões concluídas": _contar(
            db.select(SessaoTreino).where(SessaoTreino.concluida_em.is_not(None))
        ),
    }
    return render_template("admin/inicio.html", usuarios=usuarios, totais=totais)


@bp.get("/alunos")
@perfil_obrigatorio(Perfil.ADMIN)
def alunos():
    consulta = db.select(Aluno).join(Usuario).order_by(Usuario.nome)
    return render_template(
        "admin/alunos.html",
        alunos=db.session.scalars(consulta).all(),
        treinadores=_treinadores_ativos(),
    )


@bp.route("/alunos/novo", methods=["GET", "POST"])
@perfil_obrigatorio(Perfil.ADMIN)
def novo_aluno():
    def formulario(status=200):
        return (
            render_template(
                "admin/aluno_form.html",
                dados=request.form,
                sexos=SEXOS,
                treinadores=_treinadores_ativos(),
            ),
            status,
        )

    if request.method == "GET":
        return formulario()

    form, erros = request.form, []
    conta = _ler_conta(form, erros)
    treinador_id = _ler_treinador_id(form, erros)
    nascimento = _ler_nascimento(form, erros)
    sexo = form.get("sexo") or None
    if sexo is not None and sexo not in SEXOS:
        erros.append("Escolha uma opção de sexo da lista.")
    telefone = _ler_texto(form, "telefone", "Telefone", 20, erros)
    endereco = _ler_texto(form, "endereco", "Endereço", 200, erros)
    contato = _ler_texto(form, "contato_emergencia", "Contato de emergência", 120, erros)

    if erros:
        _mostrar_erros(erros)
        return formulario(400)

    db.session.add(
        Aluno(
            usuario=_criar_usuario(conta, Perfil.ALUNO),
            treinador_id=treinador_id,
            dados_pessoais=DadosPessoais(
                data_nascimento=nascimento,
                sexo=sexo,
                telefone=telefone,
                endereco=endereco,
                contato_emergencia=contato,
            ),
        )
    )
    db.session.commit()
    flash(f"Aluno {conta['nome']} cadastrado.", "sucesso")
    return redirect(url_for("admin.alunos"))


@bp.post("/alunos/<int:aluno_id>/treinador")
@perfil_obrigatorio(Perfil.ADMIN)
def atribuir_treinador(aluno_id):
    """Atribui ou troca o treinador. Os treinos do aluno passam para o novo treinador."""
    aluno = db.session.get(Aluno, aluno_id)
    if aluno is None:
        abort(404)

    erros = []
    treinador_id = _ler_treinador_id(request.form, erros)
    if erros:
        _mostrar_erros(erros)
        return redirect(url_for("admin.alunos"))

    aluno.treinador_id = treinador_id
    db.session.commit()
    if aluno.treinador:
        mensagem = f"{aluno.usuario.nome} agora treina com {aluno.treinador.usuario.nome}."
    else:
        mensagem = f"{aluno.usuario.nome} ficou sem treinador."
    flash(mensagem, "sucesso")
    return redirect(url_for("admin.alunos"))


@bp.get("/treinadores")
@perfil_obrigatorio(Perfil.ADMIN)
def treinadores():
    consulta = db.select(Treinador).join(Usuario).order_by(Usuario.nome)
    return render_template(
        "admin/treinadores.html", treinadores=db.session.scalars(consulta).all()
    )


@bp.route("/treinadores/novo", methods=["GET", "POST"])
@perfil_obrigatorio(Perfil.ADMIN)
def novo_treinador():
    if request.method == "GET":
        return render_template("admin/treinador_form.html", dados={})

    form, erros = request.form, []
    conta = _ler_conta(form, erros)
    cref = _ler_texto(form, "cref", "CREF", 20, erros)
    especialidade = _ler_texto(form, "especialidade", "Especialidade", 120, erros)

    if erros:
        _mostrar_erros(erros)
        return render_template("admin/treinador_form.html", dados=form), 400

    db.session.add(
        Treinador(
            usuario=_criar_usuario(conta, Perfil.TREINADOR),
            cref=cref,
            especialidade=especialidade,
        )
    )
    db.session.commit()
    flash(f"Treinador {conta['nome']} cadastrado.", "sucesso")
    return redirect(url_for("admin.treinadores"))
