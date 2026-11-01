from datetime import date, datetime, time, timedelta

import click

from .extensions import db
from .models import (
    Agendamento,
    Aluno,
    Aparelho,
    DadosPessoais,
    Exercicio,
    GrupoMuscular,
    MedidaBiometrica,
    Perfil,
    SessaoExercicio,
    SessaoTreino,
    StatusExercicio,
    Treinador,
    Treino,
    TreinoExercicio,
    Usuario,
)

SENHA_DEMO = "fitcontrol123"
DIAS_DE_HISTORICO = 60

# nome: (grupo muscular, aparelhos, nível)
CATALOGO = {
    "Supino reto": ("Peito", ["Banco reto", "Barra"], "Intermediário"),
    "Crucifixo na máquina": ("Peito", ["Peck deck"], "Iniciante"),
    "Puxada frontal": ("Costas", ["Pulley"], "Iniciante"),
    "Remada baixa": ("Costas", ["Pulley"], "Iniciante"),
    "Agachamento livre": ("Pernas", ["Barra", "Rack"], "Intermediário"),
    "Leg press 45°": ("Pernas", ["Leg press"], "Iniciante"),
    "Desenvolvimento": ("Ombros", ["Banco reto", "Halteres"], "Intermediário"),
    "Rosca direta": ("Bíceps", ["Barra"], "Iniciante"),
    "Tríceps na polia": ("Tríceps", ["Pulley"], "Iniciante"),
    "Prancha": ("Abdômen", [], "Iniciante"),
}


def _criar_usuario(nome, email, perfil):
    usuario = Usuario(nome=nome, email=email, perfil=perfil)
    usuario.definir_senha(SENHA_DEMO)
    db.session.add(usuario)
    return usuario


def _criar_catalogo():
    grupos, aparelhos, exercicios = {}, {}, {}
    for nome, (grupo, nomes_aparelhos, nivel) in CATALOGO.items():
        exercicio = Exercicio(
            nome=nome,
            nivel=nivel,
            grupo_muscular=grupos.setdefault(grupo, GrupoMuscular(nome=grupo)),
            aparelhos=[aparelhos.setdefault(a, Aparelho(nome=a)) for a in nomes_aparelhos],
        )
        db.session.add(exercicio)
        exercicios[nome] = exercicio
    return exercicios


def _criar_treino(nome, objetivo, aluno, treinador, dias, itens, exercicios, criado_em):
    treino = Treino(
        nome=nome, objetivo=objetivo, aluno=aluno, treinador=treinador, criado_em=criado_em
    )
    treino.definir_dias(dias)
    for ordem, (exercicio, series, repeticoes, carga) in enumerate(itens, start=1):
        treino.itens.append(
            TreinoExercicio(
                exercicio=exercicios[exercicio],
                ordem=ordem,
                series=series,
                repeticoes=repeticoes,
                carga_kg=carga,
            )
        )
    db.session.add(treino)
    return treino


def _registrar_sessao(treino, data, nao_realizado=None):
    db.session.add(
        SessaoTreino(
            treino=treino,
            data=data,
            iniciada_em=datetime.combine(data, time(18, 10)),
            concluida_em=datetime.combine(data, time(19, 0)),
            exercicios=[
                SessaoExercicio(
                    exercicio=item.exercicio,
                    carga_kg=item.carga_kg,
                    status=StatusExercicio.NAO_REALIZADO
                    if item.exercicio.nome == nao_realizado
                    else StatusExercicio.REALIZADO,
                )
                for item in treino.itens
            ],
        )
    )


def _ultimas_datas(treinos, quantidade, hoje):
    """Últimas datas anteriores a hoje em que algum dos treinos estava previsto."""
    datas = (hoje - timedelta(days=dias) for dias in range(1, DIAS_DE_HISTORICO))
    encontradas = [(data, t) for data in datas for t in treinos if t.ocorre_em(data)]
    return encontradas[:quantidade]


def popular_demo():
    """Cria os dados de demonstração a partir das personas do projeto."""
    _criar_usuario("Roberto Mendes", "admin@fitcontrol.test", Perfil.ADMIN)

    giuseppe = Treinador(
        usuario=_criar_usuario("Giuseppe Gourlami", "giuseppe@fitcontrol.test", Perfil.TREINADOR),
        cref="000000-G/SP",
        especialidade="Hipertrofia",
    )
    ana = Treinador(
        usuario=_criar_usuario("Ana Ribeiro", "ana@fitcontrol.test", Perfil.TREINADOR),
        cref="000001-G/SP",
        especialidade="Condicionamento físico",
    )
    maria = Aluno(
        usuario=_criar_usuario("Maria Camole", "maria@fitcontrol.test", Perfil.ALUNO),
        treinador=giuseppe,
        dados_pessoais=DadosPessoais(data_nascimento=date(2003, 5, 14), sexo="Feminino"),
    )
    pedro = Aluno(
        usuario=_criar_usuario("Pedro Almeida", "pedro@fitcontrol.test", Perfil.ALUNO),
        treinador=giuseppe,
        dados_pessoais=DadosPessoais(data_nascimento=date(1998, 11, 2), sexo="Masculino"),
    )
    # Sem treinador, para demonstrar a atribuição pelo administrador.
    lucas = Aluno(
        usuario=_criar_usuario("Lucas Ferreira", "lucas@fitcontrol.test", Perfil.ALUNO),
        dados_pessoais=DadosPessoais(data_nascimento=date(2000, 8, 21), sexo="Masculino"),
    )
    db.session.add_all([giuseppe, ana, maria, pedro, lucas])

    exercicios = _criar_catalogo()
    agora = datetime.now().replace(second=0, microsecond=0)
    criado_em = agora - timedelta(days=DIAS_DE_HISTORICO)
    treino_a = _criar_treino(
        "Treino A",
        "Superiores",
        maria,
        giuseppe,
        [0, 2, 4],
        [
            ("Supino reto", 3, "10", 20),
            ("Puxada frontal", 3, "10", 30),
            ("Desenvolvimento", 3, "12", 6),
            ("Prancha", 3, "30 s", None),
        ],
        exercicios,
        criado_em,
    )
    treino_b = _criar_treino(
        "Treino B",
        "Inferiores",
        maria,
        giuseppe,
        [1, 3, 5],
        [("Leg press 45°", 4, "8-12", 80), ("Agachamento livre", 3, "10", 25)],
        exercicios,
        criado_em,
    )
    _criar_treino(
        "Treino Único",
        "Condicionamento",
        pedro,
        giuseppe,
        [0, 2, 4],
        [("Remada baixa", 3, "12", 35), ("Rosca direta", 3, "12", 12)],
        exercicios,
        criado_em,
    )

    # O flush aplica os valores padrão, como ativo=True, usados em ocorre_em.
    db.session.flush()

    hoje = date.today()
    for dias_atras, peso, gordura in [(90, 64.0, 27.5), (60, 63.1, 26.2), (30, 62.4, 25.1)]:
        maria.medidas.append(
            MedidaBiometrica(
                data=hoje - timedelta(days=dias_atras),
                peso_kg=peso,
                altura_cm=165,
                percentual_gordura=gordura,
                avaliador=giuseppe,
            )
        )

    for data, treino in _ultimas_datas([treino_a, treino_b], 3, hoje):
        # Um exercício fica como não realizado para a demonstração.
        _registrar_sessao(treino, data, nao_realizado="Prancha")

    inicio = agora.replace(hour=18, minute=0) + timedelta(days=1)
    db.session.add(
        Agendamento(
            treinador=giuseppe,
            aluno=maria,
            inicio=inicio,
            fim=inicio + timedelta(hours=1),
            observacoes="Reavaliação física",
        )
    )
    db.session.commit()


def registrar(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Apaga TODOS os dados antes de popular.")
    def seed(reset):
        """Cria as tabelas e os dados de demonstração."""
        if reset:
            db.drop_all()
        db.create_all()
        if db.session.scalar(db.select(Usuario).limit(1)):
            click.echo("O banco já tem dados. Use --reset para recriar.")
            return
        popular_demo()
        click.echo(f"Banco pronto. Senha de todas as contas de demonstração: {SENHA_DEMO}")
        for usuario in db.session.scalars(db.select(Usuario).order_by(Usuario.id)):
            click.echo(f"  {usuario.perfil.value:<10} {usuario.email}")
