# CargoFlow AI

Piattaforma digitale mobile-first per professionalizzare lo scambio carichi nel settore autotrasporto, sostituendo flussi frammentati basati su gruppi WhatsApp con un ecosistema sicuro, tracciato e assistito da Intelligenza Artificiale.

## Visione

CargoFlow AI connette trasportatori e autisti in un unico sistema operativo per:
- pubblicazione e assegnazione carichi
- aste in tempo reale
- tracking missione e geofencing
- OCR documentale e automazione operativa
- reputazione, verifiche documentali e blacklist

## Struttura iniziale del repository

- `docs/` contiene visione prodotto, architettura e roadmap
- `apps/mobile/` ospitera l'app mobile per trasportatori e autisti
- `apps/backend/` ospitera API, business logic, aste, matching e AI orchestration
- `packages/shared/` ospitera modelli condivisi, contratti API e utility comuni

## Stato attuale dello scaffold

- `apps/backend/` contiene una API FastAPI iniziale con route di healthcheck e riepilogo dominio
- `apps/backend/app/models/domain.py` contiene il primo modello relazionale SQLAlchemy del MVP
- `apps/mobile/` contiene una base Expo React Native con flusso auth collegabile al backend
- `apps/mobile/` persiste localmente sessione e base URL API, con bootstrap automatico tramite `/api/auth/me`
- `apps/mobile/` include dashboard MVP distinte per Trasportatore e Autista, alimentate per ora da dati mock strutturati
- `packages/shared/` contiene tipi condivisi del dominio per mobile e integrazioni future
- `docs/data-model.md` dettaglia bounded context, relazioni e regole di dominio iniziali

## Stack consigliato per il MVP

- App mobile: React Native con Expo
- Backend: Python FastAPI oppure Django Ninja per API e pannello operativo
- Database: PostgreSQL con PostGIS per query geografiche
- Realtime: WebSocket o Supabase Realtime per aste e tracking
- AI/OCR: servizi modulari con OCR, speech-to-text e motore di matching/ranking
- Storage documenti: S3 compatibile
- Autenticazione: JWT + refresh token + inviti aziendali

## Macro-moduli MVP

1. Registrazione aziende e autisti con verifica documentale.
2. Pubblicazione carichi e ricerca guidata.
3. Aste realtime con timer e storico offerte.
4. Missione operativa con tracking posizione e stati viaggio.
5. Chat contestuale legata alla scheda viaggio.
6. OCR per DDT/CMR e caricamento documenti.
7. Rating, blacklist e controlli di compliance.

## Prossimi passi

1. Validare stack tecnico e confini MVP.
2. Disegnare data model e permessi.
3. Avviare scaffold di mobile app e backend API.
4. Implementare autenticazione, inviti e onboarding.
5. Sviluppare marketplace carichi, aste e missioni.

## Bootstrap locale

### Mobile

1. Entrare in `apps/mobile`
2. Installare dipendenze con `npm install`
3. Avviare con `npm run start`
4. Inserire nella UI il base URL del backend FastAPI raggiungibile dal simulatore

### Backend

1. Entrare in `apps/backend`
2. Creare un virtualenv Python 3.11+
3. Installare dipendenze con `pip install -e .`
4. Avviare con `uvicorn app.main:app --reload`
