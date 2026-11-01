"""Modelo de dados do FitControl.

Principais relações:
- Usuario 1:1 Treinador | Aluno (o admin só precisa de Usuario).
- Treinador 1:N Aluno.
- Aluno 1:1 DadosPessoais e 1:N MedidaBiometrica (tabelas separadas).
- Treino pertence a um Aluno e foi montado por um Treinador.
- Treino N:N Exercicio, por TreinoExercicio (séries, repetições e carga).
- Treino 1:N TreinoDia: os dias da semana em que o aluno deve fazê-lo.
- SessaoTreino registra um treino em uma data; SessaoExercicio guarda a marcação
  de cada exercício. São a base da evolução e da frequência.
"""

from datetime import date, datetime
from enum import StrEnum

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Column, Enum, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


# Mesma numeração de date.weekday(): segunda é 0.
DIAS_SEMANA = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")


class Perfil(StrEnum):
    ADMIN = "admin"
    TREINADOR = "treinador"
    ALUNO = "aluno"


class StatusAgendamento(StrEnum):
    AGENDADO = "agendado"
    REALIZADO = "realizado"
    CANCELADO = "cancelado"


class StatusExercicio(StrEnum):
    REALIZADO = "realizado"
    NAO_REALIZADO = "nao_realizado"


def _enum(tipo):
    """Guarda o valor do enum como texto, sem tipo nativo no banco."""
    return Enum(
        tipo,
        native_enum=False,
        length=20,
        values_callable=lambda enum: [item.value for item in enum],
    )


exercicio_aparelho = Table(
    "exercicio_aparelho",
    db.metadata,
    Column("exercicio_id", ForeignKey("exercicios.id", ondelete="CASCADE"), primary_key=True),
    Column("aparelho_id", ForeignKey("aparelhos.id", ondelete="RESTRICT"), primary_key=True),
)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(120))
    email: Mapped[str] = mapped_column(db.String(254), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(db.String(255))
    perfil: Mapped[Perfil] = mapped_column(_enum(Perfil))
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(default=datetime.now)

    treinador: Mapped["Treinador | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", uselist=False
    )
    aluno: Mapped["Aluno | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", uselist=False
    )

    @property
    def is_active(self):
        return self.ativo

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


@login_manager.user_loader
def carregar_usuario(usuario_id):
    return db.session.get(Usuario, int(usuario_id))


class Treinador(db.Model):
    __tablename__ = "treinadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    cref: Mapped[str | None] = mapped_column(db.String(20))
    especialidade: Mapped[str | None] = mapped_column(db.String(120))

    usuario: Mapped[Usuario] = relationship(back_populates="treinador")
    alunos: Mapped[list["Aluno"]] = relationship(back_populates="treinador")
    treinos: Mapped[list["Treino"]] = relationship(back_populates="treinador")
    agendamentos: Mapped[list["Agendamento"]] = relationship(
        back_populates="treinador", cascade="all, delete-orphan"
    )


class Aluno(db.Model):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    # Fica vazio se o treinador sair; o admin indica outro depois.
    treinador_id: Mapped[int | None] = mapped_column(
        ForeignKey("treinadores.id", ondelete="SET NULL"), index=True
    )

    usuario: Mapped[Usuario] = relationship(back_populates="aluno")
    treinador: Mapped[Treinador | None] = relationship(back_populates="alunos")
    dados_pessoais: Mapped["DadosPessoais | None"] = relationship(
        back_populates="aluno", cascade="all, delete-orphan", uselist=False
    )
    medidas: Mapped[list["MedidaBiometrica"]] = relationship(
        back_populates="aluno",
        cascade="all, delete-orphan",
        order_by="MedidaBiometrica.data",
    )
    treinos: Mapped[list["Treino"]] = relationship(back_populates="aluno")
    agendamentos: Mapped[list["Agendamento"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )

    @property
    def treinos_ativos(self):
        return [treino for treino in self.treinos if treino.ativo]

    @property
    def medida_atual(self):
        return self.medidas[-1] if self.medidas else None

    @property
    def dias_de_frequencia(self):
        """Dias distintos com treino concluído, do mais recente ao mais antigo."""
        dias = {
            sessao.data
            for treino in self.treinos
            for sessao in treino.sessoes
            if sessao.concluida_em is not None
        }
        return sorted(dias, reverse=True)


class DadosPessoais(db.Model):
    __tablename__ = "dados_pessoais"

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), unique=True
    )
    data_nascimento: Mapped[date | None]
    sexo: Mapped[str | None] = mapped_column(db.String(20))
    telefone: Mapped[str | None] = mapped_column(db.String(20))
    endereco: Mapped[str | None] = mapped_column(db.String(200))
    contato_emergencia: Mapped[str | None] = mapped_column(db.String(120))

    aluno: Mapped[Aluno] = relationship(back_populates="dados_pessoais")


class MedidaBiometrica(db.Model):
    """Cada avaliação física gera uma linha, formando o histórico de evolução."""

    __tablename__ = "medidas_biometricas"
    __table_args__ = (
        CheckConstraint("peso_kg > 0", name="ck_medida_peso_positivo"),
        CheckConstraint("altura_cm > 0", name="ck_medida_altura_positiva"),
        CheckConstraint(
            "percentual_gordura BETWEEN 0 AND 100", name="ck_medida_gordura_valida"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), index=True
    )
    avaliador_id: Mapped[int | None] = mapped_column(
        ForeignKey("treinadores.id", ondelete="SET NULL")
    )
    data: Mapped[date] = mapped_column(default=date.today)
    peso_kg: Mapped[float | None]
    altura_cm: Mapped[float | None]
    percentual_gordura: Mapped[float | None]
    massa_muscular_kg: Mapped[float | None]
    cintura_cm: Mapped[float | None]
    quadril_cm: Mapped[float | None]
    braco_cm: Mapped[float | None]
    coxa_cm: Mapped[float | None]
    observacoes: Mapped[str | None] = mapped_column(db.Text)

    aluno: Mapped[Aluno] = relationship(back_populates="medidas")
    avaliador: Mapped[Treinador | None] = relationship()

    @property
    def imc(self):
        if not self.peso_kg or not self.altura_cm:
            return None
        return round(self.peso_kg / (self.altura_cm / 100) ** 2, 1)


class GrupoMuscular(db.Model):
    __tablename__ = "grupos_musculares"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(60), unique=True)

    exercicios: Mapped[list["Exercicio"]] = relationship(back_populates="grupo_muscular")


class Aparelho(db.Model):
    __tablename__ = "aparelhos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(80), unique=True)

    exercicios: Mapped[list["Exercicio"]] = relationship(
        secondary=exercicio_aparelho, back_populates="aparelhos"
    )


class Exercicio(db.Model):
    """Catálogo compartilhado. Sai de uso com ativo=False para preservar o histórico."""

    __tablename__ = "exercicios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(120), unique=True)
    grupo_muscular_id: Mapped[int] = mapped_column(
        ForeignKey("grupos_musculares.id", ondelete="RESTRICT"), index=True
    )
    nivel: Mapped[str | None] = mapped_column(db.String(20))
    descricao: Mapped[str | None] = mapped_column(db.Text)
    instrucoes: Mapped[str | None] = mapped_column(db.Text)
    ativo: Mapped[bool] = mapped_column(default=True)

    grupo_muscular: Mapped[GrupoMuscular] = relationship(back_populates="exercicios")
    aparelhos: Mapped[list[Aparelho]] = relationship(
        secondary=exercicio_aparelho, back_populates="exercicios"
    )


class Treino(db.Model):
    """Sai de uso com ativo=False, sem apagar as sessões já realizadas."""

    __tablename__ = "treinos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(120))
    objetivo: Mapped[str | None] = mapped_column(db.String(200))
    aluno_id: Mapped[int] = mapped_column(
        ForeignKey("alunos.id", ondelete="RESTRICT"), index=True
    )
    # Autor do treino: não muda se o aluno trocar de treinador.
    treinador_id: Mapped[int | None] = mapped_column(
        ForeignKey("treinadores.id", ondelete="SET NULL"), index=True
    )
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(default=datetime.now)

    aluno: Mapped[Aluno] = relationship(back_populates="treinos")
    treinador: Mapped[Treinador | None] = relationship(back_populates="treinos")
    itens: Mapped[list["TreinoExercicio"]] = relationship(
        back_populates="treino",
        cascade="all, delete-orphan",
        order_by="TreinoExercicio.ordem",
    )
    sessoes: Mapped[list["SessaoTreino"]] = relationship(back_populates="treino")
    dias: Mapped[list["TreinoDia"]] = relationship(
        back_populates="treino",
        cascade="all, delete-orphan",
        order_by="TreinoDia.dia_semana",
    )

    @property
    def dias_semana(self):
        return sorted(dia.dia_semana for dia in self.dias)

    def definir_dias(self, dias_semana):
        atuais = {dia.dia_semana: dia for dia in self.dias}
        self.dias = [
            atuais.get(numero) or TreinoDia(dia_semana=numero)
            for numero in sorted(set(dias_semana))
        ]

    def ocorre_em(self, data):
        """Indica se o aluno deve fazer este treino na data informada."""
        return (
            self.ativo
            and data.weekday() in self.dias_semana
            and self.criado_em.date() <= data
        )


class TreinoDia(db.Model):
    __tablename__ = "treino_dias"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 0 AND 6", name="ck_treino_dia_valido"),
    )

    treino_id: Mapped[int] = mapped_column(
        ForeignKey("treinos.id", ondelete="CASCADE"), primary_key=True
    )
    dia_semana: Mapped[int] = mapped_column(primary_key=True)

    treino: Mapped[Treino] = relationship(back_populates="dias")


class TreinoExercicio(db.Model):
    """Prescrição de um exercício dentro de um treino."""

    __tablename__ = "treino_exercicios"
    __table_args__ = (
        UniqueConstraint("treino_id", "exercicio_id", name="uq_item_exercicio_no_treino"),
        CheckConstraint("series > 0", name="ck_item_series_positivas"),
        CheckConstraint("carga_kg >= 0", name="ck_item_carga_nao_negativa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    treino_id: Mapped[int] = mapped_column(
        ForeignKey("treinos.id", ondelete="CASCADE"), index=True
    )
    exercicio_id: Mapped[int] = mapped_column(
        ForeignKey("exercicios.id", ondelete="RESTRICT"), index=True
    )
    ordem: Mapped[int] = mapped_column(default=1)
    series: Mapped[int] = mapped_column(default=3)
    # Texto para aceitar faixas como "8-12" ou "até a falha".
    repeticoes: Mapped[str] = mapped_column(db.String(20), default="10")
    carga_kg: Mapped[float | None]
    descanso_s: Mapped[int | None]
    observacoes: Mapped[str | None] = mapped_column(db.String(200))

    treino: Mapped[Treino] = relationship(back_populates="itens")
    exercicio: Mapped[Exercicio] = relationship()


class SessaoTreino(db.Model):
    """Registro de um treino em uma data. Só existe depois da primeira marcação."""

    __tablename__ = "sessoes_treino"
    __table_args__ = (UniqueConstraint("treino_id", "data", name="uq_sessao_treino_data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    treino_id: Mapped[int] = mapped_column(
        ForeignKey("treinos.id", ondelete="RESTRICT"), index=True
    )
    # Dia do treino, que pode ser anterior ao momento da marcação.
    data: Mapped[date] = mapped_column(default=date.today)
    iniciada_em: Mapped[datetime] = mapped_column(default=datetime.now)
    concluida_em: Mapped[datetime | None]
    observacoes: Mapped[str | None] = mapped_column(db.Text)

    treino: Mapped[Treino] = relationship(back_populates="sessoes")
    exercicios: Mapped[list["SessaoExercicio"]] = relationship(
        back_populates="sessao", cascade="all, delete-orphan"
    )

    def atualizar_conclusao(self):
        """Conclui com todos os exercícios marcados e ao menos um realizado."""
        marcas = {marca.exercicio_id: marca.status for marca in self.exercicios}
        previstos = [marcas.get(item.exercicio_id) for item in self.treino.itens]
        concluida = None not in previstos and StatusExercicio.REALIZADO in previstos
        if not concluida:
            self.concluida_em = None
        elif self.concluida_em is None:
            self.concluida_em = datetime.now()


class SessaoExercicio(db.Model):
    """Aponta para o exercício, não para o item do treino: o histórico não
    depende de edições posteriores da prescrição."""

    __tablename__ = "sessao_exercicios"
    __table_args__ = (
        UniqueConstraint("sessao_id", "exercicio_id", name="uq_marca_exercicio_na_sessao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sessao_id: Mapped[int] = mapped_column(
        ForeignKey("sessoes_treino.id", ondelete="CASCADE"), index=True
    )
    exercicio_id: Mapped[int] = mapped_column(
        ForeignKey("exercicios.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[StatusExercicio] = mapped_column(_enum(StatusExercicio))
    carga_kg: Mapped[float | None]
    repeticoes: Mapped[int | None]

    sessao: Mapped[SessaoTreino] = relationship(back_populates="exercicios")
    exercicio: Mapped[Exercicio] = relationship()


class Agendamento(db.Model):
    __tablename__ = "agendamentos"
    __table_args__ = (CheckConstraint("fim > inicio", name="ck_agendamento_periodo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    treinador_id: Mapped[int] = mapped_column(
        ForeignKey("treinadores.id", ondelete="CASCADE"), index=True
    )
    aluno_id: Mapped[int] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), index=True
    )
    inicio: Mapped[datetime]
    fim: Mapped[datetime]
    status: Mapped[StatusAgendamento] = mapped_column(
        _enum(StatusAgendamento), default=StatusAgendamento.AGENDADO
    )
    observacoes: Mapped[str | None] = mapped_column(db.String(200))

    treinador: Mapped[Treinador] = relationship(back_populates="agendamentos")
    aluno: Mapped[Aluno] = relationship(back_populates="agendamentos")
