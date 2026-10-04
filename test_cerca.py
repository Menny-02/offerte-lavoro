"""Self-check della logica pura di cerca.py: python test_cerca.py"""
from datetime import date

from cerca import (carica_comuni, chiave, flag_protette, parse_llm, punteggio_parole, unisci,
                   vicino)

KM = carica_comuni()

# filtro distanza: primo pezzo del luogo, confronto esatto col comune, max 15 km da Treviso
assert vicino("Treviso, VEN, IT", "", KM)
assert vicino("Paese, Veneto, Italia", "", KM)
assert vicino("Quinto di Treviso", "", KM)
assert vicino("Quarto d’Altino, Veneto, Italy", "", KM)  # apostrofo curvo, comune VE a 14 km
assert not vicino("Castelfranco Veneto (TV)", "", KM)  # in provincia ma a 24 km
assert not vicino("CONEGLIANO (TV)", "sede a Treviso", KM)  # comune noto lontano: il testo non conta
assert not vicino("Rubano, Veneto, Italy", "sede a Treviso", KM)
assert not vicino("Mestre, Venezia", "", KM)
assert not vicino("Italia", "", KM)
assert not vicino("Venice, Veneto, Italy", "zona Mestre", KM)
# luogo sconosciuto (frazione, regione, area metropolitana): vale se il testo nomina un comune vicino
assert vicino("Bonisiolo, VEN, IT", "Sede di lavoro: Mogliano Veneto (TV)", KM)
assert vicino("Greater Treviso Metropolitan Area", "Ufficio a Villorba", KM)
assert not vicino("Greater Treviso Metropolitan Area", "Sede a Oderzo (TV)", KM)
assert not vicino("Veneto, Italy", "Azienda in provincia di Treviso cerca", KM)
assert not vicino("Veneto, Italy", "Azienda di Padova cerca", KM)
assert not vicino("", "", KM)

# dedup: stesso annuncio su LinkedIn e Indeed -> stessa chiave
a = {"titolo": "Impiegata Back-Office", "azienda": "Rossi S.r.l.", "luogo": "Treviso, Veneto, Italy", "url": "u1"}
b = {"titolo": "impiegata back office", "azienda": "ROSSI SRL", "luogo": "Treviso, VEN, IT", "url": "u2"}
assert chiave(a) == chiave(b)
# senza azienda (Centri per l'Impiego) titoli generici non devono collidere
c1 = {"titolo": "CONTABILI", "azienda": "", "luogo": "TREVISO (TV)", "url": "x/1"}
c2 = {"titolo": "CONTABILI", "azienda": "", "luogo": "TREVISO (TV)", "url": "x/2"}
assert chiave(c1) != chiave(c2)

# unione: conserva prima_vista e punteggio, aggiunge i nuovi, taglia oltre 30 giorni
oggi = date(2026, 10, 3)
vecchio = dict(a, id=chiave(a), prima_vista="2026-09-30", data="2026-09-29", punteggio=88, motivo="ok", punteggio_ai=True)
scaduto = dict(c1, id=chiave(c1), prima_vista="2026-08-01", data="2026-08-01", punteggio=50)
nuovo = dict(c2, data="2026-10-02")
uniti = {x["id"]: x for x in unisci([vecchio, scaduto], [b, nuovo], oggi)}
assert set(uniti) == {chiave(a), chiave(c2)}, uniti.keys()
assert uniti[chiave(a)]["prima_vista"] == "2026-09-30" and uniti[chiave(a)]["punteggio"] == 88
assert uniti[chiave(c2)]["prima_vista"] == "2026-10-03" and "punteggio" not in uniti[chiave(c2)]
# annuncio pubblicato da oltre 30 giorni ma visto oggi per la prima volta: scartato (niente "nuovo" fasullo)
assert unisci([], [dict(c1, data="2026-08-01")], oggi) == []

# risposta AI: buona, dentro ```json, rotta
ok = '{"risultati":[{"id":"k1","punteggio":91,"motivo":"Gestione ordini.","richiede_inglese":false}]}'
assert parse_llm(ok)["k1"]["punteggio"] == 91
assert parse_llm("```json\n" + ok + "\n```")["k1"]["motivo"] == "Gestione ordini."
assert parse_llm("scusa, non posso") == {}
assert parse_llm('{"risultati":[{"id":"k1","punteggio":"tanto"}]}') == {}

# fallback a parole chiave e flag L. 68/99
assert punteggio_parole({"titolo": "Addetta ufficio acquisti"}) > punteggio_parole({"titolo": "Magazziniere carrellista"})
assert flag_protette({"titolo": "Back office - Categoria Protetta L.68/99", "testo": ""})
assert flag_protette({"titolo": "Impiegata", "testo": "riservato iscritti legge 68/99 art. 18"})
assert not flag_protette({"titolo": "Impiegata", "testo": "contratto CCNL commercio"})

print("test_cerca: tutto ok")
