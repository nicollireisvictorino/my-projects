from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import regras
from app.main import app

TERCA = "2026-10-27"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setenv("SENHA_BARBEIRO", "navalha")
    monkeypatch.setattr(regras, "agora", lambda: datetime(2026, 10, 26, 10, 0))
    with TestClient(app) as c:
        yield c


def agendar(cliente, **campos):
    dados = {"nome": "João", "telefone": "(11) 98765-4321", "servico_id": 1, "data": TERCA, "hora": "10:00"} | campos
    return cliente.post("/agendamentos", json=dados)


def test_lista_servicos_e_dias(cliente):
    assert len(cliente.get("/servicos").json()) == 5

    dias = cliente.get("/dias").json()
    assert dias[0] == {"data": "2026-10-26", "aberto": False}  # segunda
    assert dias[1] == {"data": TERCA, "aberto": True}
    assert len(dias) == 15


def test_agendar_tira_o_horario_da_lista(cliente):
    resposta = agendar(cliente)
    assert resposta.status_code == 201
    agendamento = resposta.json()
    assert len(agendamento["codigo"]) == 6
    assert agendamento["fim"] == "2026-10-27T10:30:00"
    assert "telefone" not in agendamento  # o cliente não precisa ver o telefone de volta

    horarios = cliente.get("/horarios", params={"data": TERCA, "servico_id": 1}).json()
    assert "09:30" in horarios
    assert "10:00" not in horarios
    assert "10:30" in horarios


def test_nao_deixa_marcar_horario_ocupado(cliente):
    agendar(cliente)
    resposta = agendar(cliente, nome="Pedro", telefone="11912345678", hora="10:15")
    assert resposta.status_code == 409


def test_nao_deixa_marcar_fora_do_expediente(cliente):
    assert agendar(cliente, hora="12:15").status_code == 409            # almoço
    assert agendar(cliente, data="2026-11-01").status_code == 409       # domingo
    assert agendar(cliente, hora="10:07").status_code == 409            # fora da grade de 15 min


def test_valida_dados(cliente):
    assert agendar(cliente, telefone="123").status_code == 422
    assert agendar(cliente, nome=" ").status_code == 422
    assert agendar(cliente, servico_id=99).status_code == 404


def test_limite_de_agendamentos_por_telefone(cliente):
    assert agendar(cliente, hora="09:00").status_code == 201
    assert agendar(cliente, hora="10:00").status_code == 201
    terceiro = agendar(cliente, hora="11:00")
    assert terceiro.status_code == 409
    assert "Cancele um" in terceiro.json()["detail"]


def test_cancelar_libera_o_horario(cliente):
    codigo = agendar(cliente).json()["codigo"]

    cancelado = cliente.post(f"/agendamentos/{codigo.lower()}/cancelar").json()
    assert cancelado["cancelado"] is True

    horarios = cliente.get("/horarios", params={"data": TERCA, "servico_id": 1}).json()
    assert "10:00" in horarios
    assert cliente.post("/agendamentos/XXXXXX/cancelar").status_code == 404


def test_nao_cancela_horario_que_ja_passou(cliente, monkeypatch):
    codigo = agendar(cliente).json()["codigo"]
    monkeypatch.setattr(regras, "agora", lambda: datetime(2026, 10, 27, 11, 0))
    assert cliente.post(f"/agendamentos/{codigo}/cancelar").status_code == 409


def test_agenda_do_barbeiro_exige_senha(cliente):
    agendar(cliente)
    agendar(cliente, nome="Pedro", telefone="11912345678", hora="15:00", servico_id=3)

    assert cliente.get("/agenda", params={"data": TERCA}).status_code == 401
    assert cliente.get("/agenda", params={"data": TERCA}, headers={"X-Senha-Barbeiro": "errada"}).status_code == 401

    agenda = cliente.get("/agenda", params={"data": TERCA}, headers={"X-Senha-Barbeiro": "navalha"}).json()
    assert [item["nome"] for item in agenda] == ["João", "Pedro"]
    assert agenda[0]["telefone"] == "11987654321"
    assert agenda[1]["servico"]["nome"] == "Corte + barba"
