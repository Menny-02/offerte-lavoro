"""Self-check della logica pura di cerca.py: python test_cerca.py"""
from datetime import date

from cerca import (carica_comuni, chiave, flag_protette, in_provincia, parse_llm,
                   punteggio_parole, unisci)

TV, ALTRI = carica_comuni()

# filtro provincia: primo pezzo del luogo, confronto esatto
assert in_provincia("Paese, Veneto, Italia", "", TV, ALTRI)
assert in_provincia("Castelfranco Veneto (TV)", "", TV, ALTRI)
assert in_provincia("Treviso, VEN, IT", "", TV, ALTRI)
assert in_provincia("Quinto di Treviso", "", TV, ALTRI)
assert in_provincia("Greater Treviso Metropolitan Area", "", TV, ALTRI)
assert in_provincia("CASTELLO DI GODEGO", "", TV, ALTRI)
assert not in_provincia("Mestre, Venezia", "", TV, ALTRI)
assert not in_provincia("Quarto d’Altino, Veneto, Italy", "zona Treviso", TV, ALTRI)  # apostrofo curvo, comune VE
assert not in_provincia("Rubano, Veneto, Italy", "sede a Treviso", TV, ALTRI)  # comune noto di PD vince sul testo
assert not in_provincia("Italia", "", TV, ALTRI)
assert not in_provincia("Venice, Veneto, Italy", "zona Mestre", TV, ALTRI)
# luogo sconosciuto (frazione, regione): decide il testo
assert in_provincia("Bonisiolo, VEN, IT", "Sede di lavoro: Mogliano Veneto (TV)", TV, ALTRI)
assert in_provincia("Veneto, Italy", "Azienda in provincia di Treviso cerca", TV, ALTRI)
assert not in_provincia("Veneto, Italy", "Azienda di Padova cerca", TV, ALTRI)
assert not in_provincia("", "", TV, ALTRI)

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
