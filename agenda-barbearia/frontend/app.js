const escolha = { servico: null, dia: null, hora: null };
let servicos = [];

const CHAVE_MEUS = "barbearia:meus-codigos";

// ---------- Passo 1: serviço ----------

async function carregarServicos() {
  servicos = await api("/servicos");
  const lista = el("servicos");
  lista.replaceChildren(
    ...servicos.map((servico) => {
      const botao = document.createElement("button");
      botao.type = "button";
      botao.className = "servico";
      botao.setAttribute("aria-pressed", "false");
      botao.innerHTML = `<strong></strong><small></small><span class="preco"></span>`;
      botao.querySelector("strong").textContent = servico.nome;
      botao.querySelector("small").textContent = `${servico.minutos} min`;
      botao.querySelector(".preco").textContent = formatarPreco(servico.preco_centavos);
      botao.addEventListener("click", () => {
        marcarSelecionado(lista, botao);
        escolha.servico = servico;
        habilitar("passo-dia");
        // Se já tinha um dia, recarrega: o serviço novo pode ter outra duração
        if (escolha.dia) carregarHorarios();
        atualizarResumo();
      });
      return botao;
    }),
  );
}

// ---------- Passo 2: dia ----------

async function carregarDias() {
  const dias = await api("/dias");
  const lista = el("dias");
  lista.replaceChildren(
    ...dias.map(({ data, aberto }) => {
      const dataObj = dataLocal(data);
      const botao = document.createElement("button");
      botao.type = "button";
      botao.className = "dia";
      botao.disabled = !aberto;
      botao.setAttribute("aria-pressed", "false");
      botao.setAttribute("aria-label", aberto ? dataPorExtenso(data) : `${dataPorExtenso(data)}, fechado`);
      const semana = dataObj.toLocaleDateString("pt-BR", { weekday: "short" }).replace(".", "");
      botao.innerHTML = `<span>${semana}</span><strong>${dataObj.getDate()}</strong><span>${aberto ? dataObj.toLocaleDateString("pt-BR", { month: "short" }).replace(".", "") : "fechado"}</span>`;
      botao.addEventListener("click", () => {
        marcarSelecionado(lista, botao);
        escolha.dia = data;
        carregarHorarios();
      });
      return botao;
    }),
  );
}

// ---------- Passo 3: horário ----------

async function carregarHorarios() {
  escolha.hora = null;
  desabilitar("passo-dados");
  habilitar("passo-horario");
  atualizarResumo();

  const lista = el("horarios");
  const dica = el("dica-horario");
  lista.replaceChildren();
  dica.hidden = false;
  dica.textContent = "Procurando horários livres…";

  try {
    const horarios = await api(`/horarios?data=${escolha.dia}&servico_id=${escolha.servico.id}`);
    dica.textContent = horarios.length ? "" : "Esse dia já está cheio. Tente outro dia.";
    dica.hidden = horarios.length > 0;
    lista.replaceChildren(
      ...horarios.map((h) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "horario";
        botao.textContent = h;
        botao.setAttribute("aria-pressed", "false");
        botao.addEventListener("click", () => {
          marcarSelecionado(lista, botao);
          escolha.hora = h;
          habilitar("passo-dados");
          atualizarResumo();
          el("passo-dados").scrollIntoView({ behavior: "smooth", block: "start" });
        });
        return botao;
      }),
    );
  } catch (erro) {
    dica.textContent = erro.message;
  }
}

// ---------- Passo 4: dados e confirmação ----------

function atualizarResumo() {
  const { servico, dia, hora } = escolha;
  el("resumo").textContent = servico && dia && hora
    ? `${servico.nome} (${servico.minutos} min) · ${dataPorExtenso(dia)} às ${hora} · ${formatarPreco(servico.preco_centavos)}, pago na hora`
    : "";
}

// Máscara simples: (11) 98765-4321
function mascararTelefone(evento) {
  const d = evento.target.value.replace(/\D/g, "").slice(0, 11);
  let texto = d;
  if (d.length > 2) texto = `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length > 6) texto = `(${d.slice(0, 2)}) ${d.slice(2, d.length - 4)}-${d.slice(-4)}`;
  evento.target.value = texto;
}

async function confirmar(evento) {
  evento.preventDefault();
  const form = el("agendamento");
  const erro = el("erro-formulario");
  erro.hidden = true;

  if (form.nome.value.trim().length < 2) return mostrarErro("Escreva seu nome.");
  if (form.telefone.value.replace(/\D/g, "").length < 10) return mostrarErro("Confira o WhatsApp com DDD.");

  const botao = el("confirmar");
  botao.disabled = true;
  botao.textContent = "Confirmando…";
  try {
    const agendamento = await api("/agendamentos", {
      method: "POST",
      body: JSON.stringify({
        nome: form.nome.value,
        telefone: form.telefone.value,
        servico_id: escolha.servico.id,
        data: escolha.dia,
        hora: escolha.hora,
      }),
    });
    guardarCodigo(agendamento.codigo);
    mostrarConfirmacao(agendamento);
  } catch (e) {
    mostrarErro(e.message);
    // Alguém pegou o horário enquanto a pessoa digitava: mostra a lista atualizada
    if (e.status === 409 && e.message.includes("horário")) carregarHorarios();
  } finally {
    botao.disabled = false;
    botao.textContent = "Confirmar horário";
  }

  function mostrarErro(mensagem) {
    erro.textContent = mensagem;
    erro.hidden = false;
  }
}

function mostrarConfirmacao(agendamento) {
  el("agendamento").hidden = true;
  el("confirmado").hidden = false;
  el("confirmado-texto").textContent =
    `${agendamento.servico.nome} · ${dataPorExtenso(agendamento.inicio)} às ${hora(agendamento.inicio)}`;
  el("confirmado-codigo").textContent = agendamento.codigo;
  window.scrollTo({ top: 0, behavior: "smooth" });
  carregarMeus();
}

function recomecar() {
  Object.assign(escolha, { servico: null, dia: null, hora: null });
  el("agendamento").reset();
  document.querySelectorAll("[aria-pressed='true']").forEach((b) => b.setAttribute("aria-pressed", "false"));
  el("horarios").replaceChildren();
  el("dica-horario").hidden = false;
  el("dica-horario").textContent = "Escolha um dia para ver os horários livres.";
  ["passo-dia", "passo-horario", "passo-dados"].forEach(desabilitar);
  el("confirmado").hidden = true;
  el("agendamento").hidden = false;
}

// ---------- Meus horários (códigos guardados neste aparelho) ----------

function lerCodigos() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE_MEUS)) || [];
  } catch {
    return [];
  }
}

function guardarCodigo(codigo) {
  try {
    localStorage.setItem(CHAVE_MEUS, JSON.stringify([...new Set([codigo, ...lerCodigos()])].slice(0, 10)));
  } catch {
    // Navegador sem localStorage (aba anônima): o código aparece na tela mesmo assim
  }
}

async function carregarMeus() {
  const codigos = lerCodigos();
  const resultados = await Promise.allSettled(codigos.map((c) => api(`/agendamentos/${c}`)));
  const agora = new Date();
  const ativos = resultados
    .filter((r) => r.status === "fulfilled")
    .map((r) => r.value)
    .filter((a) => !a.cancelado && new Date(a.inicio) > agora)
    .sort((a, b) => a.inicio.localeCompare(b.inicio));

  const lista = el("meus-lista");
  lista.replaceChildren(
    ...ativos.map((a) => {
      const item = document.createElement("li");
      item.className = "meu";
      item.innerHTML = `<div><strong></strong><small></small></div><button class="botao contorno pequeno" type="button">Cancelar</button>`;
      item.querySelector("strong").textContent = `${dataPorExtenso(a.inicio)} às ${hora(a.inicio)}`;
      item.querySelector("small").textContent = `${a.servico.nome} · código ${a.codigo}`;
      item.querySelector("button").addEventListener("click", () => cancelar(a));
      return item;
    }),
  );
  el("meus").hidden = ativos.length === 0;
}

async function cancelar(agendamento) {
  if (!confirm(`Cancelar ${agendamento.servico.nome} de ${dataPorExtenso(agendamento.inicio)} às ${hora(agendamento.inicio)}?`)) return;
  try {
    await api(`/agendamentos/${agendamento.codigo}/cancelar`, { method: "POST" });
    await carregarMeus();
    if (escolha.dia) carregarHorarios();
  } catch (erro) {
    alert(erro.message);
  }
}

// ---------- Apoio ----------

function marcarSelecionado(lista, escolhido) {
  lista.querySelectorAll("[aria-pressed]").forEach((b) => b.setAttribute("aria-pressed", String(b === escolhido)));
}

function habilitar(id) { el(id).removeAttribute("aria-disabled"); }
function desabilitar(id) { el(id).setAttribute("aria-disabled", "true"); }

async function iniciar() {
  el("agendamento").addEventListener("submit", confirmar);
  el("agendamento").telefone.addEventListener("input", mascararTelefone);
  el("marcar-outro").addEventListener("click", recomecar);
  try {
    await Promise.all([carregarServicos(), carregarDias()]);
    carregarMeus();
  } catch (erro) {
    el("erro-geral").textContent = erro.message;
    el("erro-geral").hidden = false;
  }
}

iniciar();
