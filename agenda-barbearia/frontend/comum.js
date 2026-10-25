// Funções usadas pelas duas páginas (cliente e barbeiro).

const el = (id) => document.getElementById(id);

const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const formatarPreco = (centavos) => reais.format(centavos / 100);

async function api(caminho, opcoes = {}) {
  let resposta;
  try {
    resposta = await fetch(API_URL + caminho, {
      ...opcoes,
      headers: { "Content-Type": "application/json", ...opcoes.headers },
    });
  } catch {
    throw new Error("Não consegui falar com o servidor. Confira sua internet e tente de novo.");
  }
  const corpo = await resposta.json();
  if (!resposta.ok) {
    const erro = new Error(
      Array.isArray(corpo.detail)
        ? corpo.detail[0].msg.replace("Value error, ", "")
        : corpo.detail || "Algo deu errado.",
    );
    erro.status = resposta.status;
    throw erro;
  }
  return corpo;
}

// "2026-10-27" → Date local (sem o new Date("2026-10-27") que usa UTC e volta um dia)
function dataLocal(iso) {
  const [ano, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(ano, mes - 1, dia);
}

function dataIso(data) {
  return [data.getFullYear(), String(data.getMonth() + 1).padStart(2, "0"), String(data.getDate()).padStart(2, "0")].join("-");
}

const hora = (dataHoraIso) => dataHoraIso.slice(11, 16);

function dataPorExtenso(iso) {
  return dataLocal(iso).toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
}
