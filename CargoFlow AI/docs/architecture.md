# Technical Architecture

## Scelta architetturale proposta

Si consiglia una architettura mobile-first con backend modulare e servizi verticali per realtime, geolocalizzazione e AI.

## Componenti principali

### Mobile App
Unica app con esperienza differenziata per ruolo:
- flusso Trasportatore
- flusso Autista
- accesso tramite autenticazione e ruolo aziendale

Scelta consigliata:
- React Native con Expo per velocita di rilascio
- navigazione role-based
- offline cache per missioni e documenti recenti

### Backend API
Responsabilita:
- autenticazione, ruoli, permessi e inviti
- gestione aziende, flotte, autisti e documenti
- pubblicazione carichi e aste
- missioni, chat, rating, blacklist
- compliance documentale e audit

Scelta consigliata:
- FastAPI per API tipizzate e asincrone
- PostgreSQL come database principale
- Redis per code brevi, cache e timer aste

### Realtime Engine
Responsabilita:
- broadcast offerte asta
- aggiornamento timer
- stato missione in tempo reale
- eventi chat e tracking

Tecnologie possibili:
- WebSocket nativo lato backend
- Redis pub/sub
- eventuale broker eventi per scalabilita

### AI Services
Servizi separati per limitare accoppiamento:
- OCR service per estrazione documenti
- voice command service per speech-to-text
- matching engine per compatibilita carico/mezzo
- price intelligence per suggerimenti economici

### Document Storage
- object storage compatibile S3
- bucket separati per documenti aziendali, documenti missione e allegati chat
- firma hash e metadati per audit

## Modello dominio iniziale

Entita principali:
- Company
- User
- DriverProfile
- CarrierProfile
- Vehicle
- VehicleEquipment
- RoutePreference
- ComplianceDocument
- Load
- Auction
- Bid
- Trip
- TripStop
- TripStatusEvent
- ChatThread
- ChatMessage
- OCRDocument
- Rating
- BlacklistEntry
- Invoice

## Flussi critici

### 1. Onboarding azienda
1. registrazione account
2. inserimento dati aziendali
3. upload documenti
4. verifica automatica e manuale fallback
5. attivazione profilo trasportatore

### 2. Invito autista
1. il trasportatore genera codice invito
2. l'autista si registra con il codice
3. il backend associa autista all'azienda
4. l'autista vede solo missioni e strumenti operativi consentiti

### 3. Assegnazione carico
1. il trasportatore pubblica il carico
2. il sistema calcola matching su mezzo, rotta e prossimita
3. invio notifiche push ai soggetti compatibili
4. apertura asta e raccolta offerte
5. assegnazione automatica o manuale
6. generazione missione

### 4. Esecuzione missione
1. autista riceve missione
2. app invia posizione periodica
3. geofencing aggiorna stati
4. documenti vengono acquisiti via OCR
5. chiusura missione con prova di consegna

## Sicurezza
- autenticazione con access token e refresh token
- autorizzazione role-based e company-scoped
- cifratura documenti sensibili at-rest e in transit
- audit trail per pubblicazione carichi, offerte, assegnazioni e verifiche
- controllo scadenza documenti prima di consentire operazioni critiche

## Roadmap tecnica suggerita

### Fase 1
- monorepo
- autenticazione e data model base
- API aziende, utenti, flotte, documenti

### Fase 2
- marketplace carichi
- matching engine v1 basato su regole
- aste realtime

### Fase 3
- missioni operative
- tracking GPS e geofencing
- chat contestuale

### Fase 4
- OCR documentale
- voice assistant v1
- analytics e price intelligence
