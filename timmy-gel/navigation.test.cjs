const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'navigation.js'), 'utf8');

function visit(address, stored, blocked = false) {
  const state = { redirect: null, stored, links: [{ href: 'https://www.timmygel.com/servizi.html' }] };
  const location = new URL(address);
  const window = {
    location: { href: address, protocol: location.protocol, replace: value => { state.redirect = value; } },
    sessionStorage: {
      getItem: () => { if (blocked) throw Error('blocked'); return state.stored; },
      setItem: (key, value) => { if (blocked) throw Error('blocked'); state.stored = value; }
    },
    matchMedia: () => ({ matches: false }),
    addEventListener() {}
  };
  const document = { addEventListener() {}, querySelectorAll: () => state.links };
  vm.runInNewContext(source, { window, document, URL });
  return state;
}

test('new visitors open the company directly, including deep links', () => {
  for (const filename of ['index.html', 'azienda.html', 'servizi.html', 'mezzi-magazzino.html', 'contatti.html']) {
    assert.equal(visit('https://www.timmygel.com/' + filename).redirect, null);
    const html = fs.readFileSync(path.join(__dirname, filename), 'utf8');
    assert.ok(html.includes('href="https://www.sanvincenzoservice.it/gruppo/"'));
  }
});
test('legacy choice links keep working without storing a selection', () => {
  const state = visit('https://www.timmygel.com/index.html?azienda=timmy-gel');
  assert.equal(state.redirect, null);
  assert.equal(state.stored, undefined);
  assert.equal(visit('https://www.timmygel.com/servizi.html', state.stored).redirect, null);
});
test('query parameters do not redirect visitors', () => {
  assert.equal(visit('https://www.timmygel.com/?azienda=other').redirect, null);
});
test('local preview stays usable', () => {
  assert.equal(visit('file:///C:/site/index.html').redirect, null);
});
test('navigation stays direct when session storage is blocked', () => {
  const state = visit('https://www.timmygel.com/index.html?azienda=timmy-gel', null, true);
  assert.equal(state.redirect, null);
  assert.equal(state.links[0].href, 'https://www.timmygel.com/servizi.html');
});