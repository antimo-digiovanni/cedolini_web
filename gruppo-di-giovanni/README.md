# Ingresso Gruppo Di Giovanni

- Pagina pubblica Django: `/gruppo/`; la radice anonima rimanda qui.
- I visitatori delle pagine pubbliche San Vincenzo passano dal selettore. La scelta `/azienda/san-vincenzo/` salva la selezione nella sessione Django e apre `/sito-web/`.
- Login, portale, richieste POST e utenti autenticati restano esclusi dal filtro.
- Timmy Gel usa `navigation.js`: i nuovi visitatori HTTP/HTTPS passano dal gruppo; `?azienda=timmy-gel` salva la scelta nella sessione della scheda. Richiede JavaScript; le anteprime locali restano libere.
- Eurofrozen e Antimo Petroli restano in preparazione: i loro domini non sono stati forniti o configurati.
- Il filtro e uguale per tutti i visitatori, senza distinguere Google. Non garantisce la posizione o la comparsa nei risultati di ricerca.
- Distribuire `index.html` e i quattro loghi accanto a questo file. Le anteprime PNG non servono al deploy. Il logo San Vincenzo usa l'asset pubblico gia esistente.
- Test: `python manage.py test portal.test_group_gateway` e `node --test timmy-gel/navigation.test.cjs`.