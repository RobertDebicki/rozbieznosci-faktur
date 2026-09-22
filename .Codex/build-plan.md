# Rozbieżności faktur — plan budowy

**Cel:** działająca demonstracja agenta dla księgowości, od pytania o klienta
i okres do listy rozbieżności, wyjaśnień z dowodami i pytań uzupełniających.

**Specyfikacja:** `.Codex/architecture.md`, `.Codex/design-system.md` oraz
brief w `.claude/project-state.md`. Plan zatwierdzony przez użytkownika.

**Stack wykonawczy:** Python 3.11+, SQLite z FTS5, FastAPI z szablonami Jinja2,
zwykły JavaScript i CSS, lokalny wielojęzyczny model embeddingów przez
Sentence Transformers, wymienny dostawca LLM przez API. Testy `pytest`.
Jeden proces aplikacji i jedna lokalna baza demonstracyjna. Klucz API jest
potrzebny do analizy z modelem; dane i interfejs działają na syntetycznych
przykładach także bez klucza, z wyraźnym oznaczeniem trybu demonstracyjnego.

**Granice:** tylko dane syntetyczne; żadnych realnych integracji Google,
uwierzytelniania udającego produkcyjne konto ani porad księgowych typu
„można zaksięgować” generowanych przez model. Kwoty są w groszach całkowitych.
Kwoty i statusy pochodzą z kodu, a przyczyny z modelu tylko po sprawdzeniu
cytatu. Po każdym etapie uaktualnić `.Codex/AGENTS.md` razem z kodem.

## Mapa plików

| Obszar | Pliki i odpowiedzialność |
|---|---|
| Dane | `rozbieznosci/db.py` — połączenie i migracje; `rozbieznosci/schema.sql` — relacje i ograniczenia; `skrypty/generuj_dane.py` — syntetyczne dane |
| Domena | `rozbieznosci/models.py` — typy; `rozbieznosci/detektor.py` — porównanie transz i kwot |
| Dokumenty | `rozbieznosci/indeks.py` — fragmenty i FTS5; `rozbieznosci/szukaj.py` — łączenie wyników tekstowych i semantycznych |
| Agent | `rozbieznosci/pytanie.py` — interpretacja filtrów; `rozbieznosci/model.py` — interfejs dostawcy; `rozbieznosci/wyjasnij.py` — hipotezy i walidacja; `rozbieznosci/dopytaj.py` — dalsze pytania |
| Aplikacja | `rozbieznosci/app.py` — trasy i składanie usług; `rozbieznosci/templates/` — strony; `rozbieznosci/static/` — CSS i JavaScript |
| Pomiar | `rozbieznosci/pomiary.py` — czas, tokeny i koszt; `skrypty/ewaluuj.py` — raport na ustalonym zestawie; `ewaluacja/zestaw.jsonl` — 30 przypadków |
| Dokumentacja | `.Codex/AGENTS.md`, `README.md`, `.claude/project-state.md` |

## Etap 1 — Dane i uruchamialny fundament ✅

**Wynik:** `python -m skrypty.generuj_dane` tworzy odtwarzalną bazę oraz
pliki dokumentów i maili; prosty odczyt pokazuje klienta, projekt, transzę,
fakturę i źródło. Przygotować 30 opisanych spraw ewaluacyjnych, co najmniej
5 bez potwierdzalnej przyczyny, zanim powstanie wyjaśniacz.

**Pliki:** `schema.sql`, `db.py`, `models.py`, `skrypty/generuj_dane.py`,
`dane/syntetyczne/`, `ewaluacja/zestaw.jsonl`, `testy/test_dane.py`.

**Kontrakt:** `open_db(path: Path) -> Connection`,
`seed_demo(db: Connection, seed: int = 2026) -> None`.

**Test przed kodem:** powtórzenie generatora z tym samym ziarnem daje te same
identyfikatory i kwoty; FK nie wskazują nieistniejącego projektu; zmiana bez
zatwierdzenia nie zmienia kwoty referencyjnej; kwoty przechodzą przez bazę bez
utraty groszy. Uruchomić `pytest testy/test_dane.py -q`, zobaczyć błąd,
wdrożyć minimum i uruchomić ponownie. Na końcu `python -m skrypty.generuj_dane`
i sprawdzenie liczby spraw ewaluacyjnych.

## Etap 2 — Detektor rozbieżności ✅

**Wynik:** polecenie demonstracyjne zwraca listę policzonych spraw bez LLM.
Faktura częściowa dla otwartego etapu nie staje się alarmem przez porównanie
z pełną wartością projektu.

**Pliki:** `detektor.py`, `skrypty/sprawdz.py`, `testy/test_detektor.py`.

**Kontrakt:** `detect(db: Connection, client_id: int | None, date_from: date,
date_to: date, min_difference_cents: int = 0, min_difference_pct: Decimal =
Decimal(0)) -> list[Detection]`. `Detection` zawiera fakturę, transzę,
kwotę referencyjną, różnicę w groszach i status: `equal`, `difference`,
`not_comparable`.

**Test przed kodem:** pełna transza równa fakturze, nadwyżka, rabat,
niezatwierdzony aneks, faktura częściowa, brak mapowania transzy, wcześniejsza
faktura poza filtrem dat uwzględniona narastająco, VAT i kaucja poza netto.
Uruchomić `pytest testy/test_detektor.py -q` przed i po wdrożeniu. Sprawdzić
wynik `python -m skrypty.sprawdz --last-months 12` na syntetycznej bazie.

## Etap 3 — Indeks i wyszukiwanie dowodów

**Wynik:** zapytanie o projekt, numer aneksu, kwotę lub opis prac zwraca
fragmenty z identyfikatorem i lokalizatorem. Indeksowanie odbywa się wsadowo.

**Pliki:** `indeks.py`, `szukaj.py`, `skrypty/indeksuj.py`,
`testy/test_szukaj.py`.

**Kontrakt:** `index_documents(db: Connection, corpus_dir: Path) -> int` oraz
`retrieve(db: Connection, project_id: int, query: str, limit: int = 8)
-> list[EvidenceChunk]`. `EvidenceChunk` zawiera `document_id`, `chunk_id`,
`locator`, `text`, `source_path` i ranking. Wyszukiwanie pełnotekstowe FTS5
łączy się z lokalnym podobieństwem semantycznym; filtr projektu jest
stosowany przed przekazaniem fragmentów modelowi.

**Test przed kodem:** dokładny numer aneksu i kwota trafiają do wyników,
parafraza znajduje właściwy fragment, fragment obcego projektu nie wycieka,
nieczytelny dokument jest oznaczony jako niedostępny. Uruchomić
`pytest testy/test_szukaj.py -q` przed i po wdrożeniu oraz `python -m
skrypty.indeksuj` na danych demo.

## Etap 4 — Wyjaśniacz z kontrolą dowodów

**Wynik:** różnica otrzymuje jedną z uzgodnionych przyczyn tylko wtedy, gdy
walidator potwierdzi istniejący cytat. Bez dowodu status to `unknown`.

**Pliki:** `model.py`, `wyjasnij.py`, `pomiary.py`,
`testy/test_wyjasnij.py`.

**Kontrakt:** `LLMProvider.complete_json(messages: list[dict], schema: dict)
-> ModelReply`; `explain(detection: Detection, chunks: list[EvidenceChunk],
provider: LLMProvider) -> Explanation`. `Explanation` zawiera `cause` ze
zbioru `staged_billing`, `approved_change`, `discount`, `extra_work`,
`invoice_or_estimate_error`, `unknown`; ponadto `evidence_ids`, cytaty,
tekst dla użytkownika i powód nieustalenia. Kwoty są kopiowane z `Detection`.

**Test przed kodem:** fikcyjny `chunk_id`, cytat nieobecny w tekście,
zmyślona kwota i nieznana przyczyna są odrzucane; brak źródła, timeout i błąd
API kończą się `unknown`, bez utraty wyniku liczbowego. Testy używają
podstawionego dostawcy, bez sieci. Uruchomić `pytest testy/test_wyjasnij.py
-q` przed i po wdrożeniu. Jedno rzeczywiste wywołanie API wykonać dopiero
po podaniu klucza w środowisku; brak klucza ma czytelny status w aplikacji.

## Etap 5 — Interpretacja pytań i API analizy

**Wynik:** użytkownik może podać klienta, datę i próg zwykłym językiem
albo formularzem. Wynik API zwraca zrozumiane filtry, sprawy i statusy.

**Pliki:** `pytanie.py`, `app.py`, `testy/test_pytanie.py`,
`testy/test_api.py`.

**Kontrakt:** `parse_request(text: str, today: date, clients: list[Client])
-> AnalysisRequest | Clarification`; `POST /api/analyses` tworzy analizę,
`GET /api/analyses/{id}` zwraca wynik, `GET /api/analyses/{id}/cases/{case_id}`
zwraca sprawę. Dopuszczone są jedynie zdefiniowane filtry; daty i nazwy
klientów są walidowane po interpretacji. API zwraca odrębne wyniki `no_invoices`
i `no_discrepancies`.

**Test przed kodem:** „ostatnie pół roku”, dokładna data, dwóch klientów
o podobnej nazwie, nieznany klient, odwrócony zakres dat, próg 10%, brak
faktur, brak różnic, pytanie spoza zakresu. Uruchomić wskazane dwa pliki
testowe przed i po kodzie, potem sprawdzić ręcznie kilka żądań HTTP.

## Etap 6 — Interfejs od pytania do dowodu

**Wynik:** pełna główna ścieżka w przeglądarce odpowiada mockupowi:
start → ewentualny wybór klienta → postęp → wyniki → szczegół → źródło.
Filtry i historia przeglądania zachowują się poprawnie po powrocie.

**Pliki:** `templates/base.html`, `templates/start.html`,
`templates/results.html`, `templates/case.html`, `templates/history.html`,
`templates/help.html`, `static/app.css`, `static/app.js`, `app.py`,
`testy/test_widoki.py`.

**Kontrakt:** trasy stron `GET /`, `GET /analyses/{id}`,
`GET /analyses/{id}/cases/{case_id}`, `GET /history`, `GET /help`;
podgląd źródła pobiera wyłącznie fragment powiązany ze sprawą.

**Test przed kodem:** HTML pokazuje tekstowe statusy i kwoty, brak faktur
nie jest podpisany jako brak rozbieżności, niedostępne źródło nie ma aktywnego
„Otwórz”, klawiatura otwiera i zamyka podgląd, pola mają etykiety. Uruchomić
`pytest testy/test_widoki.py -q`, następnie ręcznie przejść główną ścieżkę
na szerokim i wąskim ekranie. W CSS przenieść tokeny z `design-system.md`.

## Etap 7 — Pytania uzupełniające i historia

**Wynik:** użytkownik pyta o wynik lub sprawę; odpowiedź odnosi się do
aktualnej analizy i wskazuje źródła. Historia otwiera zapisane analizy.

**Pliki:** `dopytaj.py`, `app.py`, `static/app.js`, szablony z etapu 6,
`testy/test_dopytaj.py`.

**Kontrakt:** `answer_followup(analysis_id: int, case_id: int | None,
question: str, db: Connection, provider: LLMProvider) -> FollowupAnswer`;
`POST /api/analyses/{id}/questions` zapisuje pytanie i odpowiedź.

**Test przed kodem:** pytanie o największą różnicę liczy kod, pytanie o
przyczynę cytuje tylko dowody bieżącej sprawy, pytanie o nowego klienta
odsyła do nowej analizy, niedostępny model daje czytelny brak odpowiedzi,
historia przywraca filtry i wynik. Uruchomić `pytest testy/test_dopytaj.py -q`
przed i po wdrożeniu oraz ręcznie zadać pytanie z mockupu.

## Etap 8 — Ewaluacja, dokumentacja i demonstracja

**Wynik:** odtwarzalny raport z 30 sprawami, trafnością wyjaśnień, liczbą
fikcyjnych źródeł, odsetkiem `unknown`, czasem oraz użyciem i kosztem modelu.
README pokazuje jak uruchomić demo i jak odczytać wynik ewaluacji.

**Pliki:** `skrypty/ewaluuj.py`, `ewaluacja/wyniki/`,
`testy/test_ewaluacja.py`, `README.md`, `.Codex/AGENTS.md`,
`.claude/project-state.md`, `pyproject.toml`.

**Kontrakt:** `python -m skrypty.ewaluuj --dataset ewaluacja/zestaw.jsonl
--output ewaluacja/wyniki/raport.json` zapisuje wynik z licznikami i mianownikami.
W raportach oddzielić testy bez dowodu od spraw z dowodem. Wskazać, czy
osiągnięto: wszystkie kwoty poprawne, zero zmyślonych źródeł, ≥90% poprawnych
wyjaśnień dla spraw z dowodem.

**Test przed kodem:** raport liczy odsetki na znanym małym zestawie i nie
dzieli przez zero. Uruchomić `pytest testy/test_ewaluacja.py -q`, potem
cały `pytest -q`, generator, indeksowanie i ewaluację. Na końcu przejść
główny flow i skrajne przypadki w przeglądarce oraz zaktualizować
`.Codex/AGENTS.md` wraz z dokumentacją projektu.

## Warunek rozpoczęcia

Fazy 1–4 są ukończone. Każdy etap kończy się działającą i sprawdzoną
wersją; kolejny etap nie ukrywa błędów poprzedniego.
