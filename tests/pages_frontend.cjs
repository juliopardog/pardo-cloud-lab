const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {parseHTML} = require('linkedom');
for (const route of ['index.html', 'infrastructure/index.html', 'journal/index.html']) {
  const {document} = parseHTML(fs.readFileSync('pages-site/' + route, 'utf8'));
  const context = {document, console, localStorage: {getItem: () => null},
    fetch: () => {throw new Error('Public portfolio must not call private APIs');}};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('pages-site/app.js', 'utf8'), context);
  vm.runInContext(fs.readFileSync('pages-site/portfolio.js', 'utf8'), context);
  if (route === 'index.html') {
    assert.match(document.querySelector('.statusbar').textContent, /Public portfolio/);
  } else if (route.startsWith('infrastructure')) {
    assert.ok([...document.querySelectorAll('#ranges button')].every(b => b.disabled));
    assert.match(document.querySelector('#range-label').textContent, /PRIVATE/);
    assert.ok([...document.querySelectorAll('.dashboard .empty h3')].every(e => e.textContent === 'Private'));
  } else {
    assert.match(document.querySelector('#deployment-empty').textContent, /GitHub Actions/);
    assert.ok([...document.querySelectorAll('#deployment-filters button')].every(b => b.disabled));
  }
  console.log('PASS public', route);
}
