# Rozbieżności faktur — mapa projektu

## Wymagania i cel

Demonstracyjna aplikacja dla działu księgowego, na danych wyłącznie syntetycznych.
Ma wykrywać różnice między fakturą a wyceną właściwej transzy, szukać przyczyny
w dokumentach i mailach oraz pokazywać dowód. Brak dowodu oznacza „przyczyna
nieustalona”. Użytkownik pracuje w przeglądarce i może zadawać proste pytania.
Kryteria sukcesu i zakres są w `.claude/project-state.md`.

## Zaimplementowane funkcje

### Generator danych syntetycznych

- Polecenie `python -m skrypty.generuj_dane` tworzy lokalną bazę SQLite,
  30 syntetycznych spraw, dokumenty tekstowe i `ewaluacja/zestaw.jsonl`.
- `--db`, `--corpus`, `--evaluation`, `--seed` i `--as-of` sterują miejscem
  zapisu, odtwarzalnością i datą referencyjną. Generator odmawia nadpisania
  bazy z danymi, więc nie usuwa przypadkowo pracy użytkownika.
- Każda faktura należy do istniejącego klienta, projektu i transzy tego
  projektu. Schemat odrzuca niecałkowite kwoty w groszach. Widok
  `tranche_references` uwzględnia tylko zatwierdzone zmiany.
- Zestaw obejmuje pięć przypadków fakturowania etapowego bez różnicy,
  pięć zatwierdzonych zmian, pięć rabatów, pięć prac dodatkowych, pięć
  błędów faktury lub wyceny i pięć spraw z nieustaloną przyczyną.
- Pliki: `rozbieznosci/db.py`, `rozbieznosci/schema.sql`,
  `rozbieznosci/models.py`, `skrypty/generuj_dane.py`, `dane/syntetyczne/`,
  `ewaluacja/zestaw.jsonl`; testy w `testy/test_dane.py`.

## Architektura

Pełny opis w `.Codex/architecture.md`. Detektor kwot będzie deterministyczny;
agent językowy później oceni dowody dla różnic. Projekt jest jednym lokalnym
serwisem z bazą SQLite. Obecnie działa tylko generator danych; API i UI są
następnymi etapami.

## Design system

Tokeny CSS i struktura widoków są w `.Codex/design-system.md`. Przekazany
HTML jest prototypem wizualnym z odpowiedziami na sztywno, nie logiką aplikacji.

## Plan budowy

Plan w `.Codex/build-plan.md` został zatwierdzony. Etap 1: dane i fundament
wykonane. Następny etap: deterministyczny detektor rozbieżności.

## Ważne decyzje

- Dane wyłącznie syntetyczne; lokalne pliki zastępują Drive i Gmail.
- Kwoty zapisujemy jako całkowite grosze; VAT pozostaje oddzielny.
- Etapowanie jest modelowane przez transze, więc częściowa faktura nie jest
  porównywana do pełnej wyceny projektu.
- Baza demo (`dane/*.sqlite`) jest generowana lokalnie i ignorowana przez git;
  tekstowe źródła i etykiety ewaluacyjne mogą być publiczne.
- Python 3.12.13 zapewnia `uv` w lokalnym `.venv`; nie trzeba instalować
  Pythona systemowo.
