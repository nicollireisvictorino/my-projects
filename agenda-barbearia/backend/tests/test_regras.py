from datetime import date, datetime, time

import pytest

from app.regras import SERVICOS, horarios_livres, limpar_telefone, se_sobrepoem

CORTE = SERVICOS[1]          # 30 min
CORTE_E_BARBA = SERVICOS[3]  # 50 min

TERCA = date(2026, 10, 27)
SABADO = date(2026, 10, 31)
DOMINGO = date(2026, 11, 1)
# "Agora" na segunda anterior, para nenhum horário da terça estar no passado
AGORA = datetime(2026, 10, 26, 10, 0)


def h(texto: str) -> time:
    return time.fromisoformat(texto)


def test_dia_fechado_nao_tem_horario():
    assert horarios_livres(DOMINGO, CORTE, [], AGORA) == []


def test_dia_util_respeita_abertura_almoco_e_fechamento():
    livres = horarios_livres(TERCA, CORTE, [], AGORA)

    assert livres[0] == h("09:00")
    assert livres[-1] == h("18:30")  # termina 19:00, quando fecha
    # 11:30 + 30 min = 12:00, pode. 11:45 invade o almoço, não pode.
    assert h("11:30") in livres
    assert h("11:45") not in livres
    assert h("12:30") not in livres
    assert h("13:00") in livres


def test_servico_longo_tem_menos_opcoes_no_fim_do_dia():
    livres = horarios_livres(TERCA, CORTE_E_BARBA, [], AGORA)
    assert livres[-1] == h("18:00")  # 18:00 + 50 min = 18:50
    assert h("11:15") not in livres  # 11:15 + 50 = 12:05, invade o almoço


def test_sabado_sem_almoco():
    livres = horarios_livres(SABADO, CORTE, [], AGORA)
    assert livres[0] == h("08:00")
    assert h("12:00") in livres
    assert livres[-1] == h("13:30")


def test_horario_ocupado_bloqueia_o_que_se_sobrepoe():
    ocupado = [(datetime(2026, 10, 27, 10, 0), datetime(2026, 10, 27, 10, 30))]
    livres = horarios_livres(TERCA, CORTE, ocupado, AGORA)

    assert h("09:30") in livres      # termina 10:00, encosta mas não sobrepõe
    assert h("09:45") not in livres  # termina 10:15
    assert h("10:00") not in livres
    assert h("10:15") not in livres
    assert h("10:30") in livres


def test_hoje_so_mostra_horario_com_antecedencia():
    agora = datetime(2026, 10, 27, 14, 10)
    livres = horarios_livres(TERCA, CORTE, [], agora)
    assert livres[0] == h("14:45")  # 14:40 é o mínimo; o próximo da grade é 14:45


def test_nao_mostra_dia_passado_nem_muito_longe():
    assert horarios_livres(date(2026, 10, 20), CORTE, [], AGORA) == []
    assert horarios_livres(date(2026, 11, 20), CORTE, [], AGORA) == []


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        (("10:00", "10:30"), ("10:30", "11:00"), False),
        (("10:00", "10:30"), ("10:15", "10:45"), True),
        (("10:00", "11:00"), ("10:15", "10:30"), True),
    ],
)
def test_se_sobrepoem(a, b, esperado):
    def dt(t):
        return datetime.combine(TERCA, h(t))

    assert se_sobrepoem(dt(a[0]), dt(a[1]), dt(b[0]), dt(b[1])) is esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("(11) 98765-4321", "11987654321"),
        ("11 3456-7890", "1134567890"),
        ("+55 21 99999-8888", "21999998888"),
    ],
)
def test_limpar_telefone(entrada, esperado):
    assert limpar_telefone(entrada) == esperado


@pytest.mark.parametrize("entrada", ["98765-4321", "123", "(01) 98765-4321", "abc"])
def test_telefone_invalido(entrada):
    with pytest.raises(ValueError):
        limpar_telefone(entrada)
