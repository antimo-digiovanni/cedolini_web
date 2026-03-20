# Product Requirements

## Obiettivo

Creare una piattaforma mobile che digitalizza e rende affidabile lo scambio carichi nel settore autotrasporto, eliminando dispersione informativa, assenza di tracciabilita e scarsa sicurezza operativa dei canali informali.

## Tipi di utente

### 1. Trasportatore
Responsabilita principali:
- gestione profilo aziendale e flotta
- pubblicazione carichi e partecipazione ad aste
- assegnazione missioni agli autisti
- firma digitale documenti
- controllo fatturazione e pagamento
- supervisione compliance documentale

### 2. Autista
Responsabilita principali:
- consultazione missioni assegnate
- invio posizione e aggiornamenti operativi
- scansione DDT, CMR e documenti tramite OCR
- chat operativa essenziale
- conferma stati viaggio e prova consegna

## Funzionalita core

### A. Registrazione e profilazione
- onboarding aziendale con dati societari
- verifica automatica di P.IVA, iscrizione albo, assicurazione, DURC
- creazione parco mezzi con caratteristiche tecniche dettagliate
- preferenze di rotta e aree geografiche di interesse
- invito autisti tramite codice univoco aziendale

### B. Aste e ricerca carichi
- pubblicazione carico con scheda standardizzata
- aste al rialzo o ribasso con timer e regole configurabili
- filtri avanzati per tipologia mezzo, area, data, ADR e allestimenti
- smart matching con notifiche push solo a soggetti idonei
- cronologia offerte e audit trail completo

### C. Intelligenza Artificiale
- OCR da fotocamera per DDT, CMR, licenze e documenti viaggio
- compilazione automatica campi dai documenti acquisiti
- ricerca carichi con comandi vocali
- suggerimento prezzi etici basati su dati storici, distanza, urgenza e compatibilita mezzo
- scoring di matching tra mezzo, tratta, affidabilita e prossimita geografica

### D. Chat e comunicazione
- chat per viaggio con scheda fissa sempre visibile
- messaggistica contestuale tra trasportatore e autista
- eventi automatici in chat generati dal sistema
- geofencing per stati automatici: in arrivo, caricato, in transito, scaricato

## Sicurezza e affidabilita
- rating bilaterale su puntualita, integrita merce e tempi di pagamento
- blacklist di utenti o aziende non affidabili
- blocco automatico pubblicazione o assegnazione se documenti scaduti
- audit log per azioni sensibili
- firma elettronica dei documenti rilevanti

## Monetizzazione
- fee per transazione vinta in asta
- abbonamento premium per visibilita e analytics
- servizi finanziari di anticipo fatture e factoring

## KPI iniziali
- tempo medio assegnazione carico
- tasso di conversione notifica > offerta
- tasso completamento missioni senza intervento manuale
- percentuale documenti processati via OCR
- numero contestazioni per viaggio
- tempo medio pagamento

## Confini MVP

### Inclusi nel MVP
- autenticazione e onboarding base
- profilo trasportatore e autista
- mezzi, rotte preferite e documenti aziendali
- pubblicazione carichi, ricerca e aste realtime
- missioni con tracking e geofencing
- chat per viaggio
- upload documenti con OCR
- rating e blocchi compliance documentale

### Esclusi dal MVP iniziale
- factoring operativo reale con partner finanziario
- integrazioni EDI avanzate
- marketplace internazionale multi-lingua completo
- pricing AI completamente autonomo senza supervisione
