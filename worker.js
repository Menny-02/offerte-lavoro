// Cloudflare Worker: fa partire la ricerca su GitHub Actions senza mettere il token nella pagina.
// Variabili: REPO ("utente/offerte-lavoro"), PAGES_ORIGIN ("https://utente.github.io"). Secret: GH_TOKEN
// (token fine-grained solo su quel repo, permesso "Actions: Read and write").
// GET /stato -> { id, stato: "in_corso" | "pronta", esito }   POST /cerca -> avvia (409 se già in corso)
export default {
  async fetch(req, env) {
    const cors = {
      "Access-Control-Allow-Origin": env.PAGES_ORIGIN,
      "Access-Control-Allow-Methods": "GET, POST",
      "Vary": "Origin",
    };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    const rispondi = (dati, status = 200) => Response.json(dati, { status, headers: cors });

    const gh = (path, init = {}) =>
      fetch(`https://api.github.com/repos/${env.REPO}/actions/workflows/cerca.yml${path}`, {
        ...init,
        headers: {
          Authorization: `Bearer ${env.GH_TOKEN}`,
          Accept: "application/vnd.github+json",
          "User-Agent": "cerca-lavoro-worker",
        },
      });

    const r = await gh("/runs?per_page=1");
    if (!r.ok) return rispondi({ errore: `GitHub ${r.status}` }, 502);
    const ultima = (await r.json()).workflow_runs[0];
    const stato = {
      id: ultima?.id ?? null,
      stato: ultima && ultima.status !== "completed" ? "in_corso" : "pronta",
      esito: ultima?.conclusion ?? null,
    };

    const { pathname } = new URL(req.url);
    if (req.method === "POST" && pathname === "/cerca") {
      // solo la pagina della zia può avviare la ricerca, e una alla volta
      if (req.headers.get("Origin") !== env.PAGES_ORIGIN) return rispondi({ errore: "origine non ammessa" }, 403);
      if (stato.stato === "in_corso") return rispondi(stato, 409);
      const d = await gh("/dispatches", { method: "POST", body: JSON.stringify({ ref: "main" }) });
      return d.ok ? rispondi({ ...stato, avviata: true }) : rispondi({ errore: `GitHub ${d.status}` }, 502);
    }
    if (req.method === "GET" && pathname === "/stato") return rispondi(stato);
    return rispondi({ errore: "non trovato" }, 404);
  },
};
