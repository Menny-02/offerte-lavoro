# Offerte di lavoro per te

Pagina: https://menny-02.github.io/offerte-lavoro/

Ogni mattina (e quando si preme "Cerca nuovi annunci adesso") GitHub Actions esegue `cerca.py`:
raccoglie annunci d'ufficio da LinkedIn, Indeed, ClicLavoro Veneto e Subito, tiene solo la
provincia di Treviso, li valuta con un LLM gratuito (Groq) e pubblica `docs/` su GitHub Pages.

## Configurazione (una volta sola, tutto gratis)

1. **Chiave AI**: crea una API key su https://console.groq.com/keys e salvala come secret del repo
   `LLM_API_KEY` (Settings → Secrets and variables → Actions → New repository secret).
   Per cambiare fornitore basta impostare le *variables* `LLM_BASE_URL` e `LLM_MODEL`
   (es. Gemini: `https://generativelanguage.googleapis.com/v1beta/openai` e `gemini-2.5-flash`).
   Senza chiave il sito funziona lo stesso, con un punteggio a parole chiave.
2. **Bottone "Cerca adesso"**:
   - crea un token *fine-grained* (GitHub → Settings → Developer settings → Fine-grained tokens):
     solo il repo `offerte-lavoro`, permesso **Actions: Read and write**;
   - su https://dash.cloudflare.com crea un Worker, incolla `worker.js`, poi in Settings → Variables:
     `REPO` = `Menny-02/offerte-lavoro`, `PAGES_ORIGIN` = `https://menny-02.github.io`,
     secret `GH_TOKEN` = il token;
   - metti l'indirizzo del Worker nella costante `WORKER` in `docs/index.html`.

## Manutenzione

- Parole cercate: `QUERY` e `QUERY_SUBITO` in `cerca.py`. Profilo usato dall'AI: `PROFILO`.
- Stato delle fonti: in fondo alla pagina ("non raggiungibile" = quel sito ha bloccato la ricerca).
- Test della logica: `python test_cerca.py` (gira anche in ogni esecuzione del workflow).
- GitHub sospende il cron dopo 60 giorni senza attività nel repo: si riattiva da Actions → cerca → Enable.
