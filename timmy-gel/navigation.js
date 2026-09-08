(() => {
  if (window.location.protocol !== 'file:') {
    const current = new URL(window.location.href);
    const selected = current.searchParams.get('azienda') === 'timmy-gel';
    let allowed = selected;
    try {
      if (selected) window.sessionStorage.setItem('timmy-gel-selected', '1');
      allowed = allowed || window.sessionStorage.getItem('timmy-gel-selected') === '1';
    } catch {
      if (selected) {
        document.querySelectorAll('a[href]').forEach((link) => {
          const destination = new URL(link.href, current);
          if (destination.origin === current.origin && destination.pathname.endsWith('.html')) {
            destination.searchParams.set('azienda', 'timmy-gel');
            link.href = destination.href;
          }
        });
      }
    }
    if (!allowed) {
      window.location.replace('https://www.sanvincenzoservice.it/gruppo/');
      return;
    }
  }
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let navigationTimer;
  let recoveryTimer;

  const resetTransition = () => {
    window.clearTimeout(navigationTimer);
    window.clearTimeout(recoveryTimer);
    document.body.classList.remove('is-leaving');
  };

  window.addEventListener('pageshow', resetTransition);
  window.addEventListener('pagehide', resetTransition);

  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (reducedMotion.matches || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;

    const destination = new URL(link.href, window.location.href);
    const currentDirectory = new URL('.', window.location.href);
    if (!['file:', 'http:', 'https:'].includes(destination.protocol)) return;
    if (destination.origin !== currentDirectory.origin || new URL('.', destination).pathname !== currentDirectory.pathname) return;
    if (!destination.pathname.endsWith('.html') || destination.pathname === window.location.pathname) return;

    event.preventDefault();
    resetTransition();
    document.body.classList.add('is-leaving');
    navigationTimer = window.setTimeout(() => {
      window.location.assign(destination.href);
    }, 180);
    recoveryTimer = window.setTimeout(resetTransition, 1500);
  });
})();