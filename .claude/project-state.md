# Stan projektu — Agent dochodzeniowy: rozbieznosci faktura vs wycena

Założony: 14.09.2026. Brief zatwierdzony: 21.09.2026.

## Faza 1 — Brief  ✅ UKOŃCZONA

**Cel i odbiorca:** demonstracja do publicznego portfolio, bez wdrożenia u klienta.
Głównym użytkownikiem jest dział księgowy, w którym nie ma wielu osób technicznych.
Użytkownik ma szybko zrozumieć różnice między fakturami a wycenami i ich przyczyny.

**Sposób użycia:** prosta aplikacja w przeglądarce. Użytkownik może wpisać zwykłe
pytanie, np. „Pokaż rozbieżności z ostatniego roku” lub „Sprawdź rozbieżności
na fakturach klienta XYZ z ostatniego pół roku”. Dostępne jest również uruchomienie
analizy bez pisania pytania. Po wyniku można zadawać pytania uzupełniające o analizę.

**Zakres pierwszej wersji:** faktury w syntetycznej bazie danych oraz lokalna
symulacja dokumentów z Google Drive i korespondencji mailowej. Dokumenty: pierwotna
wycena, umowa, aneksy, protokoły odbioru i maile. Rozpoznawane przyczyny:
fakturowanie etapowe, zmiana zakresu potwierdzona aneksem lub mailem, rabat,
dodatkowe prace oraz błąd w fakturze lub wycenie. Wynik ma zawierać kwotę,
zrozumiałe wyjaśnienie i dowód ze źródła. Bez wystarczającego dowodu agent mówi
„przyczyna nieustalona” i wskazuje materiały do sprawdzenia. „Nie znaleziono
rozbieżności” jest odrębnym wynikiem, gdy kwoty się zgadzają.

**Kryteria sukcesu:** ewaluacja na 30 syntetycznych sprawach, w tym co najmniej
5 bez możliwej do potwierdzenia przyczyny. Wszystkie kwoty policzone poprawnie,
zero zmyślonych źródeł i co najmniej 90% poprawnych wyjaśnień w sprawach z dowodem.
Interfejs ma być łatwy w obsłudze i umożliwiać pytania uzupełniające. Koszt
działania i czas odpowiedzi będą mierzone; projekt korzysta z darmowych narzędzi.

## Faza 2 — Design mockup  ✅ UKOŃCZONA
Użytkownik przekazał eksport HTML i JS mockupu 21.09.2026. Układ, interakcje,
typografia i tokeny zostały zapisane w `../.Codex/design-system.md`.
Eksport jest prototypem wizualnym, a nie implementacją obliczeń i odpowiedzi.

## Faza 3 — Architektura i user flows  ✅ UKOŃCZONA
Zatwierdzona przez użytkownika 21.09.2026. Przepływy, model danych, nawigacja,
komponenty i obsługa błędów są w `../.Codex/architecture.md`.

## Faza 4 — Plan budowy  ✅ UKOŃCZONA
Plan w `../.Codex/build-plan.md` został zatwierdzony przez użytkownika.
Etap 1: generator danych i zestaw ewaluacyjny — wykonany.
Etap 2: deterministyczny detektor rozbieżności — wykonany.
Etap 3: indeks dokumentów i wyszukiwanie dowodów — wykonany.
Następny jest etap 4: wyjaśniacz z kontrolą dowodów.

---

## Ustalenia z rozmowy 14.09.2026 (kontekst, nie zatwierdzona architektura)

**Zrodlo case'u:** zadanie z rozmowy rekrutacyjnej. Firma trzymala umowy, aneksy i wyceny
na Google Drive, korespondencje z osobami odpowiedzialnymi po stronie klienta na Gmailu,
a faktury w systemie z API. Agent mial znalezc projekty z rozbieznoscia faktura vs wycena
i ustalic, DLACZEGO sie roznia.

**Glowna pulapka, zidentyfikowana przed startem:** wiekszosc "rozbieznosci" w firmie
wykonawczej to fakturowanie etapowe, nie blad. Naiwny agent generuje setki falszywych
alarmow i traci zaufanie uzytkownika. Odsiew etapowania nalezy do fazy A (regula), nie do modelu.

**Co ten projekt ma udowodnic rekruterowi:** podzial na czesc deterministyczna i czesc
dla modelu, praca z dokumentami, dowod przy kazdej tezie, uczciwe "nie wiem", zmierzony koszt.

**Punkt odniesienia dla szkieletu:** wcześniejszy prywatny projekt (struktura,
warstwa dostawców, walidacja wyjścia, pomiar kosztu i latencji, generator danych).
