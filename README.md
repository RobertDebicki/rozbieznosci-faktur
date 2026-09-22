# Rozbieznosci faktura vs wycena — agent dochodzeniowy

> 🚧 Brief, mockup, architektura i plan zatwierdzone. Etap 1 dostarcza dane syntetyczne oraz zestaw ewaluacyjny. Interfejs i agent powstaną w kolejnych etapach.

## Problem

Firma wykonawcza traci marze i nie wie gdzie. Wartosci na fakturach odbiegaja od wycen,
a ustalenie przyczyny wymaga recznego przekopania sie przez umowy, aneksy i korespondencje.
Przy kilkuset projektach nikt tego nie robi systematycznie, wiec strata wychodzi na jaw
dopiero przy zamknieciu roku.

## Co system ma robic

1. **Wykrycie** — zestawia wyceny z faktami fakturowymi i wskazuje projekty z rozbieznoscia.
2. **Odsiew** — odrzuca to, co rozbieznoscia nie jest: fakturowanie etapowe, VAT, kaucje, zaokraglenia.
3. **Wyjasnienie** — dla pozostalych szuka przyczyny w dokumentach i korespondencji,
   z cytatem i linkiem do zrodla przy kazdej tezie.
4. **Uczciwa niewiedza** — gdy dowodu nie ma, mowi "nie ustalono" i podaje, gdzie sprawdzic recznie.

## Zalozenie projektowe

Liczby pochodza z SQL-a, nie z modelu. Model odpowiada wylacznie za znalezienie i ocene
dowodu w tekscie. Dzieki temu kwota w raporcie nigdy nie jest zmyslona.

## Status

| Etap | Stan |
|---|---|
| Brief | ✅ zatwierdzony 21.09.2026 |
| Design | ✅ mockup przekazany 21.09.2026; tokeny w `.Codex/design-system.md` |
| Architektura | ✅ zatwierdzona 21.09.2026; opis w `.Codex/architecture.md` |
| Dane syntetyczne | ✅ generator i lokalne dokumenty |
| Zestaw ewaluacyjny | ✅ 30 spraw, w tym 5 bez potwierdzalnej przyczyny |
| Plan budowy | ✅ zatwierdzony; `.Codex/build-plan.md` |
| Implementacja | ⏳ etap 1 z 8 |
| Wyniki i pomiary | ❌ |

## Dane

Wylacznie syntetyczne. Repozytorium jest publiczne, wiec nie trafiaja tu zadne dane
realnego klienta. Generator danych jest w `skrypty/`.

## Uruchomienie etapu 1

Wymagany jest `uv`. Uruchamia on odpowiednią wersję Pythona w lokalnym `.venv`:

```bash
uv run --extra dev python -m skrypty.generuj_dane
uv run --extra dev pytest -q
```

Pierwsze polecenie tworzy `dane/demo.sqlite`, dokumenty w
`dane/syntetyczne/` i `ewaluacja/zestaw.jsonl`. Baza jest ignorowana przez
git i generator jej nie nadpisuje. Do odtworzenia użyj nowej ścieżki
`--db` lub usuń własną wygenerowaną bazę. Parametr `--as-of RRRR-MM-DD`
ustawia datę referencyjną spraw demonstracyjnych.
