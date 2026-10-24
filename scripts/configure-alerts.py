"""Run with sudo in an interactive terminal; secrets are never printed."""
import getpass
import json
import os
from pathlib import Path
import subprocess
if os.geteuid()!=0: raise SystemExit('Run this configuration command with sudo.')
values={}
values['ALERT_TO']=input('Destination email: ').strip()
values['SMTP_HOST']=input('SMTP hostname [smtp.gmail.com]: ').strip() or 'smtp.gmail.com'
values['SMTP_PORT']=input('SMTP port [465]: ').strip() or '465'
values['SMTP_USER']=input('SMTP username: ').strip()
values['SMTP_FROM']=input('From email [SMTP username]: ').strip() or values['SMTP_USER']
values['SMTP_PASSWORD']=getpass.getpass('SMTP app password (hidden): ')
if any(not v or '\n' in v or '\r' in v for v in values.values()): raise SystemExit('All values are required and must be single lines.')
path=Path('/etc/pardo-cloud-lab/alerts.env')
with path.open('w',opener=lambda p,f:os.open(p,f,0o600)) as stream:
    for key,value in values.items(): stream.write(key+'='+json.dumps(value)+'\n')
path.chmod(0o600)
subprocess.run(['systemctl','enable','--now','pardo-alerts.timer'],check=True)
print('Configured. Alerts send on sustained problems or recovery after three checks; no test email sent.')
