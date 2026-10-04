"""Raccoglie annunci d'ufficio entro RAGGIO_KM da Treviso, li valuta con un LLM gratuito
e scrive docs/annunci.json per la pagina. Uso: python cerca.py
Env opzionali: LLM_API_KEY (senza, punteggio a parole chiave), LLM_BASE_URL, LLM_MODEL."""
import html
import json
import math
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from curl_cffi import requests

QUI = Path(__file__).parent
FILE_DATI = QUI / "docs" / "annunci.json"
GIORNI = 30  # annunci pubblicati da più di così spariscono
CENTRO = (45.6658, 12.2456)  # Treviso
RAGGIO_KM = 15  # annunci più lontani di così dal centro di Treviso spariscono
WEB = requests.Session(impersonate="chrome")  # finge Chrome: Subito blocca i client Python normali

# LinkedIn e Indeed accettano OR: poche ricerche = meno rischio di blocco
QUERY = [
    '"inserimento ordini" OR "gestione ordini" OR "order entry" OR "ufficio ordini"',
    '"ufficio acquisti" OR "addetta acquisti" OR "addetto acquisti" OR "assistente acquisti"',
    '"back office" OR "front office" OR "customer service" OR "servizio clienti" OR "customer care"',
    '"impiegata commerciale" OR "impiegato commerciale" OR "assistente commerciale" OR "ufficio vendite"',
    '"impiegata amministrativa" OR "segreteria" OR "ufficio spedizioni" OR "receptionist"',
]
QUERY_SUBITO = ["impiegata", "ufficio", "back office", "segreteria", "commerciale", "acquisti", "ordini", "clienti"]

# Titoli da ufficio (filtra ClicLavoro, che restituisce tutte le offerte della provincia)
UFFICIO = re.compile(r"impiegat|ufficio|office|segretar|segreteri|contabil|amministrativ|acquist|approvvigion|"
                     r"\bordin|client|customer|commercial|vendit|spedizion|logistic|sportell|accoglienza|"
                     r"immissione|data entry|affari generali|reception|centralin|call center", re.I)
CENTRALI = re.compile(r"\bordin|acquist|back.?office|front.?office|customer|client|commercial|segreteri|"
                      r"impiegat|amministrativ", re.I)
PROTETTE = re.compile(r"68\s*/\s*(19)?99|categori[ae] protett|collocamento mirato", re.I)

PROFILO = """Impiegata commerciale con oltre 35 anni di esperienza in aziende della provincia di Treviso.
Competenze: inserimento e gestione ordini su gestionale, programmazione forniture e spedizioni, ufficio acquisti
e approvvigionamento materie prime, gestione clienti e customer service, front office e back office,
segreteria commerciale e supporto alla rete vendita, gestione appuntamenti, qualità ISO 9001,
contabilità di base (diploma di ragioneria). Strumenti: Word, Excel, software gestione ordini, posta elettronica.
Lingue: italiano madrelingua, inglese base (A1). Patente B, automunita. Disponibile part time o full time.
Cerca: front/back office, servizio clienti, inserimento ordini su gestionale, ufficio acquisti."""

ISTRUZIONI = f"""Sei un consulente del lavoro. Valuta quanto ogni annuncio è adatto a questa candidata.
PROFILO:
{PROFILO}

Punteggio da 0 a 100:
- 80-100: lavoro d'ufficio che corrisponde direttamente (inserimento/gestione ordini, ufficio acquisti,
  servizio clienti, front/back office, impiegata commerciale interna).
- 60-79: lavoro d'ufficio affine (amministrazione, segreteria, spedizioni/logistica d'ufficio, receptionist).
- 40-59: corrispondenza parziale.
- 0-39: non è un lavoro d'ufficio (operaio, magazzino, commessa, agente di vendita esterno, autista,
  cameriere) oppure richiede laurea o competenze tecniche specialistiche.
- Apprendistato (riservato ai giovani): massimo 20. Stage o tirocinio: massimo 50.
- Inglese buono o fluente obbligatorio: togli 20 punti (lei ha inglese base).
"motivo": una frase di massimo 20 parole, in italiano semplice, rivolta a lei con il "tu"
(es. "Cercano chi gestisca ordini e clienti: è proprio la tua esperienza.").
"richiede_inglese": true solo se l'inglese buono o fluente è richiesto (non se "gradito" o "base").
Rispondi SOLO con JSON: {{"risultati":[{{"id":"0","punteggio":0,"motivo":"...","richiede_inglese":false}}]}}"""


# ---------- logica pura (coperta da test_cerca.py) ----------

def norm(s):
    # toglie solo gli accenti; il resto (anche l'apostrofo curvo ’) diventa spazio
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def primo(luogo):
    """'Castelfranco Veneto (TV), Veneto' -> 'castelfranco veneto'"""
    return norm(re.sub(r"\(.*?\)", "", (luogo or "").split(",")[0]))


def carica_comuni():
    """nome normalizzato -> km in linea d'aria dal centro di Treviso"""
    km = {}
    for riga in (QUI / "comuni.txt").read_text(encoding="utf-8").splitlines():
        nome, lat, lon = riga.rsplit(";", 2)
        dx = (float(lon) - CENTRO[1]) * math.cos(math.radians(CENTRO[0]))
        km[norm(nome)] = math.hypot(float(lat) - CENTRO[0], dx) * 111.2
    return km


def vicino(luogo, testo, km):
    p = primo(luogo)
    if p in km:  # comune noto: conta solo la distanza, il testo no
        return km[p] <= RAGGIO_KM
    # frazione, "Veneto", "Greater Treviso Metropolitan Area"...: vale se il testo nomina un comune vicino
    # ponytail: basta un nome nel testo (anche "paese" parola comune, o la sede dell'agenzia a Treviso)
    t = " " + norm(testo).replace("provincia di treviso", "") + " "
    return any(f" {n} " in t for n, d in km.items() if d <= RAGGIO_KM)


def chiave(a):
    if not a.get("azienda"):  # titoli generici senza azienda (es. Centri per l'Impiego): vale il link
        return a["url"]
    return "|".join(norm(x).replace(" ", "") for x in (a["titolo"], a["azienda"], primo(a.get("luogo"))))


def unisci(vecchi, nuovi, oggi):
    tutti = {a["id"]: a for a in vecchi}
    for a in nuovi:
        k = chiave(a)
        if k not in tutti:
            tutti[k] = dict(a, id=k, prima_vista=oggi.isoformat())
    limite = (oggi - timedelta(days=GIORNI)).isoformat()
    return [a for a in tutti.values() if (a.get("data") or a["prima_vista"]) >= limite]


def parse_llm(testo):
    try:
        out = {}
        for r in json.loads(re.search(r"\{.*\}", testo, re.S).group(0))["risultati"]:
            out[str(r["id"])] = {"punteggio": max(0, min(100, int(r["punteggio"]))),
                                 "motivo": str(r.get("motivo") or "")[:200],
                                 "richiede_inglese": bool(r.get("richiede_inglese"))}
        return out
    except (AttributeError, KeyError, TypeError, ValueError):
        return {}


def punteggio_parole(a):
    return 50 if CENTRALI.search(a.get("titolo", "")) else 25


def flag_protette(a):
    return bool(PROTETTE.search(a.get("titolo", "") + " " + (a.get("testo") or "")))


# ---------- fonti ----------

def testo_da_html(s):
    s = re.sub(r"<(script|style).*?</\1>", " ", s, flags=re.S)
    s = re.sub(r"<(br|/p|/li|/div|/h\d)[^>]*>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def da_jobspy(sito):
    from jobspy import scrape_jobs  # import lento, solo quando serve
    out = []
    for q in QUERY:
        # distance in miglia: 10 = 16 km, appena oltre RAGGIO_KM
        df = scrape_jobs(site_name=[sito], search_term=q, distance=10, results_wanted=60, hours_old=168,
                         location="Treviso, Veneto" if sito == "indeed" else "Treviso, Veneto, Italia",
                         country_indeed="italy", description_format="markdown")
        for r in df.fillna("").to_dict("records"):
            out.append({"titolo": r["title"], "azienda": r["company"], "luogo": r["location"],
                        "url": r["job_url"], "data": str(r["date_posted"])[:10],
                        "fonte": "LinkedIn" if sito == "linkedin" else "Indeed",
                        "testo": str(r["description"])[:1500]})
        time.sleep(3)
    return out


def dettaglio_linkedin(url):
    id_ = re.search(r"(\d+)/?$", url).group(1)
    r = WEB.get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id_}", timeout=30)
    r.raise_for_status()
    m = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", r.text, re.S)
    return testo_da_html(m.group(1)) if m else ""


CLIC = "https://cpi-lavoratore.cliclavoroveneto.it"


def da_clic():
    out = []
    for offset in range(0, 1200, 12):  # 12 per pagina, prov=26 è Treviso
        r = WEB.get(f"{CLIC}/cpi/ricercaOfferte/index", timeout=30,
                    params={"q": "", "prov": 26, "offset": offset, "max": 12})
        r.raise_for_status()
        schede = re.findall(r'href="(/cpi/ricercaOfferte/show/\d+)[^"]*".*?class="titolo">(.*?)</span>'
                            r'.*?class="area">(.*?)</div>.*?Pubblicato il:\s*(\d\d)/(\d\d)/(\d{4})', r.text, re.S)
        if not schede:
            break
        for path, titolo, area, g, m, a in schede:
            titolo = html.unescape(titolo).strip()
            if UFFICIO.search(titolo):
                out.append({"titolo": titolo.capitalize(), "azienda": "", "luogo": " ".join(html.unescape(area).split()),
                            "url": CLIC + path, "data": f"{a}-{m}-{g}", "fonte": "ClicLavoro Veneto", "testo": ""})
        time.sleep(1)
    return out


def dettaglio_clic(url):
    r = WEB.get(url, timeout=30)
    r.raise_for_status()
    t = testo_da_html(r.text)
    inizio = t.find("Descrizione qualifica")
    return t[inizio:t.find("Indietro", inizio)].strip() if inizio >= 0 else ""


def da_subito():
    out = []
    for q in QUERY_SUBITO:
        r = WEB.get("https://www.subito.it/annunci-veneto/vendita/offerte-lavoro/treviso/",
                    params={"q": q}, timeout=30)
        r.raise_for_status()
        dati = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S).group(1))
        for it in dati["props"]["pageProps"]["initialState"]["items"]["originalList"]:
            geo = it.get("geo") or {}
            if not it.get("subject") or (geo.get("city") or {}).get("shortName") != "TV":
                continue
            out.append({"titolo": it["subject"], "azienda": "", "luogo": geo["town"]["value"] + " (TV)",
                        "url": it["urls"]["default"], "data": it["date"][:10], "fonte": "Subito",
                        "testo": (it.get("body") or "")[:1500]})
        time.sleep(2)
    return out


FONTI = {"LinkedIn": lambda: da_jobspy("linkedin"), "Indeed": lambda: da_jobspy("indeed"),
         "ClicLavoro Veneto": da_clic, "Subito": da_subito}
DETTAGLIO = {"LinkedIn": dettaglio_linkedin, "ClicLavoro Veneto": dettaglio_clic}


# ---------- valutazione AI ----------

def valuta(annunci):
    key = os.environ.get("LLM_API_KEY")
    if not key:
        print("LLM: nessuna chiave, uso le parole chiave")
        return
    # "or": nel workflow le variabili non impostate arrivano come stringa vuota
    url = (os.environ.get("LLM_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/") + "/chat/completions"
    model = os.environ.get("LLM_MODEL") or "openai/gpt-oss-120b"
    fine = time.time() + 8 * 60  # ponytail: tetto di tempo, il resto viene valutato al giro dopo
    da_fare = [a for a in annunci if not a.get("punteggio_ai")]
    for i in range(0, len(da_fare), 10):
        if time.time() > fine:
            print("LLM: tempo finito, il resto alla prossima ricerca")
            return
        lotto = da_fare[i:i + 10]
        messaggio = "\n---\n".join(
            f"id: {n}\nTitolo: {a['titolo']}\nAzienda: {a.get('azienda') or '-'}\nLuogo: {a['luogo']}\n"
            f"Testo: {(a.get('testo') or '')[:600]}" for n, a in enumerate(lotto))
        for _ in range(4):  # 429 = limite al minuto del piano gratuito: si aspetta e si riprova
            r = WEB.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=90, json={
                "model": model, "temperature": 0.2, "reasoning_effort": "low",
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": ISTRUZIONI}, {"role": "user", "content": messaggio}]})
            if r.status_code != 429:
                break
            time.sleep(min(60, float(r.headers.get("retry-after", 20))))
        if r.status_code != 200:
            print("LLM errore", r.status_code, r.text[:200])
            return
        voti = parse_llm(r.json()["choices"][0]["message"]["content"])
        for n, a in enumerate(lotto):
            if str(n) in voti:
                a.update(voti[str(n)], punteggio_ai=True)
        time.sleep(3)


def main():
    oggi = date.today()
    km = carica_comuni()
    stato = json.loads(FILE_DATI.read_text(encoding="utf-8")) if FILE_DATI.exists() else {"annunci": []}
    noti = {a["url"] for a in stato["annunci"]}

    raccolti, fonti = [], {}
    for nome, prendi in FONTI.items():
        try:
            trovati = prendi()
            fonti[nome] = f"ok {len(trovati)}"
            raccolti += trovati
        except Exception as e:  # una fonte rotta non ferma le altre
            fonti[nome] = f"errore: {str(e)[:80]}"
        print(nome, fonti[nome], flush=True)
    if not raccolti:
        sys.exit("Nessun annuncio da nessuna fonte: lascio intatti i dati vecchi")

    nuovi = {}
    for a in raccolti:
        if a["url"] not in noti:
            nuovi.setdefault(a["url"], a)
    for a in nuovi.values():
        if not a["testo"] and a["fonte"] in DETTAGLIO and km.get(primo(a["luogo"]), 0) <= RAGGIO_KM:
            try:
                a["testo"] = DETTAGLIO[a["fonte"]](a["url"])[:1500]
            except Exception as e:
                print("dettaglio non letto:", a["url"], e)
            time.sleep(1)
    in_zona = [a for a in nuovi.values() if vicino(a["luogo"], a["titolo"] + " " + a["testo"], km)]

    # il filtro rigira anche sui vecchi: se migliora, ripulisce lo storico
    annunci = [a for a in unisci(stato["annunci"], in_zona, oggi)
               if vicino(a["luogo"], a["titolo"] + " " + (a.get("testo") or ""), km)]
    for a in annunci:
        a["protette"] = flag_protette(a)
    try:
        valuta(annunci)
    except Exception as e:
        print("LLM non disponibile:", e)
    for a in annunci:
        if not a.get("punteggio_ai"):
            a.update(punteggio=punteggio_parole(a), motivo="", richiede_inglese=False, punteggio_ai=False)
    annunci.sort(key=lambda a: -a["punteggio"])

    FILE_DATI.parent.mkdir(exist_ok=True)
    FILE_DATI.write_text(json.dumps({"aggiornato": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                     "fonti": fonti, "annunci": annunci}, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(f"{len(annunci)} annunci salvati ({len(in_zona)} candidati nuovi entro {RAGGIO_KM} km)")


if __name__ == "__main__":
    main()
