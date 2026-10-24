"""Fixed read-only Docker query. Installed root-owned; accepts no arguments."""
import json
from pathlib import Path
import os
import subprocess
from datetime import datetime, timezone

result = {'connected': False, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'containers': []}
try:
    command = subprocess.run(['/usr/bin/docker', 'inspect', '--type', 'container', 'pardo-web'],
                             capture_output=True, text=True, check=True, timeout=6)
    for container in json.loads(command.stdout):
        state = container['State']
        result['containers'].append({'name': 'pardo-web', 'state': state['Status'],
            'running': state['Running'], 'health': state.get('Health', {}).get('Status', 'not_configured'),
            'restartCount': int(container['RestartCount']), 'startedAt': state['StartedAt']})
    result['connected'] = True
except (OSError, ValueError, KeyError, subprocess.SubprocessError):
    result['error'] = 'Container state unavailable'
path = Path('/var/lib/pardo-container-monitor/status.json')
temporary = path.with_suffix('.tmp')
temporary.write_text(json.dumps(result) + '\n')
temporary.chmod(0o644)
os.replace(temporary, path)
