# Architektura — Rozbieżności faktur

Zatwierdzona przez użytkownika 21.09.2026. Zakres: demonstracja portfolio na
syntetycznych danych, lokalne odpowiedniki bazy faktur, Drive i maili. Widoki
i wygląd wynikają z `.Codex/design-system.md`.

## Przepływy użytkownika

1. **Pytanie:** księgowa wpisuje proste polecenie z klientem, okresem lub progiem
   różnicy, albo wybiera okres i klienta w formularzu. System pokazuje rozpoznane
   filtry. Przy wielu pasujących klientach prosi o wybór; przy nieobsługiwanym
   poleceniu wyjaśnia, jakie warunki rozumie.
2. **Analiza:** aplikacja pobiera faktury z wybranego okresu, porównuje je z
   zatwierdzoną kwotą dla właściwego projektu i etapu, a dla różnic szuka
   dowodów. Ekran postępu pokazuje rzeczywisty etap, nie udawany licznik czasu.
3. **Wynik:** lista rozróżnia brak faktur, brak różnic, różnicę wyjaśnioną,
   różnicę bez przyczyny i sprawę, której nie można wiarygodnie porównać.
   Podsumowanie i kwoty pochodzą wyłącznie z bazy. Sprawę otwiera jedno
   kliknięcie, źródło drugie; powrót zachowuje filtry.
4. **Szczegół:** użytkownik widzi kwotę netto faktury, kwotę referencyjną,
   różnicę, wyjaśnienie i cytaty z lokalizacją w dokumencie. Nieczytelny
   dokument jest jawnie oznaczony. Brak dowodu daje „przyczyna nieustalona”
   i listę kontroli ręcznych.
5. **Pytanie uzupełniające:** użytkownik pyta o bieżącą analizę albo sprawę.
   Odpowiedź korzysta z wybranych danych i cytowanych źródeł. Pytanie o inną
   grupę faktur wymaga uruchomienia nowej analizy. Nie ma samodzielnego
   wykonywania dowolnego SQL przez model.

## Logika i granice odpowiedzialności

- **Interpretacja pytania:** zamknięty schemat filtrów: klient, data od/do,
  minimalna różnica kwotowa lub procentowa. Walidacja nazw klientów i dat
  odbywa się po interpretacji. Model nie może rozszerzać zakresu danych.
- **Detektor deterministyczny:** wszystkie kwoty jako grosze całkowite,
  porównanie netto do netto. Reguły etapowania, harmonogram transz i
  zatwierdzone aneksy decydują o kwocie referencyjnej. Jeśli brak mapowania faktury do etapu,
  sprawa otrzymuje status „nie można wiarygodnie porównać”, a nie fałszywą
  różnicę. VAT, kaucja i zaokrąglenia nie są przyczyną alarmu.
- **Indeks dokumentów:** wsadowe dzielenie syntetycznych umów, wycen,
  aneksów, protokołów i maili na fragmenty z identyfikatorem, typem,
  projektem, datą i lokalizatorem. Wyszukiwanie łączy pełny tekst
  (numery i kwoty) z podobieństwem semantycznym; wyniki są ograniczone
  do właściwego projektu.
- **Wyjaśniacz:** dostaje wykrytą różnicę i fragmenty źródeł. Może wybrać
  przyczynę wyłącznie z zatwierdzonej listy. Odpowiedź zawiera identyfikator
  dowodu i cytat, który istnieje w źródle. Walidator odrzuca zmyślone
  cytaty, źródła i kwoty. Bez dowodu wynik to „przyczyna nieustalona”.
- **Odpowiedzi uzupełniające:** korzystają z tego samego zamrożonego zbioru
  spraw i dowodów; wyliczenia liczy kod, model tylko je opisuje.
- **Pomiary:** zapisywany jest czas, liczba użytych źródeł, wykorzystanie
  modelu, koszt szacowany z aktualnej konfiguracji i wynik walidacji.

## Model danych

| Byt | Relacje i najważniejsze pola |
|---|---|
| Klient | 1 → wiele projektów; nazwa, identyfikator |
| Projekt | 1 → wiele etapów, wycen, faktur, dokumentów |
| Etap | Projekt, zakres, zatwierdzona kwota bazowa, data/stan |
| Transza rozliczeniowa | Etap, kolejność, kwota należna, warunek odbioru, stan |
| Wycena | Projekt, wersja, pozycje i przypisanie do etapów; jedna wersja zatwierdzona |
| Zmiana | Projekt/etap, kwota netto, typ, status zatwierdzenia, dokument źródłowy |
| Faktura i pozycja | Klient, projekt, etap, data, kwoty netto/VAT, identyfikatory; pozycje mapują się do etapu |
| Dokument | Projekt, rodzaj, data, ścieżka lokalna, dostępność |
| Fragment dokumentu | Dokument, tekst, lokalizator, indeks tekstowy, wektor |
| Analiza | Filtry, data uruchomienia, status, identyfikatory spraw |
| Sprawa i dowód | Obliczone kwoty, status, przyczyna, cytowany fragment |
| Pytanie uzupełniające | Analiza/sprawa, pytanie, odpowiedź, użyte dowody |
| Pomiar modelu | Operacja, czas, tokeny, szacowany koszt, błąd |

Kwota referencyjna dla transzy powstaje z zatwierdzonej wyceny, harmonogramu
i zatwierdzonych zmian etapu. Detektor porównuje wystawioną fakturę z należną
transzą oraz kontroluje sumę narastającą. Kwota mniejsza od pełnej wyceny
otwartego etapu nie jest alarmem tylko dlatego, że prace trwają. Jeśli brak
harmonogramu transz, detektor może wykazać przekroczenie zatwierdzonego
limitu etapu, ale nie orzeka o brakującym fakturowaniu. Zakres dat filtruje
faktury pokazywane w analizie; wcześniejsze faktury etapu nadal są uwzględniane
przy obliczaniu sumy narastającej.

## Widoki, nawigacja i komponenty

`Start` → `Doprecyzowanie klienta` (tylko gdy trzeba) → `Postęp` → `Wyniki`
→ `Szczegół sprawy` → `Podgląd źródła`. Z wyników i szczegółu można zadać
pytanie uzupełniające. Pasek główny prowadzi do nowej analizy, historii
zapisanych analiz i krótkiej pomocy z przykładami pytań.

Komponenty: `AppShell`, `QuestionForm`, `FilterForm`, `ClientPicker`,
`AnalysisProgress`, `FilterSummary`, `ResultsSummary`, `CaseList`, `CaseRow`,
`CaseDetail`, `AmountBreakdown`, `Explanation`, `EvidenceCard`,
`SourcePreview`, `FollowupForm`, `HistoryList`, `HelpView`.

Na małym ekranie szczegół układa się w jedną kolumnę, a panel pytań przestaje
być sticky. Każdy status ma tekstową etykietę; źródła są dostępne także
z klawiatury. Ekran pusty nie może mylić braku faktur z brakiem różnic.

## Błędy i ograniczenia

- Niedostępność dostawcy modelu nie zmienia wyników liczbowych; wyjaśnienie
  pozostaje nieustalone z czytelnym komunikatem.
- Nieczytelny skan jest pokazywany jako brak dostępnego dowodu.
- Nie ma automatycznej rekomendacji „można zaksięgować” na podstawie samej
  odpowiedzi modelu. Prototypowa odpowiedź tego typu nie jest wymaganiem.
- Dane są wyłącznie syntetyczne, bez realnego Drive, Gmaila i faktur klientów.
- Ewaluacja używa 30 spraw, co najmniej 5 bez potwierdzalnej przyczyny;
  cele to poprawne kwoty, zero fikcyjnych źródeł i co najmniej 90% poprawnych
  wyjaśnień dla spraw z dowodem.
