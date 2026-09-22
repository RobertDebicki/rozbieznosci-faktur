# Design system — Rozbieżności faktur

Źródło: przekazany przez użytkownika mockup `Rozbieżności faktur.dc.html`
(21.09.2026). Plik `support.js` jest środowiskiem uruchomieniowym podglądu,
nie częścią docelowej aplikacji.

## Kierunek

Spokojny interfejs dla działu księgowego: jasne, ciepłe tło, atramentowy tekst,
niebieski akcent i czytelne kwoty. Ekran startowy daje dwie równorzędne drogi:
pytanie naturalnym językiem albo formularz z okresem i klientem. Wynik prowadzi
od podsumowania przez sprawę do konkretnego fragmentu dokumentu.

## Tokeny CSS

Poniższe zmienne zachowują wartości z mockupu. Można je umieścić w globalnym
arkuszu stylów niezależnie od później wybranego frameworka.

```css
:root {
  /* Typografia */
  --font-body: "IBM Plex Sans", system-ui, sans-serif;
  --font-heading: "Source Serif 4", Georgia, serif;
  --font-numeric: "IBM Plex Mono", ui-monospace, monospace;

  /* Powierzchnie i tekst */
  --color-page: #F6F4EF;
  --color-surface: #FFFFFF;
  --color-surface-subtle: #FBFAF7;
  --color-surface-document: #FDFCFA;
  --color-surface-muted: #F1EEE7;
  --color-text: #1C1B18;
  --color-text-strong: #35312A;
  --color-text-body: #4A463D;
  --color-text-secondary: #5B564C;
  --color-text-muted: #8A8377;
  --color-border: #DED8CD;
  --color-border-soft: #E3DED4;
  --color-divider: #EDE8DF;

  /* Akcent */
  --color-primary: oklch(0.44 0.07 235);
  --color-primary-hover: oklch(0.36 0.075 235);
  --color-primary-text: oklch(0.38 0.07 235);
  --color-primary-soft: oklch(0.97 0.012 235);

  /* Stany: każdy status ma etykietę tekstową; kolor jest dodatkiem */
  --color-explained-text: oklch(0.40 0.08 150);
  --color-explained-bg: oklch(0.96 0.03 150);
  --color-explained-border: oklch(0.88 0.05 150);
  --color-unknown-text: oklch(0.42 0.10 55);
  --color-unknown-bg: oklch(0.96 0.035 75);
  --color-unknown-border: oklch(0.88 0.06 75);
  --color-unavailable-text: #3D3A33;
  --color-unavailable-bg: #EDEAE3;
  --color-unavailable-border: #D3CCBE;
  --color-positive-difference: oklch(0.45 0.13 30);
  --color-negative-difference: oklch(0.42 0.08 150);
  --color-evidence-highlight: oklch(0.94 0.06 95);

  /* Odstępy, promienie i cień */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --radius-control: 9px;
  --radius-card: 12px;
  --radius-feature: 14px;
  --radius-pill: 999px;
  --shadow-question: 0 1px 2px rgba(28, 27, 24, .04),
                     0 10px 30px -18px rgba(28, 27, 24, .25);

  /* Szerokości treści */
  --width-start: 880px;
  --width-narrow: 720px;
  --width-content: 1160px;
  --width-source-modal: 760px;
}
```

Fonty z eksportu: `Source Serif 4` 400/600/700, `IBM Plex Sans` 400/500/600,
`IBM Plex Mono` 400/500. Nagłówek startowy 44 px/1.12, nagłówki widoków
34 px, nagłówki kart 20–23 px, treść 16–19 px, opisy pomocnicze 13–15 px.
Kwoty i identyfikatory dokumentów są w kroju monospace, z cyframi tablicowymi.

## Układ i komponenty

- Górny pasek: znak „R”, nazwa produktu, „Nowa analiza”, „Historia”, „Pomoc”
  i użytkownik. Pozycja sticky, białe tło, dolna linia.
- Start: główne pytanie w dużym polu, przykłady pytań, a poniżej formularz
  „Sprawdź rozbieżności” z gotowymi okresami, datami i klientem.
- Doprecyzowanie klienta: osobny widok z wyborem firmy i identyfikatorami.
- Analiza: opis wykonywanego etapu, pasek postępu i możliwość przerwania.
- Wyniki: potwierdzenie zrozumianych filtrów, podsumowanie, liczby, filtry statusu,
  lista spraw i pytania uzupełniające.
- Sprawa: dwie kolumny na szerokim ekranie — wyliczenie, wyjaśnienie i dowody
  po lewej; pytania i metadane sprawy po prawej.
- Źródło: modal z tytułem, lokalizatorem i wyróżnionym fragmentem dokumentu.
- Stany odrębne: brak faktur do porównania, faktury bez rozbieżności,
  rozbieżność wyjaśniona, przyczyna nieustalona, niedostępny dokument.

Mockup nie podaje liczbowych breakpointów. Używa zawijania flex i siatki
`repeat(auto-fit, minmax(320px, 1fr))`. Implementacja powinna zachować kolejność
treści na małym ekranie; szczególnie trzeba sprawdzić nawigację i prawą kolumnę,
która na desktopie jest sticky. Animacje wejścia trwają około 200–260 ms;
ruch należy wyłączyć przy `prefers-reduced-motion`.

## Granica między designem a działaniem

Eksport jest klikalnym prototypem z wpisanymi na sztywno sprawami, filtrami
i odpowiedziami. Nie jest zatwierdzoną implementacją: daty, kwoty, odpowiedzi
na dalsze pytania i komunikaty o księgowaniu muszą wynikać z danych i dowodów.
Pozycje „Historia” i „Pomoc” w mockupie nie mają zaimplementowanych akcji;
ich zakres trzeba rozstrzygnąć w architekturze. Procent „pewności” nie jest
skalibrowany w prototypie; jeśli pojawi się w produkcie, musi mieć jasną
definicję i podstawę pomiaru.
