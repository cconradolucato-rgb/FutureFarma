from pathlib import Path
import json,tempfile,unittest,zipfile
from recover_config import recover
class Recovery(unittest.TestCase):
 def fixture(self,folder,native=True):
  r=Path(folder);(r/'static').mkdir();(r/'data').mkdir();(r/'static/index.html').write_text('<body>Future Farma</body>');(r/'server.py').write_text('# server')
  (r/'config.json').write_text(json.dumps({'public_key':'a'*64,'decrypt_key':'b'*64}))
  (r/'reader.py').write_text("transport='powershell_local'" if native else '# no native')
  (r/'coletar_servidor.ps1').write_text("Integrated Security=True; [FutureFarma.NativeCollector]::Run($connection,$query)")
  (r/'coletor_json_nativo.ps1').write_text('class NativeCollector {}')
  (r/'data/settings.json').write_text('metas e taxas originais');(r/'data/auth.json').write_text('senha original');(r/'data/snapshot.json').write_text('historico original')
  return r
 def assert_data(self,r):
  self.assertEqual((r/'data/settings.json').read_text(),'metas e taxas originais');self.assertEqual((r/'data/auth.json').read_text(),'senha original');self.assertEqual((r/'data/snapshot.json').read_text(),'historico original')
 def test_native_reconstruction_when_backup_missing(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.fixture(d);old=(r/'config.json').read_bytes();result=recover(r);self.assertEqual(json.loads((r/'config.json').read_text()),{'sql_server':{'enabled':True,'transport':'powershell_local','poll_seconds':30}});self.assertEqual((Path(result['backup'])/'config_do_pacote_antigo.json').read_bytes(),old);self.assert_data(r)
 def test_backup_preserved_exactly(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.fixture(d);b=r/'backup_previous';b.mkdir();good={'sql_server':{'enabled':True,'transport':'powershell_local','poll_seconds':45},'custom':'preservar'};raw=json.dumps(good).encode();(b/'config.json').write_bytes(raw)
   recover(r);self.assertEqual((r/'config.json').read_bytes(),raw);self.assert_data(r)
 def test_zip_backup(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.fixture(d);good={'sql_server':{'enabled':True,'transport':'powershell_local','poll_seconds':60}}
   with zipfile.ZipFile(r/'backup.zip','w') as z:z.writestr('FutureFarma_Servidor/config.json',json.dumps(good))
   recover(r);self.assertEqual(json.loads((r/'config.json').read_text()),good)
 def test_unknown_config_not_changed(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.fixture(d);(r/'config.json').write_text('{"unknown":true}');before=(r/'config.json').read_bytes()
   with self.assertRaises(ValueError):recover(r)
   self.assertEqual((r/'config.json').read_bytes(),before);self.assertFalse((r/'automatic_recovery').exists())
 def test_no_native_and_no_backup_fails_without_changes(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.fixture(d,False);before=(r/'config.json').read_bytes()
   with self.assertRaises(ValueError):recover(r)
   self.assertEqual((r/'config.json').read_bytes(),before);self.assert_data(r)
 def test_second_run_no_change(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.fixture(d);recover(r);self.assertEqual(recover(r)['result'],'unchanged');self.assertEqual(len(list((r/'automatic_recovery').iterdir())),1)
if __name__=='__main__':unittest.main()
