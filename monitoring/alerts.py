"""Send state-change email alerts through explicitly configured SMTP."""
import json
import os
from pathlib import Path
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timezone
STATE=Path('/var/lib/pardo-alerts/state.json')

def evaluate(snapshot,now):
    problems=[]
    if now-datetime.fromisoformat(snapshot['updatedAt']).timestamp()>60: problems.append('Telemetry collector is stale')
    if not snapshot['website']['healthy']: problems.append('Local website health check failed')
    if not snapshot['containerMonitor'].get('connected'): problems.append('Container collector is unavailable')
    elif any(c.get('health')!='healthy' or not c.get('running') for c in snapshot['containerMonitor'].get('containers',[])): problems.append('Website container is unhealthy')
    for key,limit,label in [('cpuPercent',95,'CPU'),('memoryPercent',90,'RAM'),('diskPercent',85,'Disk')]:
        if snapshot['host'][key]>=limit: problems.append(label+' usage is high')
    if not snapshot['github'].get('connected'): problems.append('GitHub workflow data is unavailable')
    runs=snapshot['github'].get('runs',[])
    if runs and runs[0].get('conclusion') in ('failure','timed_out','action_required'): problems.append('Latest deployment workflow failed')
    return sorted(problems)

def send(problems,recovery=False):
    message=EmailMessage();message['From']=os.environ['SMTP_FROM'];message['To']=os.environ['ALERT_TO']
    message['Subject']='Pardo Cloud Lab: recovered' if recovery else 'Pardo Cloud Lab: attention needed'
    message.set_content(('Monitoring checks recovered.' if recovery else '\n'.join(problems))+'\n\nMeasured by the server. A complete server outage needs an independent monitor.\n')
    host=os.environ['SMTP_HOST'];port=int(os.environ.get('SMTP_PORT','465'))
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=15,context=ssl.create_default_context()) as client:
            client.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);client.send_message(message)
    else:
        with smtplib.SMTP(host,port,timeout=15) as client:
            client.starttls(context=ssl.create_default_context());client.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);client.send_message(message)

def main():
    try: state=json.loads(STATE.read_text())
    except (OSError,ValueError): state={'candidate':[],'count':0,'notified':[]}
    try:
        snapshot=json.loads(Path('/srv/pardo-cloud-lab/website/telemetry/status.json').read_text())
        problems=evaluate(snapshot,datetime.now(timezone.utc).timestamp())
    except (OSError,ValueError,KeyError,TypeError): problems=['Monitoring snapshot unavailable']
    state['count']=state.get('count',0)+1 if state.get('candidate')==problems else 1
    state['candidate']=problems
    if state['count']>=3 and problems!=state.get('notified',[]):
        try:
            send(problems,recovery=not problems);state['notified']=problems
            print('Email notification delivered')
        except (OSError,KeyError,ValueError,smtplib.SMTPException) as error:
            print('Email delivery failed: '+type(error).__name__)
    temp=STATE.with_suffix('.tmp');temp.write_text(json.dumps(state));temp.chmod(0o600);temp.replace(STATE)
if __name__=='__main__': main()
