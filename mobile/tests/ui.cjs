/* Interaction checks against the actual Expo web export, not a mock App. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { JSDOM, ResourceLoader, VirtualConsole } = require('jsdom');

test('exported app supports reviewed entry and invalidates stale calculations', async () => {
  const root = path.resolve(__dirname, '../dist');
  class LocalAssets extends ResourceLoader {
    fetch(url) {
      const parsed = new URL(url);
      assert.equal(parsed.origin, 'http://slipsavvy.test');
      const file = path.resolve(root, '.' + decodeURIComponent(parsed.pathname));
      assert.ok(file.startsWith(root + path.sep));
      return fs.readFile(file);
    }
  }
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', error => errors.push(error));
  const dom = new JSDOM(await fs.readFile(path.join(root, 'index.html'), 'utf8'), {
    url: 'http://slipsavvy.test/', runScripts: 'dangerously',
    resources: new LocalAssets(), pretendToBeVisual: true, virtualConsole,
    beforeParse(window) {
      window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {},
        addEventListener() {}, removeEventListener() {} });
      window.scrollTo = () => {};
    },
  });
  const { window } = dom;
  const document = window.document;
  const tick = () => new Promise(resolve => setTimeout(resolve, 30));
  const byId = id => document.querySelector(`[data-testid="${id}"]`);
  const click = async id => { assert.ok(byId(id), `missing ${id}`); byId(id).click(); await tick(); };
  const fill = async (id, value) => {
    const input = byId(id);
    assert.ok(input, `missing input ${id}`);
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(input, value);
    input.dispatchEvent(new window.Event('input', { bubbles: true }));
    await tick();
  };
  try {
    const deadline = Date.now() + 15000;
    while (!byId('add') && Date.now() < deadline && !errors.length) await tick();
    assert.deepEqual(errors.map(e => e.message), []);
    assert.ok(byId('add'), 'application booted');
    assert.match(document.body.textContent, /Entries stay in memory/);
    await click('tab-learn');
    assert.match(document.body.textContent, /4\.67%/);
    await click('tab-check');

    await click('add'); await click('review');
    assert.ok(byId('error'), 'blank selection rejected');
    await fill('selection', 'Synthetic home win');
    await fill('event', 'Synthetic game A');
    await fill('odds', '+99'); await click('review');
    assert.ok(byId('error'), 'invalid American odds rejected');
    await fill('odds', '+100'); await click('review');
    assert.equal(byId('pick-0'), null, 'review has not yet saved the selection');
    assert.match(document.body.textContent, /Manual entry \(unverified\)/);
    assert.match(document.body.textContent, /Unknown — payout math only/);
    await click('back-to-edit'); await fill('odds', '-110');
    await click('review'); await click('confirm');
    assert.match(byId('pick-0').textContent, /-110/);
    await click('calculate');
    assert.match(byId('results').textContent, /\$19\.09/);
    assert.match(byId('results').textContent, /52\.38%/);
    assert.match(byId('results').textContent, /Chance under your assumptionsUnknown/);

    await fill('stake', '20');
    assert.equal(byId('results'), null, 'stake change clears stale math');
    await click('calculate'); assert.match(byId('results').textContent, /\$38\.18/);
    await click('edit-0'); assert.equal(byId('results'), null, 'editing clears stale math');
    await fill('odds', '+150'); await click('review'); await click('cancel');
    assert.match(byId('pick-0').textContent, /-110/, 'cancel leaves confirmed odds intact');

    await click('edit-0'); await fill('odds', '+100'); await fill('chance', '60');
    await click('review'); await click('confirm');
    assert.equal(document.querySelectorAll('[data-testid^="pick-"]').length, 1);
    await click('add'); await fill('selection', 'Synthetic away win');
    await fill('event', 'Synthetic game B'); await fill('odds', '+100'); await fill('chance', '60');
    await click('review'); await click('confirm');
    await click('calculate');
    assert.doesNotMatch(byId('results').textContent, /ALL MUST WIN/);
    const switchElement = byId('independent');
    const checkbox = switchElement.matches('input') ? switchElement : switchElement.querySelector('input');
    assert.ok(checkbox, 'native switch exports an operable checkbox');
    checkbox.click(); await tick();
    assert.equal(byId('results'), null, 'independence change clears stale math');
    await click('calculate');
    assert.match(byId('results').textContent, /ALL MUST WIN/);
    assert.match(byId('results').textContent, /36\.00%/);
    assert.match(byId('results').textContent, /\$80\.00/);
    assert.match(byId('results').textContent, /Hypothetical combined price/);

    await click('edit-1'); await fill('event', ' synthetic GAME a ');
    await click('review'); await click('confirm'); await click('calculate');
    assert.doesNotMatch(byId('results').textContent, /ALL MUST WIN/, 'same-game combination is excluded');
    await fill('stake', '0'); await click('calculate');
    assert.ok(byId('error')); assert.equal(byId('results'), null);
    await click('remove-0'); assert.equal(byId('results'), null);
    assert.equal(document.querySelectorAll('[data-testid^="pick-"]').length, 1);
    assert.deepEqual(errors.map(e => e.message), []);
  } finally { window.close(); }
});
