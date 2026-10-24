(() => {
  const one = s => document.querySelector(s);
  const all = s => [...document.querySelectorAll(s)];
  const duration = seconds => `${Math.floor(seconds / 86400)}d ${Math.floor(seconds % 86400 / 3600)}h ${Math.floor(seconds % 3600 / 60)}m`;
  const percent = value => `${value.toFixed(1)}%`;
  let latest = null;
  let history = [], selectedHours = 1, deploymentFilter = 'All deployments';
  function set(selector, text) { const e = one(selector); if (e) e.textContent = text; }
  function metric(index, value, rows, note) {
    const card = all('.metrics .metric')[index];
    if (!card) return;
    card.querySelector('.metric-value').textContent = value;
    [...card.querySelectorAll('.metric-row')].forEach((row, i) => {
      if (rows[i]) row.lastElementChild.textContent = rows[i];
    });
    card.lastElementChild.textContent = note;
  }
  function unavailable(message) {
    latest = null;
    set('.statusbar > span:last-child', message);
    all('.metrics .metric').forEach(card => {
      card.querySelector('.metric-value').textContent = '—';
      card.querySelectorAll('.metric-row').forEach(row => row.lastElementChild.textContent = 'Unavailable');
      card.lastElementChild.textContent = message;
    });
    all('.dashboard .empty').forEach(card => {
      card.querySelector('h3').textContent = '—';
      card.querySelector('small').textContent = message;
    });
    set('#telemetry-description', message);
    set('#range-label', 'LIVE SNAPSHOT · DATA UNAVAILABLE');
    set('.metrics + p', message);
    set('#container-live', message);
  }
  function render(data) {
    const h = data.host;
    const time = new Date(data.updatedAt).toLocaleTimeString();
    const note = `Measured ${time} · refreshes every 15 seconds`;
    set('.statusbar > span:last-child', `● Telemetry connected · ${time}`);
    metric(0, percent(h.cpuPercent), [`${percent(h.cpuPercent)} / ${percent(h.memoryPercent)}`, `${percent(h.diskPercent)} / ${duration(h.uptimeSeconds)}`], note);
    metric(1, data.dockerServiceActive ? 'Running' : 'Stopped', [data.website.healthy ? 'HTTP 200' : 'Check failed', 'Not collected'], 'Docker daemon status; individual container health is not collected.');
    metric(2, 'Not connected', ['main', 'Not connected'], 'GitHub deployment history is not connected.');
    metric(3, data.website.healthy ? 'Responding' : 'Unavailable', [data.website.healthy ? 'Local HTTP check passed' : 'Local HTTP check failed', time], 'Local check only; external reachability is not measured.');
    set('.metrics + p', `Source: ${data.source}. ${note}. No historical availability percentage is calculated.`);
    const values = [percent(h.cpuPercent), percent(h.memoryPercent), percent(h.diskPercent), duration(h.uptimeSeconds), `${(h.networkBytesPerSecond / 1024).toFixed(1)} KiB/s`, 'Not collected', data.website.responseMs === null ? 'Unavailable' : `${data.website.responseMs.toFixed(1)} ms`, 'Not connected', data.website.healthy ? 'Responding' : 'Unavailable'];
    all('.dashboard .empty').forEach((card, i) => {
      card.querySelector('h3').textContent = values[i];
      card.querySelector('small').textContent = i === 5 ? 'Per-container health not collected' : i === 7 ? 'GitHub history not connected' : i === 8 ? 'Local HTTP check only' : note;
    });
    set('#telemetry-description', 'Live host measurements refresh every 15 seconds. Historical charts, individual container health, and GitHub deployment history are not connected.');
    set('#range-label', `LIVE SNAPSHOT · UPDATED ${time} · HISTORY NOT COLLECTED`);
    renderConnections(data);
  }
  function validate(data) {
    const age = Date.now() - Date.parse(data.updatedAt);
    if (data.connected !== true || !Number.isFinite(age) || age > 45000 || age < -60000) throw new Error('Stale telemetry');
    for (const key of ['cpuPercent', 'memoryPercent', 'diskPercent']) {
      if (!Number.isFinite(data.host?.[key]) || data.host[key] < 0 || data.host[key] > 100) throw new Error('Invalid measurement');
    }
    for (const key of ['uptimeSeconds', 'networkBytesPerSecond']) {
      if (!Number.isFinite(data.host?.[key]) || data.host[key] < 0) throw new Error('Invalid measurement');
    }
    if (typeof data.dockerServiceActive !== 'boolean' || typeof data.website?.healthy !== 'boolean' || !(data.website.responseMs === null || Number.isFinite(data.website.responseMs) && data.website.responseMs >= 0)) throw new Error('Invalid health check');
    return data;
  }
  async function refresh() {
    try {
      const response = await fetch(`/telemetry/status.json?t=${Date.now()}`, {cache: 'no-store', signal: AbortSignal.timeout(5000)});
      if (!response.ok) throw new Error('Telemetry request failed');
      latest = validate(await response.json());
      render(latest);
    } catch { unavailable('Telemetry unavailable or stale · retrying automatically'); }
  }
  function text(tag, value, className) {
    const e = document.createElement(tag);
    if (value !== undefined) e.textContent = value;
    if (className) e.className = className;
    return e;
  }
  function connectionRegion() {
    if (one('#container-live')) return one('#container-live');
    const dashboard = one('.dashboard');
    if (!dashboard) return null;
    const region = text('div', '', 'notice spacer'); region.id = 'container-live';
    dashboard.after(region); return region;
  }
  function renderConnections(data) {
    const monitor = data.containerMonitor;
    const monitorAge = Date.now() - Date.parse(monitor?.updatedAt);
    const connected = monitor?.connected === true && Number.isFinite(monitorAge) && monitorAge < 45000 && monitorAge > -60000;
    const containers = connected && Array.isArray(monitor.containers) ? monitor.containers.filter(c => c.name === 'pardo-web') : [];
    const container = containers[0];
    const health = container ? (container.health === 'not_configured' ? 'No Docker healthcheck configured' : `${container.health} · ${container.state}`) : 'Container telemetry unavailable';
    const github = data.github;
    const githubAge = Date.now() - Date.parse(github?.updatedAt);
    const githubFresh = github?.connected === true && Number.isFinite(githubAge) && githubAge < 600000 && githubAge > -60000;
    const runs = Array.isArray(github?.runs) ? github.runs : [];
    const run = runs[0];
    const result = githubFresh ? run ? run.conclusion || run.status : 'No runs yet' : 'GitHub unavailable';
    metric(1, container?.running ? 'Running' : container ? container.state : 'Unavailable', [data.website.healthy ? 'HTTP 200' : 'Check failed', health], `Container observation: ${connected ? new Date(monitor.updatedAt).toLocaleTimeString() : 'unavailable'}`);
    metric(2, result, [run?.branch || 'main', run ? `Run #${run.number} · ${result}` : result], `GitHub workflow history; refreshes every 5 minutes. ${github?.updatedAt ? 'Checked ' + new Date(github.updatedAt).toLocaleTimeString() : ''}`);
    const widgets = all('.dashboard .empty');
    if (widgets[5]) { widgets[5].querySelector('h3').textContent = container?.health || 'Unavailable'; widgets[5].querySelector('small').textContent = health; }
    if (widgets[7]) { widgets[7].querySelector('h3').textContent = result; widgets[7].querySelector('small').textContent = run ? `Workflow run #${run.number} · ${new Date(run.createdAt).toLocaleString()}` : result; }
    set('#telemetry-description', 'Live host and container measurements refresh every 15 seconds. GitHub workflow history refreshes every 5 minutes. Recorded history begins when monitoring was installed.');
    const region = connectionRegion();
    if (region) {
      region.replaceChildren(text('strong', 'Website container'));
      region.append(text('p', container ? `${container.name}: ${health}. Restarts: ${Number.isSafeInteger(container.restartCount) ? container.restartCount : 'unknown'}. Started: ${new Date(container.startedAt).toLocaleString()}.` : health));
    }
    renderDeployments(runs, githubFresh, github?.updatedAt);
    renderHistory();
  }
  function renderDeployments(runs, fresh, updatedAt) {
    const empty = one('#deployment-empty');
    if (!empty) return;
    const region = empty.parentElement;
    while (empty.nextSibling) empty.nextSibling.remove();
    empty.textContent = fresh ? 'GitHub deployment workflow history' : 'GitHub unavailable · showing cached workflow history';
    const filtered = runs.filter(run => deploymentFilter === 'All deployments' ||
      deploymentFilter === 'Successful' && run.conclusion === 'success' ||
      deploymentFilter === 'Failed' && ['failure', 'timed_out', 'action_required', 'startup_failure'].includes(run.conclusion) ||
      deploymentFilter === 'In progress' && run.status !== 'completed');
    if (!filtered.length) region.append(text('p', fresh ? 'No matching workflow runs.' : 'No cached workflow runs available.'));
    for (const run of filtered) {
      const row = text('p');
      if (Number.isSafeInteger(run.id) && run.id > 0) {
        const link = text('a', `Run #${run.number} · ${run.conclusion || run.status}`, 'textlink');
        link.href = `https://github.com/juliopardog/pardo-cloud-lab/actions/runs/${run.id}`;
        link.target = '_blank'; link.rel = 'noopener'; row.append(link);
      }
      row.append(text('span', ` · ${new Date(run.createdAt).toLocaleString()} · ${run.branch} · ${String(run.commit).slice(0,7)}`));
      region.append(row);
    }
    region.append(text('p', `Source: GitHub deploy.yml${updatedAt ? ' · checked ' + new Date(updatedAt).toLocaleString() : ''}. Workflow results describe GitHub runs; the served release revision is recorded separately in /release.json.`));
  }
  function renderHistory() {
    const dashboard = one('.dashboard'); if (!dashboard) return;
    let region = one('#telemetry-history');
    if (!region) { region = text('section', '', 'notice spacer'); region.id = 'telemetry-history'; dashboard.after(region); }
    const now = Date.now() / 1000;
    const samples = history.filter(s => Number.isFinite(s.timestamp) && s.timestamp >= now - selectedHours * 3600 && s.timestamp <= now + 60 && ['cpuPercent','memoryPercent','diskPercent'].every(k => Number.isFinite(s[k]) && s[k] >= 0 && s[k] <= 100));
    region.replaceChildren(text('h3', 'Recorded host history'));
    const start = samples.length ? new Date(samples[0].timestamp * 1000).toLocaleString() : 'waiting for first sample';
    set('#range-label', `LAST ${selectedHours === 168 ? '7 DAYS' : selectedHours + ' HOURS'} · ${samples.length} RECORDED MINUTE SAMPLES · SINCE ${start}`);
    region.append(text('p', `One sample per minute, retained for seven days. Available in this range: ${samples.length} samples, starting ${start}. Gaps represent missing measurements.`));
    if (!samples.length) return;
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', '0 0 700 210'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'Recorded CPU, memory and disk utilization percentages, zero to one hundred percent'); svg.style.width = '100%'; svg.style.maxHeight = '260px';
    const span = Math.max(60, samples[samples.length-1].timestamp - samples[0].timestamp);
    const legends = [['cpuPercent','#0757f9','CPU'],['memoryPercent','#087861','RAM'],['diskPercent','#b06400','Disk']];
    for (const [key, color] of legends) {
      let d = '', last = null;
      for (const sample of samples) {
        const x = 15 + (sample.timestamp - samples[0].timestamp) / span * 670;
        const y = 190 - sample[key] * 1.7;
        d += `${last === null || sample.timestamp - last > 120 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)} `; last = sample.timestamp;
        if (samples.length === 1) { const dot = document.createElementNS(ns, 'circle'); dot.setAttribute('cx', x); dot.setAttribute('cy', y); dot.setAttribute('r', '4'); dot.setAttribute('fill', color); svg.append(dot); }
      }
      const path = document.createElementNS(ns, 'path'); path.setAttribute('d', d); path.setAttribute('stroke', color); path.setAttribute('stroke-width','2'); path.setAttribute('fill','none'); svg.append(path);
    }
    region.append(svg);
    const legend = text('p'); for (const [, color, label] of legends) { const e = text('span', `${label} (%)   `); e.style.color = color; legend.append(e); } region.append(legend);
    const checks = samples.filter(s => typeof s.websiteHealthy === 'boolean');
    if (checks.length) region.append(text('p', `Local HTTP checks passed in ${checks.filter(s => s.websiteHealthy).length} of ${checks.length} recorded minute samples. This is sampled local health, not internet availability.`));
  }
  async function refreshHistory() {
    if (!one('.dashboard')) return;
    try {
      const r = await fetch(`/telemetry/history.json?t=${Date.now()}`, {cache:'no-store', signal:AbortSignal.timeout(5000)});
      if (!r.ok) throw new Error('History unavailable');
      const data = await r.json(); if (!Array.isArray(data.samples)) throw new Error('Invalid history');
      history = data.samples; renderHistory();
    } catch { set('#range-label', 'RECORDED HISTORY UNAVAILABLE · RETRYING'); }
  }
  all('#ranges button').forEach((button, i) => { button.disabled = false; button.title = 'Show recorded samples in this range'; button.onclick = () => { selectedHours = [1,24,168][i]; all('#ranges button').forEach(b => b.classList.toggle('selected', b === button)); renderHistory(); }; });
  all('#deployment-filters button').forEach(button => { button.onclick = () => { deploymentFilter = button.textContent; all('#deployment-filters button').forEach(b => b.classList.toggle('selected', b === button)); if (latest) renderConnections(latest); }; });
  refreshHistory(); setInterval(refreshHistory, 60000);
  refresh();
  setInterval(refresh, 15000);
  setInterval(() => { if (latest && Date.now() - Date.parse(latest.updatedAt) > 45000) unavailable('Telemetry stale · waiting for fresh measurements'); }, 5000);
})();
