---
name: Portale San Vincenzo S.r.l.
description: Area riservata per dipendenti e amministrazione di San Vincenzo S.r.l. (cedolini, marcature, turni, patrimonio).
colors:
  accent: "#3451d1"
  accent-hover: "#2a43b0"
  accent-active: "#233a99"
  accent-ink: "#22378f"
  accent-tint: "#eef1fd"
  accent-tint-2: "#dfe5fb"
  bg: "#f6f8fb"
  surface: "#ffffff"
  surface-2: "#f9fafc"
  surface-3: "#f1f4f8"
  border: "#e3e8ee"
  border-strong: "#cfd7e1"
  ink: "#1a2233"
  ink-2: "#384255"
  muted: "#5b6678"
  subtle: "#8a94a6"
  success: "#0e7a4a"
  success-bg: "#e6f5ed"
  success-border: "#b9e2cb"
  warning: "#8f5300"
  warning-bg: "#fff4e0"
  warning-border: "#f6d9a6"
  warning-fill: "#f5b544"
  danger: "#be2530"
  danger-bg: "#fdecec"
  danger-border: "#f5c2c5"
  info: "#145f93"
  info-bg: "#e7f2fa"
  info-border: "#bcdcf0"
  neutral: "#475467"
  neutral-bg: "#eef1f5"
typography:
  headline:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 750
    lineHeight: 1.25
    letterSpacing: "-0.022em"
  page-title:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 750
    lineHeight: 1.25
    letterSpacing: "-0.022em"
  title:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  panel-title:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  kpi:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    letterSpacing: "-0.02em"
    fontFeature: "'tnum'"
  body:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "-0.003em"
    fontFeature: "'cv11', 'ss01'"
  table:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    fontFeature: "'tnum'"
  label:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 650
  table-head:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    letterSpacing: "0.02em"
  nav-group:
    fontFamily: "Manrope, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    letterSpacing: "0.06em"
rounded:
  xs: "6px"
  sm: "8px"
  md: "10px"
  lg: "14px"
  auth: "16px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "24px"
  3xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-primary-active:
    backgroundColor: "{colors.accent-active}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
    height: "40px"
  button-secondary-hover:
    backgroundColor: "{colors.surface-2}"
  button-outline-primary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.accent}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
  button-outline-primary-hover:
    backgroundColor: "{colors.accent-tint}"
    textColor: "{colors.accent-hover}"
  button-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    padding: "7px 14px"
  button-disabled:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.subtle}"
    rounded: "{rounded.sm}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
    height: "40px"
  input-disabled:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.muted}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "24px"
  table-head:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.muted}"
    typography: "{typography.table-head}"
    padding: "11px 14px"
  badge-success:
    backgroundColor: "{colors.success-bg}"
    textColor: "{colors.success}"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  badge-warning:
    backgroundColor: "{colors.warning-bg}"
    textColor: "{colors.warning}"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  badge-danger:
    backgroundColor: "{colors.danger-bg}"
    textColor: "{colors.danger}"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  badge-neutral:
    backgroundColor: "{colors.neutral-bg}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.pill}"
    padding: "3px 8px"
  sidebar-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "6px 10px"
  sidebar-item-hover:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.ink}"
  sidebar-item-active:
    backgroundColor: "{colors.accent-tint}"
    textColor: "{colors.accent-ink}"
  tabbar-item:
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    height: "50px"
  tabbar-item-active:
    textColor: "{colors.accent}"
---

# Design System: Portale San Vincenzo S.r.l.

> Fonte di verità: `portal/static/portal/portal-theme.css` (token `--sv-*` su `:root`). Questo file sostituisce `portal/DESIGN.md`, che resta nel repository come registro superato di un passaggio precedente e non va più seguito.

## Overview

**Creative North Star: "Il registro ben tenuto"**

Lo standard dei gestionali, eseguito con la cura di una dashboard alla Stripe: superficie bianca su fondo grigio-azzurro chiarissimo, navigazione laterale quieta a gruppi, tabelle precise con numeri tabulari, un solo accento indaco-blu. Il portale serve a fare una cosa al giorno (timbrare, aprire il cedolino, approvare una richiesta) in pochi tocchi, da desktop e da telefono; il tono visivo è quello di un registro aziendale in ordine, non di un prodotto che vuole farsi notare.

La densità è media: corpo a 15px, controlli a 40px su desktop e 44px su telefono, pannelli con 24px di respiro interno. La profondità è minima e ambientale: bordi da 1px fanno quasi tutto il lavoro, le ombre sono corte e servono solo a staccare il pannello dal fondo. Il colore è riservato: l'accento segna azione primaria, selezione e focus; verde, ambra e rosso parlano solo di stato.

Rifiuti confermati dal contratto di direzione e visibili nella build: niente gradienti blu, niente card che si sollevano all'hover, niente ombre pesanti, niente logo in filigrana (`.background-logo` è nascosto).

**Key Characteristics:**
- Fondo #f6f8fb, superfici bianche con bordo 1px e ombra corta.
- Un solo accento indaco-blu, più profondo del contratto per margine di contrasto.
- Manrope self-hosted, numeri tabulari in tabelle e KPI.
- Shell a tre parti: sidebar a gruppi, barra superiore sticky con sezione corrente, barra a schede in basso sotto i 992px.
- Stati in pillole tinte con filetto interno, mai blocchi saturi.
- Marchio sempre presente: logo, "San Vincenzo S.r.l." e il credito "Sistema sviluppato da Antimo Di Giovanni".

## Colors

Neutri freddi e luminosi, un indaco-blu deciso come unica voce, e quattro famiglie di stato tinte e smorzate.

### Primary
- **Indaco San Vincenzo** (`accent`): azioni primarie, link, voce attiva della sidebar e della barra a schede, focus ring, checkbox selezionate, barra di avanzamento, pagina attiva della paginazione. È volutamente più profondo dell'indaco del contratto (#3b5bdb): misura 6.5:1 su bianco e 6.1:1 sul fondo, contro 5.7:1 dell'originale, così il testo in accento (link, etichette dei bottoni outline-primary, tab attive) resta ben sopra AA anche su schermi di telefono all'aperto.
- **Indaco pieno / profondo** (`accent-hover`, `accent-active`): stati hover e premuto dei bottoni primari e dei link.
- **Inchiostro indaco** (`accent-ink`): testo su fondo tinto (voce attiva sidebar, badge primario, selezione testo, `code`). 9.3:1 su `accent-tint`.
- **Velo indaco** (`accent-tint`, `accent-tint-2`): fondo della voce attiva, avatar utente, icona dei modali di conferma, hover dei bottoni outline-primary, selezione testo.

### Neutral
- **Fondo registro** (`bg`): sfondo di pagina, login e pagine pubbliche.
- **Foglio** (`surface`): pannelli, sidebar, barra superiore (al 92% con sfocatura), modali, campi.
- **Foglio velato** (`surface-2`): intestazioni di tabella, header e footer di card e modali, hover di bottoni neutri e righe.
- **Foglio spento** (`surface-3`): hover della sidebar, campi disabilitati e readonly, bottoni disabilitati, binario delle nav-pills e della barra di avanzamento.
- **Filetto** (`border`): bordo di pannelli, divisori, separatori di shell.
- **Filetto deciso** (`border-strong`): bordo di campi, bottoni neutri e outline, paginazione.
- **Inchiostro** (`ink`): testo principale e titoli.
- **Inchiostro secondo** (`ink-2`): voci di sidebar, etichette di form, etichette KPI.
- **Grigio nota** (`muted`): testo secondario, intestazioni di tabella, footer, sottotitoli. 5.8:1 su bianco.
- **Grigio traccia** (`subtle`): solo icone della sidebar, titoli di gruppo del menu, placeholder e testo dei bottoni disabilitati. 3.1:1 su bianco: non usarlo per testo informativo.

### Stati
- **Verde conferma** (`success` + `-bg` + `-border`): esito positivo, approvazioni, inizio turno.
- **Ambra attesa** (`warning` + `-bg` + `-border`): in attesa, avvisi. `warning-fill` è il riempimento dei soli bottoni e superfici gialle, con testo #3d2600.
- **Rosso errore** (`danger` + `-bg` + `-border`): errori, rifiuti, eliminazioni, fine turno, logout all'hover.
- **Blu informazione** (`info` + `-bg` + `-border`): avvisi informativi.
- **Grigio stato** (`neutral`, `neutral-bg`): pillole neutre (`finance-pill`, badge secondari).

### Named Rules
**The One Accent Rule.** L'indaco è l'unico colore d'azione. Verde e rosso compaiono solo per stato semantico (successo/errore, approva/rifiuta, inizio/fine marcatura), mai per un normale salvataggio: "Salva", "Salva modifiche", "Segna come pagate" sono bottoni primari indaco. Le azioni scure di export diventano neutre.

**The Tinted Status Rule.** Lo stato si mostra in pillola tinta: fondo `-bg`, testo nel colore pieno, filetto interno `-border`. I riempimenti saturi restano ai bottoni d'azione.

## Typography

**Display Font:** Manrope (con -apple-system, Segoe UI, Roboto, Arial)
**Body Font:** Manrope (stessa famiglia, asse di peso variabile 200–800)

**Character:** Una sola grottesca geometrica e calda, self-hosted da `portal/static/portal/fonts/manrope-latin-wght-normal.woff2`; la gerarchia nasce dal peso (550, 650, 700, 750) e da un tracking leggermente negativo sui titoli, non da una seconda famiglia.

### Hierarchy
- **Headline** (750, 1.75rem, 1.25, -0.022em): h1 di pagina. 1.5rem sotto i 576px.
- **Page title** (750, 1.625rem): titolo nell'intestazione di pagina (`page-hero`), con sottotitolo `muted` a 15px e max 72ch. 1.375rem sotto i 992px, 1.5rem sotto i 576px nel contenuto.
- **Title** (700, 1.375rem): h2 nel contenuto; h3 1.25rem, h4 1.125rem, h5 1rem.
- **Panel title** (700, 1.0625rem, -0.01em): primo titolo di un pannello, titolo dei modali.
- **KPI** (700, 1.875rem, -0.02em, numeri tabulari): valori delle schede KPI.
- **Body** (400, 0.9375rem, 1.55): testo corrente; `small` a 0.8125rem.
- **Table** (0.875rem, numeri tabulari): celle di tabella.
- **Label** (650, 0.8125rem): etichette di form e testo dei bottoni (bottoni a 0.875rem).
- **Table head** (700, 0.75rem, 0.02em): intestazioni di colonna, in `muted`, senza maiuscolo forzato.
- **Nav group** (700, 0.6875rem, 0.06em, maiuscolo): solo i titoli di gruppo della sidebar (Personale, Cedolini, Presenze, Amministrazione, Account).

### Named Rules
**The Tabular Figures Rule.** Ogni numero che si confronta in colonna (tabelle, KPI, importi, orari) usa `font-variant-numeric: tabular-nums`.

**The Title Speaks Alone Rule.** Nessuna etichetta piccola sopra i titoli di pagina o di pannello. L'unico maiuscoletto del sistema è il titolo di gruppo della navigazione laterale.

## Layout

Shell a due colonne su desktop: sidebar sticky bianca da 256px a tutta altezza, con logo e ragione sociale in un blocco alto quanto la barra superiore; a destra, barra superiore sticky da 60px (bianco al 92% con sfocatura) che mostra "San Vincenzo S.r.l. / sezione corrente" e avatar con iniziali; sotto, contenuto con max 1440px e padding 28px 32px 40px; footer con filetto superiore, "© San Vincenzo S.r.l." a sinistra e "Sistema sviluppato da Antimo Di Giovanni" a destra.

Ritmo di spaziatura su passi di 4px: 4, 8, 12, 16, 20, 24, 32. Intestazione di pagina con 24px sotto; pannelli con 24px interni; griglie Bootstrap con gutter 1.5rem, ridotto a 1rem sotto i 576px.

Responsive (punti di rottura Bootstrap):
- **< 1200px:** gutter di pagina a 24px.
- **< 992px:** la sidebar sparisce; barra superiore da 56px con bottone menu 40px, logo e "San Vincenzo"; il menu completo apre un offcanvas (min(86vw, 320px)) con voci da 46px; compare la barra a schede fissa in basso (64px, 4–5 voci + "Altro"); pannelli a 18px interni e raggio 10px; footer centrato con spazio per la barra a schede.
- **< 768px:** campi a 16px di corpo (niente zoom automatico di iOS), controlli a 44px (piccoli 38–40px), modali con footer a bottoni distesi, tabelle fuori dai contenitori responsive rese scorrevoli.
- **< 576px:** pannelli a 16px interni, gutter 16px, paginazione centrata.
- **Puntatore grossolano:** voci di sidebar a 44px, checkbox più grandi.

Ogni bordo del viewport rispetta `env(safe-area-inset-*)`: barra superiore, barra a schede, offcanvas, footer, footer dei modali.

## Elevation & Depth

Sistema ibrido a prevalenza di bordi: ogni superficie ha un filetto da 1px e un'ombra corta e fredda (tinta rgba(16, 24, 40)), che separa senza sollevare. L'ombra non cambia mai all'hover: i pannelli sono fermi. Le ombre lunghe sono riservate a ciò che galleggia davvero (modali, offcanvas, dropdown, toast). Le barre di shell usano trasparenza e sfocatura invece dell'ombra.

### Shadow Vocabulary
- **Filo** (`--sv-shadow-xs`: `0 1px 2px rgba(16,24,40,0.05)`): campi, bottoni neutri e outline, paginazione, avvisi.
- **Foglio** (`--sv-shadow-sm`: `0 1px 2px rgba(16,24,40,0.04), 0 2px 6px rgba(16,24,40,0.04)`): pannelli, KPI, pill attiva.
- **Scheda d'accesso** (`--sv-shadow-md`: `0 2px 4px rgba(16,24,40,0.04), 0 8px 20px rgba(16,24,40,0.07)`): scheda di login e pagine pubbliche.
- **Sospeso** (`--sv-shadow-lg`: `0 8px 16px rgba(16,24,40,0.06), 0 24px 48px rgba(16,24,40,0.14)`): modali, offcanvas, dropdown, toast.
- **Anello di focus** (`--sv-ring`: `0 0 0 3px rgba(52,81,209,0.22)`): focus di bottoni e campi.

### Named Rules
**The Still Panel Rule.** I pannelli non si muovono e non cambiano ombra all'hover; l'interattività si dice con colore di fondo e bordo, in 120ms.

**The No Card In Card Rule.** Un pannello dentro un pannello non è una seconda scheda: diventa una sezione divisa da un filetto superiore (20px sopra e sotto), senza bordo laterale, ombra né fondo.

## Shapes

Angoli morbidi e misurati, che crescono con la dimensione dell'oggetto: 6px per controlli piccoli e voci di dropdown, 8px per bottoni, campi, voci di menu e paginazione, 10px per tabelle responsive, avvisi, controlli grandi e pannelli su telefono, 14px per pannelli, KPI e modali, 16px solo per la scheda d'accesso (login, recupero password, admin Django). Pillole a 999px per badge di stato e chip. L'avatar è l'unico cerchio. Gli header interni ai pannelli seguono il raggio esterno meno 1px.

## Components

### Buttons
Compatti, sicuri, con tre livelli chiari: primario indaco, neutro bianco, outline con colore solo nel testo.
- **Shape:** angoli morbidi (8px; piccoli 6px, grandi 10px), altezza 40px (34px piccoli, 48px grandi; 44px su telefono).
- **Primary:** fondo indaco, testo bianco, 650, 7px 14px, ombra indaco di 1px con luce interna sottile.
- **Hover / Focus:** hover e premuto scuriscono l'indaco; focus con anello indaco da 3px; transizioni di 120ms su colore, bordo e ombra.
- **Secondary / Light:** fondo bianco, bordo `border-strong`, testo inchiostro; hover `surface-2`.
- **Outline:** fondo bianco e bordo neutro per tutte le varianti; il colore semantico sta nel testo e nella tinta dell'hover.
- **Success / Danger:** pieni solo per azioni semantiche (approva, inizio/fine turno, elimina, conferma finale).
- **Disabled:** neutro, mai trasparenza del colore: fondo `surface-3`, bordo `border`, testo `subtle`, nessuna ombra, opacità piena.

### Chips
- **Style:** pillola 999px, 40px di altezza, bordo `border`, fondo bianco, testo `ink-2` 650 (scelta del dipendente su telefono).
- **State:** selezionato con fondo `accent-tint`, bordo #b8c4f2, testo `accent-ink`. Le pillole informative neutre (`finance-pill`) usano `neutral-bg` con filetto interno.

### Cards / Containers
- **Corner Style:** 14px (10px sotto i 992px).
- **Background:** bianco.
- **Shadow Strategy:** ombra Foglio, costante.
- **Border:** 1px `border`.
- **Internal Padding:** 24px (18px sotto i 992px, 16px sotto i 576px); header e footer su `surface-2`.
- **Pannello a fisarmonica:** se contiene solo il bottone di apertura, la riga stessa è il pannello (56px, 14px 20px, hover `surface-2`).
- **KPI:** stessa scheda, valore a numeri tabulari, etichetta `ink-2`, nota `muted`.

### Inputs / Fields
- **Style:** bordo 1px `border-strong`, fondo bianco, 8px, 40px di altezza, 8px 12px, ombra Filo; etichetta sopra a 13px/650 `ink-2`.
- **Focus:** bordo indaco e anello indaco 3px; hover bordo #b4bfcd; cursore di scrittura indaco.
- **Error / Disabled:** errore con bordo rosso e anello rosso tenue, messaggi in riquadro `danger-bg`; disabilitato e readonly su `surface-3` con testo `muted`.
- **Telefono:** corpo 16px, 44px di altezza. Nella scheda d'accesso i campi sono 48px con raggio 10px e icona a sinistra.

### Tables
- Testo 14px a numeri tabulari, celle 11px 14px, filetti orizzontali `border`, nessun bordo sull'ultima riga.
- Intestazione su `surface-2`, 12px/700 `muted`, senza a capo.
- Hover riga #f5f7fb; righe di stato con le tinte `-bg`.
- Contenitore responsive con bordo 1px e raggio 10px, scorrimento orizzontale contenuto.

### Navigation
- **Sidebar:** bianca, filetto destro; voci da 33px (44px al tocco) a 14px/550 `ink-2` con icona `subtle` da 18px; hover `surface-3`; attiva con fondo `accent-tint`, testo `accent-ink` 700 e icona indaco; titoli di gruppo 11px maiuscoli `subtle`; logout all'hover in tinta rossa.
- **Barra superiore:** sticky, 60px (56px su telefono), bianco al 92% con sfocatura, percorso "San Vincenzo S.r.l. / sezione" e avatar a iniziali su velo indaco.
- **Barra a schede (sotto 992px):** fissa in basso, bianco al 96% con sfocatura, voci verticali icona + etichetta 11px/650 `muted`; attiva in indaco; "Altro" apre l'offcanvas con il menu completo.
- **Tab e pills:** tab con sottolineatura indaco da 2px sulla voce attiva, scorrevoli senza barra; pills su binario `surface-3` con voce attiva bianca.

### Badges
- Pillola 999px, 3px 8px, 12px/650, fondo tinta, testo nel colore pieno, filetto interno. Il badge scuro (inchiostro) è l'unica eccezione a fondo pieno.

### Modali di conferma
- Raggio 14px, ombra Sospeso, backdrop rgba(15,23,42,0.45); icona in tessera 44px su velo indaco, nota opzionale in riquadro `surface-2`, Annulla outline neutro + conferma primaria (o rossa al secondo passaggio distruttivo).

### Scheda d'accesso
- Login e pagine pubbliche: header bianco con logo 40px e "San Vincenzo S.r.l.", scheda centrata max 420–440px, raggio 16px, ombra Scheda d'accesso, simbolo in tessera 52px su velo indaco, bottone pieno da 48px, footer con il credito.

## Do's and Don'ts

### Do:
- **Do** usare i token `--sv-*` di `portal-theme.css` per ogni colore, raggio e ombra; mai esadecimali nuovi nei template.
- **Do** dare a ogni salvataggio ordinario il bottone primario indaco; verde e rosso solo per stato semantico (approva/rifiuta, inizio/fine marcatura, elimina).
- **Do** trasformare un pannello annidato in sezione con filetto superiore.
- **Do** rendere neutri i bottoni disabilitati (`surface-3`, testo `subtle`, opacità piena).
- **Do** usare numeri tabulari in tabelle, KPI, importi e orari.
- **Do** su telefono: campi a 16px, controlli a 44px, safe-area su ogni bordo, barra a schede sotto i 992px.
- **Do** mostrare sempre il logo `portal/static/portal/logo.png`, "San Vincenzo S.r.l." e il credito "Sistema sviluppato da Antimo Di Giovanni" nel footer.
- **Do** esprimere gli stati in pillole tinte con filetto interno.

### Don't:
- **Don't** usare gradienti blu, logo in filigrana o pannelli che si sollevano all'hover.
- **Don't** usare ombre più lunghe di Foglio su elementi che non galleggiano.
- **Don't** mettere etichette maiuscole sopra i titoli di pagina o di pannello.
- **Don't** usare `subtle` per testo che l'utente deve leggere: è per icone, placeholder e stati spenti.
- **Don't** colorare di verde un "Salva" o di nero un'esportazione.
- **Don't** mettere una scheda con bordo e ombra dentro un'altra scheda.
- **Don't** usare caratteri di testo ("-", "+", "x") come icone: usare un'icona con etichetta accessibile.
