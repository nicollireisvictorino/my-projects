// A senha fica só na aba aberta (sessionStorage): fechou a aba, pede de novo.
const CHAVE_SENHA = "barbearia:senha";

function senhaSalva() {
  try { return sessionStorage.getItem(CHAVE_SENHA); } catch { return null; }
}

function salvarSenha(senha) {
  try {
    if (senha) sessionStorage.setItem(CHAVE_SENHA, senha);
    else sessionStorage.removeItem(CHAVE_SENHA);
  } catch {
    // sem sessionStorage, a senha vale só até recarregar a página
  }
  senhaAtual = senha;
}

let senhaAtual = senhaSalva();

async function carregarAgenda() {
  const data = el("data").value;
  el("erro-agenda").hidden = true;
  try {
    const agenda = await api(`/agenda?data=${data}`, { headers: { "X-Senha-Barbeiro": senhaAtual } });
    desenhar(agenda);
  } catch (erro) {
    if (erro.status === 401) {
      salvarSenha(null);
      mostrarLogin("Senha incorreta.");
      return;
    }
    el("erro-agenda").textContent = erro.message;
    el("erro-agenda").hidden = false;
  }
}

function desenhar(agenda) {
  const ativos = agenda.filter((a) => !a.cancelado);
  el("total-clientes").textContent = ativos.length;
  el("total-valor").textContent = formatarPreco(ativos.reduce((soma, a) => soma + a.servico.preco_centavos, 0));
  el("vazio").hidden = agenda.length > 0;

  el("agenda").replaceChildren(
    ...agenda.map((a) => {
      const item = document.createElement("li");
      item.className = `item${a.cancelado ? " cancelado" : ""}`;
      item.innerHTML = `
        <div class="hora"></div>
        <div class="quem"><strong></strong><small></small></div>
        <a class="zap" target="_blank" rel="noopener">WhatsApp</a>`;
      const horaEl = item.querySelector(".hora");
      horaEl.textContent = hora(a.inicio);
      const ate = document.createElement("small");
      ate.textContent = `até ${hora(a.fim)}`;
      horaEl.append(ate);
      item.querySelector(".quem strong").textContent = a.nome;
      item.querySelector(".quem small").textContent = a.cancelado ? `${a.servico.nome} · cancelado` : a.servico.nome;

      const zap = item.querySelector(".zap");
      zap.href = `https://wa.me/55${a.telefone}`;
      zap.setAttribute("aria-label", `Chamar ${a.nome} no WhatsApp`);
      if (a.cancelado) zap.remove();
      return item;
    }),
  );
}

function mudarDia(dias) {
  const data = dataLocal(el("data").value);
  data.setDate(data.getDate() + dias);
  el("data").value = dataIso(data);
  carregarAgenda();
}

function mostrarLogin(mensagem) {
  el("painel").hidden = true;
  el("entrar").hidden = false;
  el("erro-senha").textContent = mensagem || "";
  el("erro-senha").hidden = !mensagem;
  el("entrar").senha.focus();
}

function mostrarPainel() {
  el("entrar").hidden = true;
  el("painel").hidden = false;
  carregarAgenda();
}

el("entrar").addEventListener("submit", (evento) => {
  evento.preventDefault();
  salvarSenha(el("entrar").senha.value);
  el("entrar").reset();
  mostrarPainel();
});
el("sair").addEventListener("click", () => { salvarSenha(null); mostrarLogin(); });
el("dia-anterior").addEventListener("click", () => mudarDia(-1));
el("dia-seguinte").addEventListener("click", () => mudarDia(1));
el("hoje").addEventListener("click", () => { el("data").value = dataIso(new Date()); carregarAgenda(); });
el("data").addEventListener("change", carregarAgenda);

el("data").value = dataIso(new Date());
if (senhaAtual) mostrarPainel();
else mostrarLogin();
