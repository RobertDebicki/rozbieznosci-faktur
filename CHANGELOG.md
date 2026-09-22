# Changelog

Zapis zmian w projekcie — najnowsze wpisy na górze.

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
