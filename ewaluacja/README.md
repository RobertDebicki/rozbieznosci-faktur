# Zestaw ewaluacyjny

Zestaw 30 spraw powstał przed implementacją agenta. Etykiety są w
`zestaw.jsonl`; pięć spraw ma przyczynę `unknown` i sprawdza, czy agent
potrafi powiedzieć „nie ustalono”. Wyniki kolejnych przebiegów trafią do
`wyniki/`.

## Co tu ma byc

1. **`zestaw.jsonl`** — 30 syntetycznych spraw z oczekiwaną przyczyną,
   różnicą w groszach i identyfikatorami dowodów.
2. **Pozycje bez mozliwej odpowiedzi** — 5. Sprawdzaja, czy system umie
   powiedziec "nie wiem" zamiast zmyslic. To najwazniejsza czesc zestawu.
3. **`wyniki/`** — raport z kazdego przebiegu.

## Co mierzymy

| Miara | Dlaczego |
|---|---|
| trafnosc | ile odpowiedzi zgadza sie z ustalona |
| halucynacje | ile odpowiedzi brzmi pewnie, ale jest nieprawdziwa |
| odsetek "nie wiem" | czy system umie sie przyznac do niewiedzy |
| koszt na sprawe | czy rozwiazanie jest oplacalne |
| latencja | czy da sie z tego korzystac |

## Dlaczego to jest wyroznik

Zmierzone 14.09.2026 na 78 unikalnych ogloszeniach AI z NoFluffJobs: ewaluacja
pojawia sie w 35% ogloszen, obserwowalnosc w 51%, wdrozenie produkcyjne w 69%.
Czyli czesciej niz SQL (23%) i czesciej niz LangChain (22%).

Prawie kazdy kandydat napisze "zbudowalem agenta RAG". Prawie nikt nie pokaze liczb.
