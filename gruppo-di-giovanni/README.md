# Ingresso Gruppo Di Giovanni

- Pagina pubblica Django: `/gruppo/`, raggiungibile volontariamente dai collegamenti nei siti aziendali.
- San Vincenzo apre direttamente homepage e pagine pubbliche, senza filtro o scelta di sessione. Il vecchio link `/azienda/san-vincenzo/` resta compatibile e apre `/sito-web/` senza scrivere nella sessione.
- Login, portale e comportamento degli utenti autenticati restano invariati.
- Timmy Gel apre direttamente tutte le pagine. `navigation.js` gestisce soltanto le transizioni; il collegamento al gruppo e presente nell'HTML di ogni pagina e funziona anche senza JavaScript.
- Eurofrozen e Antimo Petroli restano in preparazione: i loro domini non sono stati forniti o configurati.
- Nessun redirect basato sulla provenienza da Google. Non viene garantita la posizione o la comparsa nei risultati di ricerca.
- Distribuire `index.html` e i quattro loghi accanto a questo file. Le anteprime PNG non servono al deploy. Il logo San Vincenzo usa l'asset pubblico gia esistente.
- Test: `python manage.py test portal.test_group_gateway` e `node --test timmy-gel/navigation.test.cjs`.