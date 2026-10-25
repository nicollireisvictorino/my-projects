// Endereço da API.
// No computador usa o back-end local; publicado, usa a API hospedada.
// Depois de publicar a API, troque o endereço da segunda linha.
const API_URL = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? "http://127.0.0.1:8000"
  : "https://agenda-barbearia-api.onrender.com";
