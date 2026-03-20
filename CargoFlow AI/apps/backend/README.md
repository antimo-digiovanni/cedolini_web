# Backend API

Backend FastAPI per CargoFlow AI.

## Avvio locale

1. Creare un ambiente virtuale Python 3.9+
2. Installare le dipendenze con `pip install -e .`
3. Copiare `.env.example` in `.env`
4. Eseguire le migrazioni con `python -m alembic upgrade head`
5. Avviare il server con `uvicorn app.main:app --reload`

## Database

- Default applicativo: SQLite locale per bootstrap rapido
- Target consigliato: PostgreSQL via `psycopg`
- Le tabelle non vengono piu create in automatico, salvo `AUTO_CREATE_TABLES=true`
- La sorgente di verita dello schema e Alembic in `alembic/versions/`

Esempio PostgreSQL:
- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cargoflow`

## Endpoints iniziali

- `GET /` metadata base servizio
- `GET /api/health` healthcheck
- `GET /api/domain/summary` riepilogo dei bounded context e delle entita principali
- `POST /api/auth/register/carrier` registrazione azienda e titolare
- `POST /api/auth/register/driver` registrazione autista tramite codice invito
- `POST /api/auth/login` autenticazione email/password
- `GET /api/auth/me` profilo autenticato corrente
- `POST /api/auth/invites` generazione codice invito per autisti o disponenti
- `GET /api/dashboard/carrier` dashboard MVP per trasportatore e disponente
- `GET /api/dashboard/driver` dashboard MVP per autista
- `GET /api/loads` elenco carichi aziendali con filtro opzionale per stato
- `GET /api/loads/{load_id}` dettaglio carico della propria azienda
- `POST /api/loads` creazione carico operativo per vettore/disponente
- `GET /api/auctions` elenco aste aziendali, opzionalmente solo live
- `GET /api/auctions/{auction_id}` dettaglio singola asta aziendale
- `POST /api/auctions` creazione asta su un carico dell'azienda

## Stato attuale

Lo scaffold include:
- configurazione centralizzata
- sessione database SQLAlchemy
- migrazione iniziale Alembic del dominio MVP
- compatibilita con SQLite locale e PostgreSQL
- autenticazione JWT con access e refresh token
- hash password e guard di ruolo
- inviti aziendali per onboarding autisti
- primi endpoint operativi per carichi aziendali
- primi endpoint operativi per aste collegate ai carichi
- route iniziali
- modello relazionale SQLAlchemy per il dominio MVP
- base pronta per sessioni DB, migrazioni e autenticazione
