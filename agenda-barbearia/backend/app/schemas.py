from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator

from .regras import limpar_telefone


class ServicoSaida(BaseModel):
    id: int
    nome: str
    minutos: int
    preco_centavos: int


class Dia(BaseModel):
    data: date
    aberto: bool


class AgendamentoEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=60, examples=["João"])
    telefone: str = Field(examples=["(11) 98765-4321"])
    servico_id: int
    data: date
    hora: time = Field(examples=["10:30"])

    @field_validator("nome")
    @classmethod
    def arrumar_nome(cls, valor: str) -> str:
        valor = " ".join(valor.split())
        if len(valor) < 2:
            raise ValueError("Escreva seu nome.")
        return valor

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, valor: str) -> str:
        return limpar_telefone(valor)


class Agendamento(BaseModel):
    """O que o próprio cliente vê do agendamento dele."""

    codigo: str
    nome: str
    servico: ServicoSaida
    inicio: datetime
    fim: datetime
    cancelado: bool


class ItemDaAgenda(Agendamento):
    """O que o barbeiro vê: inclui o telefone para poder chamar o cliente."""

    telefone: str
