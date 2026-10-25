# Agenda da Barbearia

![Testes](https://github.com/gusttavoraul/agenda-barbearia/actions/workflows/testes.yml/badge.svg)

Sistema de agendamento online para uma barbearia pequena. O cliente escolhe o serviço, o dia e o horário
pelo celular; o barbeiro abre a agenda do dia e chama o cliente no WhatsApp com um toque.

Muita barbearia ainda marca horário por mensagem, e o barbeiro para o corte para responder.
Quis resolver isso com uma tela simples, que funciona bem no celular.

| Cliente | Barbeiro |
| --- | --- |
| ![Tela do cliente](docs/cliente.png) | ![Agenda do barbeiro](docs/barbeiro.png) |

## O que dá para fazer

**Cliente**
- Escolher o serviço (cada um tem duração e preço)
- Ver só os dias em que a barbearia abre e só os horários que cabem o serviço inteiro
- Confirmar com nome e WhatsApp e receber um código
- Ver e cancelar os próprios horários ("Meus horários", salvo no aparelho)

**Barbeiro** (`/barbeiro.html`, com senha)
- Ver a agenda de qualquer dia, com horário de início e fim
- Total de clientes e valor previsto do dia
- Botão para chamar o cliente no WhatsApp

## Regras da agenda

- Ter a sex das 9h às 19h (qui até 20h), almoço das 12h às 13h; sábado das 8h às 14h; domingo e segunda fechado
- Horários de início de 15 em 15 minutos
- Um serviço só aparece num horário se **couber inteiro** antes do almoço ou do fechamento
  (às 11:30 cabe um corte de 30 min, mas não um corte + barba de 50 min)
- Pelo menos 30 minutos de antecedência e no máximo 14 dias para frente
- No máximo 2 horários futuros por telefone, para ninguém lotar a agenda
- Não dá para cancelar um horário que já passou

## Tecnologias

- **Back-end:** Python, FastAPI e SQLite
- **Front-end:** HTML, CSS e JavaScript puro
- **Testes:** pytest (regras e API), rodando no GitHub Actions a cada push

## Decisões que tomei

- **Dois clientes no mesmo horário.** Se duas pessoas confirmam o mesmo horário quase juntas, só uma pode
  ganhar. Por isso a gravação usa `BEGIN IMMEDIATE`: o SQLite trava a escrita, a segunda pessoa espera e,
  quando chega a vez dela, o horário já aparece ocupado e a API responde `409`. A tela então recarrega os horários livres.
- **Regras sem banco.** O cálculo dos horários livres fica em `backend/app/regras.py` e recebe o "agora"
  como parâmetro. Assim os testes controlam o relógio e não quebram dependendo do dia em que rodam.
- **Privacidade.** A rota pública nunca devolve nome ou telefone de outros clientes, só os horários livres.
  Os dados de quem marcou só aparecem na agenda do barbeiro, que exige senha (comparada com
  `secrets.compare_digest`).
- **Código sem letras que confundem.** O código do agendamento não usa 0/O nem 1/I/L.
- **Fuso horário.** Tudo é calculado no horário de Brasília (`America/Sao_Paulo`), não no do servidor.

## Como rodar no seu computador

Você precisa do Python 3.11 ou mais novo.

```bash
# 1. API
cd backend
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
export SENHA_BARBEIRO=uma-senha  # no Windows: set SENHA_BARBEIRO=uma-senha
uvicorn app.main:app --reload
```

Documentação interativa da API: http://127.0.0.1:8000/docs

```bash
# 2. Site (em outro terminal)
cd frontend
python -m http.server 5500
```

Abra http://localhost:5500 (cliente) e http://localhost:5500/barbeiro.html (barbeiro).

```bash
# Testes
cd backend
pytest -v
```

## Rotas da API

| Método | Rota | O que faz |
| --- | --- | --- |
| GET | `/servicos` | Serviços com duração e preço |
| GET | `/dias` | Próximos 14 dias e se a barbearia abre |
| GET | `/horarios?data=2026-10-27&servico_id=1` | Horários livres para o serviço nesse dia |
| POST | `/agendamentos` | Marca um horário (devolve o código) |
| GET | `/agendamentos/{codigo}` | Consulta um agendamento |
| POST | `/agendamentos/{codigo}/cancelar` | Cancela |
| GET | `/agenda?data=2026-10-27` | Agenda do dia (cabeçalho `X-Senha-Barbeiro`) |

## Próximos passos

- Mais de um barbeiro, cada um com a própria agenda
- Lembrete automático no WhatsApp no dia anterior
- Login de verdade para o barbeiro, no lugar da senha única
