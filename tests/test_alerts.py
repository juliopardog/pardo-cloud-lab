import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timezone
spec=importlib.util.spec_from_file_location('alerts',Path(__file__).resolve().parents[1]/'monitoring/alerts.py')
alerts=importlib.util.module_from_spec(spec);spec.loader.exec_module(alerts)
class AlertTests(unittest.TestCase):
    def snapshot(self):
        return {'updatedAt':datetime.now(timezone.utc).isoformat(),'website':{'healthy':True},'containerMonitor':{'connected':True,'containers':[{'running':True,'health':'healthy'}]},'host':{'cpuPercent':1,'memoryPercent':30,'diskPercent':5},'github':{'connected':True,'runs':[{'conclusion':'success'}]}}
    def test_healthy_does_not_alert(self):
        self.assertEqual(alerts.evaluate(self.snapshot(),datetime.now(timezone.utc).timestamp()),[])
    def test_failures_are_detected(self):
        data=self.snapshot();data['host']['diskPercent']=90;data['github']['runs'][0]['conclusion']='failure';data['containerMonitor']['containers'][0]['health']='unhealthy'
        result=alerts.evaluate(data,datetime.now(timezone.utc).timestamp())
        self.assertEqual(len(result),3)
