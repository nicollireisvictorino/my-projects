import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from . import regras
from .db import conexao, criar_tabelas
from .schemas import Agendamento, AgendamentoEntrada, Dia, ItemDaAgenda, ServicoSaida

Banco = Annotated[sqlite3.Connection, Depends(conexao)]

# Para ninguém lotar a agenda com nomes falsos
MAXIMO_AGENDAMENTOS_POR_TELEFONE = 2
# Sem letras e números que confundem (0/O, 1/I/L)
ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


@asynccontextmanager
async def ao_iniciar(_: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(
    title="Agenda da Barbearia",
    description="Agendamento online: o cliente escolhe serviço, dia e horário; o barbeiro vê a agenda do dia.",
    version="1.0.0",
    lifespan=ao_iniciar,
)

origens = os.environ.get("ORIGENS_PERMITIDAS", "http://localhost:5500,http://127.0.0.1:5500")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origens.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Funções de apoio ----------

def servico_ou_404(servico_id: int) -> regras.Servico:
    servico = regras.SERVICOS.get(servico_id)
    if servico is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serviço não encontrado.")
    return servico


def ocupados_no_dia(banco: sqlite3.Connection, dia: date) -> list[tuple[datetime, datetime]]:
    linhas = banco.execute(
        """
        SELECT inicio, fim FROM agendamentos
         WHERE cancelado_em IS NULL AND inicio >= ? AND inicio < ?
        """,
        (dia.isoformat(), (dia + timedelta(days=1)).isoformat()),
    ).fetchall()
    return [(datetime.fromisoformat(l["inicio"]), datetime.fromisoformat(l["fim"])) for l in linhas]


def para_agendamento(linha: sqlite3.Row, com_telefone: bool = False) -> Agendamento:
    servico = regras.SERVICOS[linha["servico_id"]]
    dados = {
        "codigo": linha["codigo"],
        "nome": linha["nome"],
        "servico": ServicoSaida(**servico.__dict__),
        "inicio": linha["inicio"],
        "fim": linha["fim"],
        "cancelado": linha["cancelado_em"] is not None,
    }
    if com_telefone:
        return ItemDaAgenda(**dados, telefone=linha["telefone"])
    return Agendamento(**dados)


def buscar_por_codigo(banco: sqlite3.Connection, codigo: str) -> sqlite3.Row:
    linha = banco.execute(
        "SELECT * FROM agendamentos WHERE codigo = ?", (codigo.upper(),)
    ).fetchone()
    if linha is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agendamento não encontrado. Confira o código.")
    return linha


def exigir_barbeiro(x_senha_barbeiro: Annotated[str | None, Header()] = None) -> None:
    senha = os.environ.get("SENHA_BARBEIRO")
    if not senha:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Defina a variável SENHA_BARBEIRO no servidor.")
    # compare_digest evita descobrir a senha pelo tempo de resposta
    if not x_senha_barbeiro or not secrets.compare_digest(x_senha_barbeiro, senha):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha incorreta.")


# ---------- Rotas do cliente ----------

@app.get("/saude", tags=["Sistema"])
def saude():
    return {"ok": True}


@app.get("/servicos", tags=["Cliente"])
def listar_servicos() -> list[ServicoSaida]:
    return [ServicoSaida(**s.__dict__) for s in regras.SERVICOS.values()]


@app.get("/dias", tags=["Cliente"])
def listar_dias() -> list[Dia]:
    hoje = regras.agora().date()
    return [Dia(data=d, aberto=regras.esta_aberto(d)) for d in regras.proximos_dias(hoje)]


@app.get("/horarios", tags=["Cliente"])
def listar_horarios(data: date, servico_id: int, banco: Banco) -> list[str]:
    servico = servico_ou_404(servico_id)
    livres = regras.horarios_livres(data, servico, ocupados_no_dia(banco, data), regras.agora())
    return [h.strftime("%H:%M") for h in livres]


@app.post("/agendamentos", status_code=status.HTTP_201_CREATED, tags=["Cliente"])
def agendar(dados: AgendamentoEntrada, banco: Banco) -> Agendamento:
    servico = servico_ou_404(dados.servico_id)
    agora = regras.agora()

    # BEGIN IMMEDIATE trava a escrita até o COMMIT. Se duas pessoas tentarem o
    # mesmo horário juntas, a segunda espera e já encontra o horário ocupado.
    banco.execute("BEGIN IMMEDIATE")
    try:
        livres = regras.horarios_livres(dados.data, servico, ocupados_no_dia(banco, dados.data), agora)
        if dados.hora.replace(second=0, microsecond=0) not in livres:
            raise HTTPException(status.HTTP_409_CONFLICT, "Esse horário não está mais disponível. Escolha outro.")

        futuros = banco.execute(
            "SELECT COUNT(*) FROM agendamentos WHERE telefone = ? AND cancelado_em IS NULL AND inicio >= ?",
            (dados.telefone, agora.isoformat()),
        ).fetchone()[0]
        if futuros >= MAXIMO_AGENDAMENTOS_POR_TELEFONE:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Esse telefone já tem {futuros} horários marcados. Cancele um para marcar outro.",
            )

        inicio = datetime.combine(dados.data, dados.hora.replace(second=0, microsecond=0))
        fim = inicio + timedelta(minutes=servico.minutos)
        codigo = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(6))
        banco.execute(
            """
            INSERT INTO agendamentos (codigo, nome, telefone, servico_id, inicio, fim)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (codigo, dados.nome, dados.telefone, servico.id, inicio.isoformat(), fim.isoformat()),
        )
        banco.execute("COMMIT")
    except BaseException:
        banco.execute("ROLLBACK")
        raise

    return para_agendamento(buscar_por_codigo(banco, codigo))


@app.get("/agendamentos/{codigo}", tags=["Cliente"])
def ver_agendamento(codigo: str, banco: Banco) -> Agendamento:
    return para_agendamento(buscar_por_codigo(banco, codigo))


@app.post("/agendamentos/{codigo}/cancelar", tags=["Cliente"])
def cancelar(codigo: str, banco: Banco) -> Agendamento:
    linha = buscar_por_codigo(banco, codigo)
    if linha["cancelado_em"] is None:
        if datetime.fromisoformat(linha["inicio"]) <= regras.agora():
            raise HTTPException(status.HTTP_409_CONFLICT, "Esse horário já passou e não dá mais para cancelar.")
        banco.execute(
            "UPDATE agendamentos SET cancelado_em = ? WHERE id = ?",
            (regras.agora().isoformat(), linha["id"]),
        )
    return para_agendamento(buscar_por_codigo(banco, codigo))


# ---------- Rota do barbeiro ----------

@app.get("/agenda", tags=["Barbeiro"], dependencies=[Depends(exigir_barbeiro)])
def agenda_do_dia(data: date, banco: Banco) -> list[ItemDaAgenda]:
    linhas = banco.execute(
        "SELECT * FROM agendamentos WHERE inicio >= ? AND inicio < ? ORDER BY inicio",
        (data.isoformat(), (data + timedelta(days=1)).isoformat()),
    ).fetchall()
    return [para_agendamento(linha, com_telefone=True) for linha in linhas]
