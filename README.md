# Offerte di lavoro per te

Pagina: https://menny-02.github.io/offerte-lavoro/

Ogni mattina GitHub Actions esegue `cerca.py` (si può lanciare anche a mano: Actions → cerca → Run workflow):
raccoglie annunci d'ufficio da LinkedIn, Indeed, ClicLavoro Veneto e Subito, tiene solo quelli entro
15 km da Treviso (`RAGGIO_KM` in `cerca.py`), li valuta con un LLM gratuito (Groq) e pubblica `docs/` su GitHub Pages.

## Configurazione (una volta sola, tutto gratis)

1. **Chiave AI**: crea una API key su https://console.groq.com/keys e salvala come secret del repo
   `LLM_API_KEY` (Settings → Secrets and variables → Actions → New repository secret).
   Per cambiare fornitore basta impostare le *variables* `LLM_BASE_URL` e `LLM_MODEL`
   (es. Gemini: `https://generativelanguage.googleapis.com/v1beta/openai` e `gemini-2.5-flash`).
   Senza chiave il sito funziona lo stesso, con un punteggio a parole chiave.

## Manutenzione

- Parole cercate: `QUERY` e `QUERY_SUBITO` in `cerca.py`. Profilo usato dall'AI: `PROFILO`.
- Stato delle fonti: in fondo alla pagina ("non raggiungibile" = quel sito ha bloccato la ricerca).
- Test della logica: `python test_cerca.py` (gira anche in ogni esecuzione del workflow).
- GitHub sospende il cron dopo 60 giorni senza attività nel repo: si riattiva da Actions → cerca → Enable.
