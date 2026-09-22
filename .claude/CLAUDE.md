# CLAUDE.md — Rozbieznosci faktura vs wycena

## Wymagania i cel
Demonstracyjna aplikacja dla działu księgowego. Na danych syntetycznych wykrywa
różnice między fakturami a wycenami, szuka ich przyczyn w dokumentach projektowych
i mailach oraz pokazuje dowody. Użytkownik pracuje w przeglądarce, może zadać
proste pytanie o klienta i okres oraz pytania uzupełniające o wynik.

## Zaimplementowane funkcje
Etap 1: generator syntetycznej bazy, dokumentów i 30 spraw ewaluacyjnych.
Etap 2: deterministyczny detektor porównujący faktury netto z wyceną transzy.
Szczegóły i pliki są w `.Codex/AGENTS.md`.

## Architektura
Zatwierdzona architektura i przepływy użytkownika są w `.Codex/architecture.md`.

## Design system
Zatwierdzony mockup i tokeny CSS są w `.Codex/design-system.md`.

## Plan budowy
Plan zatwierdzony. Etapy 1 i 2 wykonane; następny jest indeks dowodów.

## Wazne decyzje

**14.09.2026 — dane wylacznie syntetyczne.** Repo ma byc publiczne i pokazywane
rekruterom. Realne dane klientów nie mogą trafić do publicznego repozytorium.

**14.09.2026 — model nie liczy.** Wykrycie rozbieznosci to odejmowanie i nalezy do SQL-a.
Model dostaje gotowa liczbe i szuka dla niej uzasadnienia w tekscie. Odwrotny podzial
prowadzi do zmyslonych kwot w raporcie finansowym.

**14.09.2026 — wyszukiwanie musi byc hybrydowe.** Same embeddingi nie znajda frazy
"aneks nr 3" ani kwoty "124 500 zl", bo liczby i numery nie maja sensownej reprezentacji
wektorowej. Konieczne wyszukiwanie pelnotekstowe obok wektorowego.
