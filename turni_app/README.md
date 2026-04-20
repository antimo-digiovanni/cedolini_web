# Turni Planner

App desktop PySide6 per velocizzare la compilazione del file Excel dei turni.

Funzioni incluse:
- apertura diretta del workbook Excel con ricarica e salvataggio
- salvataggio con backup automatico nella cartella _backup_turni accanto al file
- dashboard iniziale con settimana, firma e riepilogo rapido
- editor della settimana diviso per 1 turno, 2 turno e 3 turno
- editor separati per comandata sabato e comandata domenica
- pannello rapido laterale con nominativi trovati nel file e riempimento massivo delle celle selezionate
- export delle stampe in PDF e immagini JPG

Avvio rapido su Windows:
- usa avvia_turni_planner.bat dalla root del progetto

Avvio manuale:

```powershell
.venv\Scripts\python.exe -m turni_app "C:\Users\antim\Il mio Drive\TURNI\Turni 2026\Week 13\Turni Lavoro.xlsx"
```

Note operative:
- se un valore weekend non viene cambiato, l'app conserva il valore originale del foglio, incluse eventuali formule
- le celle vuote possono essere riempite in blocco dal pannello rapido con nominativi o con il valore SCORRIMENTO
- dopo ogni salvataggio l'app rilegge il file Excel per mostrare il contenuto effettivo appena scritto
- i pulsanti di esportazione salvano sia PDF sia JPG; se una comandata occupa piu pagine vengono creati JPG numerati come _01, _02, ...