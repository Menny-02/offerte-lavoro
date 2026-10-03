# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS, no framework: one `docs/index.html` served by GitHub Pages, data from `docs/annunci.json` written by a GitHub Actions job (`cerca.py`). Zero running cost is a hard constraint.

## Users

One person: a woman in her late fifties in the province of Treviso, looking for office work after decades as an impiegata commerciale (order entry, purchasing, customer service, front/back office). Not very technological. She uses a desktop PC and opens the page from a desktop shortcut, a few times a week, to find ads worth applying to. Her nephew set it up and maintains it remotely.

## Product Purpose

Gather job ads from LinkedIn, Indeed, ClicLavoro Veneto (Centri per l'Impiego) and Subito, keep only those in the province of Treviso, rank them against her profile with a short plain-Italian reason, and let her open each ad and mark it "Mi sono candidata" or "Non mi interessa". Success: she sends more, better-targeted applications without having to search site by site.

## Operating Context

- Opened in a desktop browser, possibly with browser zoom raised.
- A search runs automatically every morning; there is no search button (the user removed it as unnecessary).
- Applying happens on the original site, in a new tab.

## Capabilities and Constraints

- Statuses ("candidata", "scartato") live in her browser's localStorage; clearing browser data loses them.
- Each ad carries: titolo, azienda (may be empty), luogo, fonte, data, punteggio 0-100, motivo (may be empty when the AI was unavailable), richiede_inglese, protette (L. 68/99).
- Ads below 40 are kept but tucked away.
- Language: Italian only.

## Evidence on Hand

Real ads in `docs/annunci.json`. No testimonials, no claims beyond what the data shows.

## Product Principles

- She never has to understand how it works: one page, plain words, nothing to configure.
- Every ad answers "is it worth my time?" before she clicks.
- Nothing she marks gets lost or shown again by surprise.
- Honest about uncertainty: say when the AI could not judge an ad, or when a search failed.

## Accessibility & Inclusion

Older, non-technical user: large text (about 19px base), high contrast, big click targets, visible keyboard focus, no jargon, no icons without words, works at 150-200% browser zoom.
