(() => {
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