"""Regras da agenda: serviços, horário de funcionamento e horários livres.

Tudo aqui é função pura (sem banco), para ficar fácil de testar.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

# De quanto em quanto tempo a agenda oferece um horário de início
INTERVALO = timedelta(minutes=15)
# Não dá para marcar "para agora": precisa de pelo menos 30 min de antecedência
ANTECEDENCIA_MINIMA = timedelta(minutes=30)
DIAS_PARA_FRENTE = 14


@dataclass(frozen=True)
class Servico:
    id: int
    nome: str
    minutos: int
    preco_centavos: int


SERVICOS = {
    1: Servico(1, "Corte", 30, 3500),
    2: Servico(2, "Barba", 20, 2500),
    3: Servico(3, "Corte + barba", 50, 5500),
    4: Servico(4, "Sobrancelha", 10, 1500),
    5: Servico(5, "Pezinho", 10, 1000),
}


@dataclass(frozen=True)
class Expediente:
    abre: time
    fecha: time
    almoco: tuple[time, time] | None = None


# weekday(): segunda = 0 ... domingo = 6. Domingo e segunda a barbearia fecha.
EXPEDIENTE = {
    1: Expediente(time(9), time(19), (time(12), time(13))),
    2: Expediente(time(9), time(19), (time(12), time(13))),
    3: Expediente(time(9), time(19), (time(12), time(13))),
    4: Expediente(time(9), time(20), (time(12), time(13))),
    5: Expediente(time(8), time(14)),
}


def agora() -> datetime:
    """Data e hora de Brasília, sem fuso no objeto (o banco guarda horário local)."""
    return datetime.now(FUSO).replace(tzinfo=None, second=0, microsecond=0)


def esta_aberto(dia: date) -> bool:
    return dia.weekday() in EXPEDIENTE


def se_sobrepoem(inicio_a: datetime, fim_a: datetime, inicio_b: datetime, fim_b: datetime) -> bool:
    # Encostar não é sobrepor: um corte até 10:30 e outro a partir de 10:30 pode.
    return inicio_a < fim_b and inicio_b < fim_a


def horarios_livres(
    dia: date,
    servico: Servico,
    ocupados: list[tuple[datetime, datetime]],
    momento: datetime,
) -> list[time]:
    """Horários em que dá para começar o serviço nesse dia.

    `ocupados` são os agendamentos já marcados (início, fim).
    `momento` é o "agora", recebido de fora para os testes controlarem o relógio.
    """
    expediente = EXPEDIENTE.get(dia.weekday())
    if expediente is None:
        return []
    if dia < momento.date() or dia > momento.date() + timedelta(days=DIAS_PARA_FRENTE):
        return []

    bloqueios = list(ocupados)
    if expediente.almoco:
        bloqueios.append(
            (datetime.combine(dia, expediente.almoco[0]), datetime.combine(dia, expediente.almoco[1]))
        )

    duracao = timedelta(minutes=servico.minutos)
    inicio = datetime.combine(dia, expediente.abre)
    fechamento = datetime.combine(dia, expediente.fecha)
    livres = []

    while inicio + duracao <= fechamento:
        fim = inicio + duracao
        cedo_demais = inicio < momento + ANTECEDENCIA_MINIMA
        ocupado = any(se_sobrepoem(inicio, fim, b_ini, b_fim) for b_ini, b_fim in bloqueios)
        if not cedo_demais and not ocupado:
            livres.append(inicio.time())
        inicio += INTERVALO

    return livres


def proximos_dias(hoje: date) -> list[date]:
    return [hoje + timedelta(days=n) for n in range(DIAS_PARA_FRENTE + 1)]


def limpar_telefone(telefone: str) -> str:
    """Deixa só os números e confere se é um celular/fixo brasileiro com DDD."""
    digitos = re.sub(r"\D", "", telefone)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if len(digitos) not in (10, 11) or digitos[0] == "0":
        raise ValueError("Telefone inválido. Use DDD + número, ex.: (11) 98765-4321.")
    return digitos
