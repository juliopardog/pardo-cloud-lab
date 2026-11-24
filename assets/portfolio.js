// Public portfolio: no private telemetry requests, credentials, or host controls.
(() => {
  const all = selector => [...document.querySelectorAll(selector)];
  const message = 'Live measurements are available on the private lab dashboard.';
  const values = ['Linux host', 'Docker / Nginx', 'GitHub Actions', 'Private monitoring'];
  all('.metrics .metric').forEach((card, i) => {
    card.querySelector('.metric-value').textContent = values[i];
    card.querySelectorAll('.metric-row').forEach(row => row.lastElementChild.textContent = 'Documented');
    card.lastElementChild.textContent = message;
  });
  const status = document.querySelector('.statusbar > span:last-child');
  if (status) status.textContent = 'Public portfolio · live monitoring stays private';
  const footnote = document.querySelector('.metrics + p');
  if (footnote) footnote.textContent = message;
  all('.dashboard .empty').forEach(card => {
    card.querySelector('h3').textContent = 'Private';
    card.querySelector('small').textContent = message;
  });
  all('#ranges button, #deployment-filters button').forEach(button => {
    button.disabled = true;
    button.title = 'Use the private dashboard or the linked GitHub Actions history.';
  });
  const range = document.querySelector('#range-label');
  if (range) range.textContent = 'HOST HISTORY REMAINS PRIVATE';
  const deployments = document.querySelector('#deployment-empty');
  if (deployments) {
    deployments.textContent = 'Deployment history on GitHub Actions';
    deployments.nextElementSibling.textContent = 'View workflow runs using the link below. Private server snapshots are not published here.';
  }
})();
