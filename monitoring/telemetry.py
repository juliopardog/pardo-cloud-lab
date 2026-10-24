"""Publish aggregate, read-only host measurements for the local website."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime, timezone
import urllib.request

OUTPUT = Path('/srv/pardo-cloud-lab/website/telemetry/status.json')
STATE = Path('/var/lib/pardo-telemetry')
CONTAINERS = Path('/var/lib/pardo-container-monitor/status.json')

def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default

def save_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, allow_nan=False) + '\n', encoding='utf-8')
    temporary.chmod(0o644)
    os.replace(temporary, path)

def github_runs():
    cache_path = STATE / 'github.json'
    cached = read_json(cache_path, {})
    if time.time() - cached.get('checkedEpoch', 0) < 300:
        return cached
    checked = datetime.now(timezone.utc).isoformat()
    try:
        request = urllib.request.Request(
            'https://api.github.com/repos/juliopardog/pardo-cloud-lab/actions/workflows/deploy.yml/runs?per_page=30',
            headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Pardo-Cloud-Lab-Monitor'})
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.load(response)
        runs = []
        for run in payload['workflow_runs']:
            run_id = int(run['id'])
            runs.append({'id': run_id, 'number': int(run['run_number']),
                         'status': str(run['status'])[:40], 'conclusion': run.get('conclusion'),
                         'createdAt': run['created_at'], 'updatedAt': run['updated_at'],
                         'branch': str(run['head_branch'])[:100], 'commit': str(run['head_sha'])[:40],
                         'url': f'https://github.com/juliopardog/pardo-cloud-lab/actions/runs/{run_id}'})
        cached = {'connected': True, 'checkedEpoch': time.time(), 'updatedAt': checked,
                  'source': 'GitHub deploy.yml workflow runs', 'runs': runs}
    except (OSError, ValueError, KeyError, TypeError):
        cached = {**cached, 'connected': False, 'checkedEpoch': time.time(), 'error': 'GitHub unavailable; cached results may be outdated'}
    save_json(cache_path, cached)
    return cached

def update_history(data):
    path = STATE / 'history.json'
    now = int(time.time())
    bucket = now // 60 * 60
    history = [s for s in read_json(path, []) if s['timestamp'] >= now - 7 * 86400]
    sample = {'timestamp': bucket, **data['host'], 'websiteHealthy': data['website']['healthy'],
              'responseMs': data['website']['responseMs']}
    if history and history[-1]['timestamp'] == bucket:
        history[-1] = sample
    else:
        history.append(sample)
    save_json(path, history)
    save_json(OUTPUT.parent / 'history.json', {'updatedAt': data['updatedAt'], 'sampleIntervalSeconds': 60, 'retentionDays': 7, 'samples': history})
    return {'sampleCount': len(history), 'startedAt': history[0]['timestamp'] if history else None, 'retentionDays': 7}

def counters():
    values = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    traffic = [line.split(':', 1) for line in Path('/proc/net/dev').read_text().splitlines()[2:]]
    defaults = {parts[0] for line in Path('/proc/net/route').read_text().splitlines()[1:] for parts in [line.split()] if len(parts)>3 and parts[1]=='00000000' and int(parts[3],16)&2}
    network = sum(int(v[0]) + int(v[8]) for name, raw in traffic if name.strip() in defaults for v in [raw.split()])
    return sum(values), values[3] + values[4], network

def active(unit):
    return subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet', unit], check=False).returncode == 0

def collect():
    before = counters()
    started = time.monotonic()
    time.sleep(1)
    after = counters()
    elapsed = time.monotonic() - started
    total = after[0] - before[0]
    cpu = 100 * (1 - (after[1] - before[1]) / total) if total > 0 else 0
    mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:', 'MemAvailable:'))}
    disk = shutil.disk_usage('/')
    check_start = time.monotonic()
    try:
        with urllib.request.urlopen('http://127.0.0.1:8080/', timeout=3) as response:
            healthy = response.status == 200
        latency = round((time.monotonic() - check_start) * 1000, 1)
    except (OSError, ValueError):
        healthy, latency = False, None
    result = {
        'connected': True, 'updatedAt': datetime.now(timezone.utc).isoformat(),
        'source': 'Linux host counters and local HTTP check',
        'host': {'cpuPercent': round(max(0, min(100, cpu)), 1),
                 'memoryPercent': round(100 * (1 - mem['MemAvailable'] / mem['MemTotal']), 1),
                 'diskPercent': round(100 * disk.used / disk.total, 1),
                 'uptimeSeconds': int(float(Path('/proc/uptime').read_text().split()[0])),
                 'networkBytesPerSecond': round(max(0, after[2] - before[2]) / elapsed)},
        'website': {'healthy': healthy, 'responseMs': latency, 'scope': 'local HTTP check'},
        'dockerServiceActive': active('docker.service'),
        'history': [], 'deployments': [],
    }
    containers = read_json(CONTAINERS, {})
    try:
        age = time.time() - datetime.fromisoformat(containers['updatedAt']).timestamp()
        containers['connected'] = containers.get('connected') is True and 0 <= age < 45
    except (KeyError, ValueError, TypeError):
        containers = {'connected': False, 'containers': []}
    result['containerMonitor'] = containers
    github = github_runs()
    result['github'] = {key: value for key, value in github.items() if key != 'checkedEpoch'}
    result['deployments'] = github.get('runs', [])
    result['historySummary'] = update_history(result)
    return result

def publish(data):
    save_json(OUTPUT, data)

if __name__ == '__main__':
    publish(collect())
