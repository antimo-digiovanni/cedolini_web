# Gestionale Preventivi

Applicazione desktop Python per creare preventivi, assegnare un numero progressivo, gestire l'anagrafica clienti, tenere traccia dello stato del preventivo e del pagamento, e generare copie PDF ed Excel.

## Funzioni incluse

- Creazione e modifica preventivi
- Anagrafica clienti con referente, email, telefono e indirizzo
- Righe dettaglio del preventivo con quantita, prezzo unitario e totale
- Numero progressivo automatico
- Stati preventivo: Da confermare, Confermato, Lavoro fatto
- Stati pagamento: Pending, Pagato
- Riepilogo conteggi in dashboard
- Esportazione PDF del preventivo
- Esportazione Excel del singolo preventivo
- Esportazione Excel del registro preventivi
- Generazione AI di testo introduttivo e punti inclusi tramite OpenAI
- Database locale SQLite
- Script di build per file .exe Windows

## Avvio

1. Installa le dipendenze:
   pip install -r requirements.txt
2. Avvia il programma:
   python app.py

## AI OpenAI

L'app puo generare il testo introduttivo e i punti inclusi del preventivo tramite OpenAI.

1. Apri l'app
2. Usa il riquadro AI
3. Inserisci la tua chiave API OpenAI
4. Scegli il modello da usare oppure lascia il predefinito `gpt-5.4`

La chiave viene salvata localmente nel file `app_settings.json` del progetto.

## Build Windows

Per generare l'eseguibile Windows:

1. Installa le dipendenze del progetto
2. Esegui lo script PowerShell:
   .\build_windows.ps1

L'eseguibile verra creato nella cartella dist\GestionalePreventivi.

## Struttura

- `app.py`: punto di ingresso
- `preventivi_app/database.py`: persistenza SQLite
- `preventivi_app/ui.py`: interfaccia PySide6
- `preventivi_app/pdf_service.py`: generazione PDF
- `preventivi_app/excel_service.py`: generazione Excel
- `preventivi_app/ai_service.py`: generazione testi via OpenAI
- `preventivi_app/settings_service.py`: impostazioni locali applicazione
- `build_windows.ps1`: build PyInstaller per Windows
