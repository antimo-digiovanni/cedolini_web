# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- **Dipendenti di San Vincenzo S.r.l.**: usano il portale soprattutto dal telefono (Samsung, iPhone di ogni generazione) per timbrare entrata/uscita sul posto di lavoro e per consultare e scaricare cedolini e CUD.
- **Amministratori**: gestiscono dipendenti, caricamento cedolini/CUD, marcature, zone di lavoro, richieste fuori zona e ferie, turni e report. Lavorano da desktop ma controllano dashboard, richieste e marcature anche dal telefono.
- **Titolare**: usa la dashboard patrimonio / carta aziendale anche dal telefono per registrare spese e movimenti.

## Product Purpose
Portale interno di San Vincenzo S.r.l. per la gestione del personale: distribuzione riservata di cedolini e CUD, marcatura presenze con controllo zona, ferie, turni, report e patrimonio aziendale. Successo: ogni operazione si fa in pochi tocchi da qualsiasi telefono e da desktop, senza errori.

## Operating Context
- Accesso con username o email; recupero password via email; attivazione account tramite invito.
- Marcature fatte sul campo, in movimento, spesso all'aperto.
- Cedolini aperti come PDF serviti dal backend autorizzato.
- Deploy su Render (Django, WhiteNoise con manifest: i file statici vanno raccolti con `collectstatic` e committati in `staticfiles/`).

## Capabilities and Constraints
- Restyling solo visivo: logiche, URL, form, nomi dei campi, permessi e flussi non si toccano.
- Nessun file del progetto va perso.
- Il sito pubblico aziendale (`templates/site/`) è fuori ambito per il restyling del portale.

## Brand Commitments
- Nome dell'azienda: **San Vincenzo S.r.l.**
- Logo San Vincenzo (`portal/static/portal/logo.png`).
- Firma visibile: **"Sistema sviluppato da Antimo Di Giovanni"**.
- Il colore blu attuale non è vincolante.
- Preferenza confermata (2026-10-02): il portale segue lo standard dei gestionali, eseguito con cura e senza stravaganze. Riferimento di qualità: **Stripe Dashboard**.

## Evidence on Hand
- Logo, icone PWA (`portal/static/portal/icons/`), font Manrope self-hosted (`portal/static/portal/fonts/`).
- Nessun testimonial o dato commerciale da mostrare nel portale.

## Product Principles
1. Il telefono è il primo schermo: tocchi da almeno 44px, niente scroll orizzontale di pagina, form leggibili senza zoom.
2. Riservatezza e fiducia: dati personali e retributivi presentati con sobrietà.
3. Il compito prima dell'estetica: stato, azioni e numeri si leggono subito.
4. Coerenza: lo stesso componente ha lo stesso aspetto in tutte le pagine.
