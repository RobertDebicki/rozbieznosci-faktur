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

### Detektor rozbieżności

- `python -m skrypty.sprawdz --last-months 12` pokazuje status i różnicę
  netto dla faktur z wybranego okresu; `--client-id`, `--from`, `--to`,
  `--min-pln` i `--min-percent` zawężają wynik.
- Porównanie odbywa się z wyceną właściwej transzy. Suma faktur tej transzy
  obejmuje również wcześniejsze faktury spoza wybranego okresu. Pierwotna
  różnica pozostaje widoczna po zatwierdzeniu aneksu lub rabatu; osobno
  liczona jest różnica względem kwoty po zatwierdzonych zmianach.
- Otwarta transza z częściowym fakturowaniem ma status `equal`, dopóki suma
  nie przekracza wyceny. Faktura bez przypisanej transzy ma status
  `not_comparable`. VAT i kaucja płatnicza nie zmieniają porównania netto.
- Pliki: `rozbieznosci/detektor.py`, `rozbieznosci/models.py`,
  `rozbieznosci/schema.sql`, `skrypty/sprawdz.py`; testy w
  `testy/test_detektor.py`.

### Indeks i wyszukiwanie dowodów

- `python -m skrypty.indeksuj` dzieli lokalne dokumenty na fragmenty,
  zapisuje ich lokalizatory i buduje indeks SQLite FTS5 oraz lokalne wektory
  wielojęzycznego modelu Sentence Transformers.
- `--fts-only` pozwala zaindeksować wyłącznie dokładne frazy bez pobierania
  modelu. Pełny tryb wymaga `uv sync --extra retrieval` i pierwszego pobrania
  modelu. Ponowne indeksowanie zastępuje stare fragmenty.
- `retrieve(db, project_id, query)` łączy ranking tekstowy i semantyczny;
  fragmenty innych projektów są odfiltrowane. Brakujące lub nieczytelne pliki
  otrzymują `available = 0` i nie są cytowane jako dowód.
- Pliki: `rozbieznosci/indeks.py`, `rozbieznosci/szukaj.py`,
  `rozbieznosci/schema.sql`, `skrypty/indeksuj.py`; testy w
  `testy/test_szukaj.py`.

### Wyjaśniacz z kontrolą dowodów

- `explain(detection, chunks, provider)` korzysta z kwoty detektora.
  Model lub symulacja wybiera przyczynę i cytat; tekst końcowy składa kod.
- Walidator wymaga znanego identyfikatora fragmentu, dosłownego cytatu,
  zgodnej kwoty i frazy wspierającej kategorię. Odrzucenie odpowiedzi,
  brak źródła i błąd dostawcy dają `unknown` z wyjaśnieniem.
- `DemoProvider` to jawna, deterministyczna symulacja na dokumentach
  syntetycznych. `GroqProvider` używa `GROQ_API_KEY` ze środowiska;
  prawdziwego wywołania API nie wykonano bez klucza użytkownika.
- Pliki: `rozbieznosci/model.py`, `rozbieznosci/wyjasnij.py`;
  testy w `testy/test_wyjasnij.py`.

### Interpretacja pytań i API analizy

- `parse_request` rozpoznaje klienta, ostatnie pół roku/rok, zakres dat
  i próg procentowy. Przy nieznanym lub niejednoznacznym kliencie zwraca
  prośbę o doprecyzowanie zamiast zgadywać.
- `POST /api/analyses` przyjmuje pytanie albo jawne filtry. Zapisuje wyniki
  w SQLite. `GET /api/analyses/{id}` i `GET /api/analyses/{id}/cases/{case_id}`
  odczytują analizę i sprawę.
- API rozróżnia `no_invoices`, `no_discrepancies`, `discrepancies` i
  `needs_review`. Pytania niejednoznaczne otrzymują 409 z opcjami.
- Pliki: `rozbieznosci/pytanie.py`, `rozbieznosci/app.py`,
  `rozbieznosci/schema.sql`; testy w `testy/test_pytanie.py` i
  `testy/test_api.py`.

### Interfejs przeglądarkowy

- Strona `/` oferuje pytanie naturalnym językiem, gotowe przykłady i formularz
  okresu oraz klienta. Doprecyzowanie klienta pokazuje opcje bez zgadywania.
- `/analyses/{id}` pokazuje zrozumiane filtry, liczby, stany puste i listę
  spraw; `/analyses/{id}/cases/{case_id}` pokazuje wyliczenie, wyjaśnienie
  i potwierdzone źródła. Podgląd pobiera fragment tylko z bieżącej sprawy.
- `/history` otwiera zapisane analizy, `/help` wyjaśnia sposób użycia.
  Widoki są responsywne i mają tekstowe statusy, etykiety pól oraz natywny
  dialog źródła. Bez klucza API używają jawnej symulacji.
- Pliki: `rozbieznosci/app.py`, `rozbieznosci/templates/`,
  `rozbieznosci/static/`; testy w `testy/test_widoki.py`.

## Architektura

Pełny opis w `.Codex/architecture.md`. Detektor kwot jest deterministyczny;
wyjaśniacz ocenia źródła, ale dopuszcza tylko zweryfikowane cytaty. Projekt
jest jednym lokalnym serwisem z bazą SQLite. Obecnie działają generator
danych, detektor, indeks, wyjaśniacz, API i UI. Następne są pytania
uzupełniające oraz końcowa ewaluacja.

## Design system

Tokeny CSS i struktura widoków są w `.Codex/design-system.md`. Przekazany
HTML jest prototypem wizualnym z odpowiedziami na sztywno, nie logiką aplikacji.

## Plan budowy

Plan w `.Codex/build-plan.md` został zatwierdzony. Etapy 1–6 wykonane.
Następny etap: pytania uzupełniające i historia odpowiedzi.

## Ważne decyzje

- Dane wyłącznie syntetyczne; lokalne pliki zastępują Drive i Gmail.
- Kwoty zapisujemy jako całkowite grosze; VAT pozostaje oddzielny.
- Etapowanie jest modelowane przez transze, więc częściowa faktura nie jest
  porównywana do pełnej wyceny projektu.
- Faktury bez mapowania transzy pozostają widoczne z uczciwym statusem
  `not_comparable`; nie przypisujemy ich automatycznie.
- Model embeddingów jest opcjonalną zależnością, więc dokładne frazy działają
  również na komputerze bez pobranego modelu.
- Symulacja odpowiedzi modelu jest jawnie oddzielona od dostawcy API.
  Żadne rzeczywiste dane klienta nie są wysyłane do modelu.
- Baza demo (`dane/*.sqlite`) jest generowana lokalnie i ignorowana przez git;
  tekstowe źródła i etykiety ewaluacyjne mogą być publiczne.
- Python 3.12.13 zapewnia `uv` w lokalnym `.venv`; nie trzeba instalować
  Pythona systemowo.
