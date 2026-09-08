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

test('new visitors enter through the group, including deep links', () => {
  assert.equal(visit('https://www.timmygel.com/contatti.html').redirect, 'https://www.sanvincenzoservice.it/gruppo/');
});
test('company selection opens Timmy Gel and persists for navigation', () => {
  const state = visit('https://www.timmygel.com/index.html?azienda=timmy-gel');
  assert.equal(state.redirect, null);
  assert.equal(state.stored, '1');
  assert.equal(visit('https://www.timmygel.com/servizi.html', state.stored).redirect, null);
});
test('unrecognized choices do not bypass the group', () => {
  assert.ok(visit('https://www.timmygel.com/?azienda=other').redirect);
});
test('local preview stays usable', () => {
  assert.equal(visit('file:///C:/site/index.html').redirect, null);
});
test('selection remains usable when session storage is blocked', () => {
  const state = visit('https://www.timmygel.com/index.html?azienda=timmy-gel', null, true);
  assert.equal(state.redirect, null);
  assert.match(state.links[0].href, /azienda=timmy-gel/);
});