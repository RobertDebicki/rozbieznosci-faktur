# Changelog

Zapis zmian w projekcie — najnowsze wpisy na górze.

---

## 2026-09-22 18:49 — Robert Dębicki

**✅ Zrobione:**
- Dodano cztery zrzuty prawdziwego interfejsu demonstracyjnego na danych syntetycznych.
- README pokazuje przepływ od pytania przez wynik do dowodu źródłowego.
- Dodano workflow GitHub Actions, który uruchamia testy z zależnościami z `uv.lock`.
- Otworzono PR #2; workflow GitHub Actions przeszedł na GitHubie.

**🚧 W toku / nie wdrożone:**
- Zmiany są w PR #2 i czekają na połączenie z `main`.

**🎯 Następny krok:**
- Połączyć PR #2 z `main`, a potem rozpocząć brief drugiego projektu.

---

## 2026-09-22 16:09 — Robert Dębicki

**✅ Zrobione:**
- Dodano raport ewaluacyjny 30 spraw z jawnymi licznikami i mianownikami.
- Poprawiono odtwarzalność generatora i ochronę istniejącego korpusu.
- Odtworzono bazę, indeks i raport; wszystkie ustalone progi demonstracji są spełnione.

**🚧 W toku / nie wdrożone:**
- Integracje z rzeczywistym Google Drive, pocztą i systemem fakturowym są poza zakresem demo.
- Nie mierzono skuteczności zewnętrznego LLM bez klucza API.

**🎯 Następny krok:**
- Udostępnić użytkownikowi repozytorium i instrukcję lokalnego uruchomienia.

---

## 2026-09-22 — Robert Dębicki

**✅ Zrobione:**
- Dodano pytania uzupełniające o analizę i konkretną fakturę.
- Odpowiedzi korzystają z zapisanych kwot i cytatów, są utrwalane w bazie.
- Sprawdzono pytania i odświeżenie historii w przeglądarce.

**🚧 W toku / nie wdrożone:**
- Końcowy raport ewaluacyjny i podsumowanie demonstracji.

**🎯 Następny krok:**
- Zmierzyć skuteczność na 30 sprawach i dopracować README.

---

## 2026-09-22 — Robert Dębicki

**✅ Zrobione:**
- Dodano responsywny interfejs od pytania przez wynik do cytatu źródłowego.
- Dodano stany braku faktur i braku rozbieżności, historię analiz i pomoc.
- Sprawdzono główną ścieżkę oraz widok mobilny w przeglądarce.

**🚧 W toku / nie wdrożone:**
- Pytania uzupełniające i końcowy raport ewaluacyjny.

**🎯 Następny krok:**
- Dodać odpowiedzi na pytania o gotową analizę.

---

## 2026-09-22 — Robert Dębicki

**✅ Zrobione:**
- Dodano interpretację prostych pytań o klienta, okres i próg rozbieżności.
- Dodano API tworzenia i odczytu analiz oraz spraw z zapisanymi wynikami.
- Rozróżniono brak faktur, brak rozbieżności i sprawy wymagające przeglądu.

**🚧 W toku / nie wdrożone:**
- Interfejs przeglądarkowy, pytania uzupełniające i raport ewaluacyjny.

**🎯 Następny krok:**
- Zbudować interfejs od pytania do źródła.

---

## 2026-09-22 — Robert Dębicki

**✅ Zrobione:**
- Dodano wyjaśniacz z walidacją cytatów, kwot i przyczyn oraz uczciwym `unknown`.
- Dodano adapter Groq i jawną symulację modelu dla danych demonstracyjnych.
- Sprawdzono wszystkie 30 spraw syntetycznych bez wywołania zewnętrznego API.

**🚧 W toku / nie wdrożone:**
- Interpretacja pytań, API, interfejs i końcowy raport ewaluacyjny.

**🎯 Następny krok:**
- Zbudować interpretację pytań i API analizy.

---

## 2026-09-22 — Robert Dębicki

**✅ Zrobione:**
- Dodano indeks fragmentów dokumentów z lokalizatorem i SQLite FTS5.
- Dodano wyszukiwanie hybrydowe w granicach projektu oraz oznaczanie niedostępnych źródeł.
- Dodano opcjonalny model embeddingów, tryb bez modelu i testy wyszukiwania.

**🚧 W toku / nie wdrożone:**
- Wyjaśniacz, API i interfejs przeglądarkowy.

**🎯 Następny krok:**
- Zbudować wyjaśniacz z kontrolą cytatów i obsługą braku dowodu.

---

## 2026-09-22 10:36 — Robert Dębicki

**✅ Zrobione:**
- Dodano deterministyczny detektor różnic netto dla właściwych transz.
- Uwzględniono faktury częściowe, zatwierdzone zmiany, filtry klienta i okresu oraz progi.
- Dodano polecenie demonstracyjne i testy detektora.

**🚧 W toku / nie wdrożone:**
- Indeks dokumentów, agent wyjaśniający i interfejs przeglądarkowy.

**🎯 Następny krok:**
- Zbudować indeks dowodów i wyszukiwanie hybrydowe z etapu 3.

---

## 2026-09-22 10:22 — Robert Dębicki

**✅ Zrobione:**
- Zatwierdzono brief, design, architekturę i plan budowy.
- Dodano schemat SQLite, generator 30 spraw syntetycznych oraz zestaw ewaluacyjny.
- Dodano testy spójności danych, odtwarzalności i reguły zatwierdzonych zmian.

**🚧 W toku / nie wdrożone:**
- Interfejs, detektor rozbieżności i agent wyjaśniający nie są jeszcze zaimplementowane.

**🎯 Następny krok:**
- Zbudować deterministyczny detektor rozbieżności z etapu 2 planu.

---
