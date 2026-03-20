# Data Model Iniziale

## Bounded contexts

### Identity and Access
- Company
- User
- InviteToken

### Fleet and Compliance
- Vehicle
- RoutePreference
- ComplianceDocument

### Load Marketplace
- Load
- Auction
- Bid

### Trip Execution
- Trip
- TripStatusEvent
- ChatMessage

## Relazioni chiave

- Una Company possiede molti User.
- Una Company puo emettere molti InviteToken.
- Una Company possiede molti Vehicle.
- Una Company definisce molte RoutePreference.
- Una Company carica molti ComplianceDocument.
- Una Company pubblica molti Load.
- Un Load puo avere al massimo una Auction.
- Un Load puo generare al massimo un Trip.
- Una Auction raccoglie molti Bid.
- Un Trip puo essere assegnato a un solo User con ruolo driver.
- Un Trip ha molti TripStatusEvent.
- Un Trip ha molti ChatMessage.
- Un InviteToken puo essere consumato una sola volta da un nuovo utente.

## Regole di dominio iniziali

- Un autista non puo esistere fuori da una Company, salvo pre-registrazione con invito.
- Un Load non puo entrare in asta se la Company ha documenti bloccanti scaduti.
- Un Trip non puo essere creato se il Load non e assegnato.
- Un Vehicle ADR puo essere richiesto dal Load tramite flag dedicato.
- Gli eventi automatici di geofencing vengono salvati in TripStatusEvent con source `system`.
- I messaggi generati automaticamente dalla piattaforma sono marcati con `is_system_generated=true`.

## Entita rinviate a milestone successive

- Rating
- BlacklistEntry
- Invoice
- OCRDocument
- NotificationDelivery
- PriceSuggestion

Queste entita vanno aggiunte quando si attivano i moduli trust, monetizzazione e AI avanzata.
