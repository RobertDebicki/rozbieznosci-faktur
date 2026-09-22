# Rozbieznosci faktura vs wycena — agent dochodzeniowy

> Gotowa demonstracja przeglądarkowa na danych syntetycznych. Pracownik wpisuje zwykłe pytanie, widzi policzone rozbieżności, źródła i może dopytać o wynik.

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
| Implementacja | ✅ etapy 1–8 z 8 |
| Wyniki i pomiary | ✅ raport w `ewaluacja/wyniki/raport.json` |

## Dane

Wylacznie syntetyczne. Repozytorium jest publiczne, wiec nie trafiaja tu zadne dane
realnego klienta. Generator danych jest w `skrypty/`.

## Szybki start

Wymagany jest `uv`. Uruchamia on odpowiednią wersję Pythona w lokalnym `.venv`:

```bash
uv run --extra dev python -m skrypty.generuj_dane --db dane/portfolio-demo.sqlite
uv run --extra dev python -m skrypty.indeksuj --db dane/portfolio-demo.sqlite --fts-only
DEMO_DB_PATH=dane/portfolio-demo.sqlite uv run uvicorn rozbieznosci.app:app --host 127.0.0.1 --port 8000
```

Otwórz `http://127.0.0.1:8000` w przeglądarce. Terminal służy tylko do
uruchomienia demonstracji; użytkownik końcowy pracuje wyłącznie w interfejsie.
Polecenie generatora tworzy 30 faktur, lokalne dokumenty i etykiety testowe.
Jeśli baza pod tą ścieżką już istnieje, pomiń pierwszy krok albo wybierz
nową ścieżkę. Generator nie nadpisuje bazy z danymi ani dokumentów o innej
treści. Nazwy dokumentów są stałe przy ponownym uruchomieniu z tym samym ziarnem.

Testy i osobny detektor uruchomisz tak:

```bash
uv run --extra dev pytest -q
uv run --extra dev python -m skrypty.sprawdz --db dane/portfolio-demo.sqlite --last-months 12
```

`skrypty.sprawdz` pokazuje faktury z wybranego okresu i ich status:
`equal`, `difference` albo `not_comparable` (brak przypisanej transzy).
Przykładowe zawężenie: `--client-id 1 --last-months 6 --min-pln 1000`.
Różnica jest liczona w kwocie netto wobec pierwotnej wyceny transzy;
zatwierdzone zmiany są liczone osobno. Stare bazy wygenerowane przed etapem 2
nie mają pełnego schematu; dla nich wybierz nową ścieżkę `--db`.

Indeks dokumentów ma tryb pełnotekstowy oraz semantyczny. Ten drugi wymaga
jednorazowego pobrania lokalnego modelu:

```bash
uv sync --extra retrieval
uv run --extra retrieval python -m skrypty.indeksuj --db dane/portfolio-demo.sqlite
```

W obu trybach fragmenty są filtrowane według projektu. Dokument, którego
nie można odczytać, jest oznaczany jako niedostępny zamiast trafiać do wyników.

Wyjaśniacz ma jawny `DemoProvider`, który symuluje odpowiedzi na przygotowanych
danych syntetycznych. Adapter `GroqProvider` może użyć klucza
`GROQ_API_KEY` ze środowiska. Walidator przyjmuje tylko cytat istniejący
w podanym fragmencie oraz kwotę zgodną z detektorem; w przeciwnym razie
zwraca „przyczyna nieustalona”. Wywołanie prawdziwego API wymaga własnego
klucza i nie jest potrzebne do lokalnej demonstracji.

API w `rozbieznosci/app.py` przyjmuje pytanie o klienta i okres przez
`POST /api/analyses`, zapisuje wynik i zwraca szczegóły przez
`GET /api/analyses/{id}`.

Wersja bez modelu embeddingów działa po indeksowaniu z `--fts-only`.
Wyjaśnienia w interfejsie tworzy jawna symulacja `DemoProvider` na
przygotowanych dokumentach.

Po otrzymaniu wyniku możesz zapytać o największą różnicę, liczbę
rozbieżności lub przyczynę i kwotę konkretnej faktury. Odpowiedzi są
zapisywane i widoczne po ponownym otwarciu analizy.

## Ewaluacja

Powtarzalny przebieg na etykietach z repozytorium:

```bash
uv run --extra dev python -m skrypty.generuj_dane --db dane/ewaluacja.sqlite --as-of 2026-09-22
uv run --extra dev python -m skrypty.indeksuj --db dane/ewaluacja.sqlite --fts-only
uv run --extra dev python -m skrypty.ewaluuj --db dane/ewaluacja.sqlite --dataset ewaluacja/zestaw.jsonl --output ewaluacja/wyniki/raport.json
```

Opublikowany [raport](ewaluacja/wyniki/raport.json) dla jawnej symulacji:

| Miara | Wynik |
|---|---:|
| Poprawne kwoty | 30/30 |
| Poprawne wyjaśnienia w sprawach z dowodem | 20/20 |
| Trafienie właściwego dowodu w wyszukiwaniu | 20/20 |
| Poprawne „przyczyna nieustalona” | 5/5 |
| Fakturowanie etapowe bez fałszywego alarmu | 5/5 |
| Fikcyjne źródła | 0 |

Te wyniki dotyczą przygotowanego zestawu syntetycznego i deterministycznego
`DemoProvider`. Nie są pomiarem jakości zewnętrznego modelu językowego.
Raport podaje czas samej analizy spraw; generowanie bazy, indeksowanie
i renderowanie strony nie wchodzą do tego czasu. Symulacja nie używa API,
więc tokeny i koszt API wynoszą 0. Adapter `GroqProvider` jest dostępny
po podaniu własnego `GROQ_API_KEY`; nie został zmierzony w opublikowanym raporcie.
