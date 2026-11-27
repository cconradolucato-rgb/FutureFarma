import copy,io,json,tempfile,unittest,zipfile,os,base64,hashlib
from pathlib import Path
from unittest.mock import Mock,patch
from updater import *
class Tests(unittest.TestCase):
 def setUp(self):
  from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
  from cryptography.hazmat.primitives import serialization
  self.key=Ed25519PrivateKey.generate();self.config={'public_key':self.key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex(),'decrypt_key':os.urandom(32).hex()}
 def package(self,files=None):
  files=files or {'career_engine.py':b'x=42\n'};raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   for n,b in files.items():z.writestr(n,b)
  nonce=os.urandom(12);m={'schema':1,'product':'futurefarma-commercial','build':2,'version':'test','payload':'releases/2.bin','files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
  cipher=AESGCM(bytes.fromhex(self.config['decrypt_key'])).encrypt(nonce,raw.getvalue(),canonical({'build':2,'product':m['product']}));m.update(nonce=base64.b64encode(nonce).decode(),cipher_sha256=hashlib.sha256(cipher).hexdigest())
  return {'manifest':m,'signature':base64.b64encode(self.key.sign(canonical(m))).decode()},cipher
 def test_valid(self):
  e,c=self.package();m,f=decode_release(e,c,self.config);self.assertEqual(f['career_engine.py'],b'x=42\n')
 def test_tampering(self):
  e,c=self.package();e['manifest']['build']=3
  with self.assertRaises(Exception):decode_release(e,c,self.config)
 def test_corrupt_cipher(self):
  e,c=self.package()
  with self.assertRaises(Exception):decode_release(e,c[:-1]+bytes([c[-1]^1]),self.config)
 def test_wrong_key(self):
  e,c=self.package();cfg={**self.config,'decrypt_key':os.urandom(32).hex()}
  with self.assertRaises(Exception):decode_release(e,c,cfg)
 def test_downgrade(self):
  e,c=self.package()
  with self.assertRaises(ValueError):decode_release(e,c,self.config,2)
 def test_protected_files(self):
  for name in ['config.json','data/settings.json','data/auth.json','../server.py','static/../../x.py']:
   with self.subTest(name=name):
    e,c=self.package({name:b'x=1\n'})
    with self.assertRaises(ValueError):decode_release(e,c,self.config)
 def test_python_syntax(self):
  e,c=self.package({'career_engine.py':b'not valid python!'});
  with self.assertRaises(SyntaxError):decode_release(e,c,self.config)
 def fixture(self,root):
  root=Path(root);(root/'static').mkdir();(root/'static/index.html').write_text('<body>Future Farma</body>');(root/'career_engine.py').write_text('x=1\n');(root/'config.json').write_text('secret unchanged');(root/'data').mkdir();(root/'data/settings.json').write_text('settings unchanged')
  u=Updater.__new__(Updater);u.root=root;u.home=root/'automatic_updates';u.home.mkdir();u.state={};u.state_path=u.home/'state.json';u.import_check=Mock();u.restart=Mock();u.health=Mock(return_value=True);return u
 def test_apply_preserves_data(self):
  with tempfile.TemporaryDirectory() as d:
   u=self.fixture(d);u.apply({'build':2,'version':'test'},{'career_engine.py':b'x=42\n'});self.assertEqual((u.root/'config.json').read_text(),'secret unchanged');self.assertEqual((u.root/'data/settings.json').read_text(),'settings unchanged');self.assertEqual(u.state['build'],2);self.assertTrue(list((u.home/'backups').glob('*/career_engine.py')))
 def test_rollback_health_failure(self):
  with tempfile.TemporaryDirectory() as d:
   u=self.fixture(d);u.health.return_value=False
   with self.assertRaises(RuntimeError):u.apply({'build':2,'version':'test'},{'career_engine.py':b'x=42\n','static/new.js':b'console.log(1)'})
   self.assertEqual((u.root/'career_engine.py').read_text(),'x=1\n');self.assertEqual((u.root/'static/index.html').read_text(),'<body>Future Farma</body>');self.assertFalse((u.root/'static/new.js').exists());self.assertEqual(u.restart.call_count,2);self.assertFalse(u.state_path.exists())
 def test_rollback_import_failure(self):
  with tempfile.TemporaryDirectory() as d:
   u=self.fixture(d);u.import_check.side_effect=RuntimeError('import')
   with self.assertRaises(RuntimeError):u.apply({'build':2,'version':'test'},{'career_engine.py':b'x=42\n'})
   self.assertEqual((u.root/'career_engine.py').read_text(),'x=1\n')
 def test_cleanup_only_managed_old_files(self):
  with tempfile.TemporaryDirectory() as d:
   u=self.fixture(d);cache=u.root/'__pycache__';cache.mkdir();old=cache/'old.pyc';old.write_bytes(b'old');os.utime(old,(0,0))
   folders=u.home/'backups';folders.mkdir()
   for i in range(8):
    p=folders/str(i);p.mkdir();(p/'keep').touch();os.utime(p,(i,i))
   unknown=u.root/'backup_manual';unknown.mkdir();(unknown/'historic').touch()
   u.cleanup();self.assertFalse(old.exists());self.assertEqual(len(list(folders.iterdir())),5);self.assertTrue((unknown/'historic').exists());self.assertEqual((u.root/'data/settings.json').read_text(),'settings unchanged')
 def test_revision_reference_parsing(self):
  response=Mock();response.url='https://github.com/cconradolucato-rgb/FutureFarma.git/info/refs?service=git-upload-pack';response.read.return_value=b'0040'+b'a'*40+b' refs/heads/main\n';response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
  with patch('updater.urllib.request.urlopen',return_value=response):self.assertEqual(latest_revision(),'a'*40)
 def test_manifest_by_immutable_revision(self):
  with tempfile.TemporaryDirectory() as d:
   u=self.fixture(d);u.config=self.config;u.apply=Mock();e,c=self.package()
   with patch('updater.latest_revision',return_value='a'*40),patch('updater.download_revision',side_effect=[json.dumps(e).encode(),c]) as fetch,patch('updater.download') as old:
    u.run();self.assertEqual(fetch.call_count,2);self.assertEqual(fetch.call_args_list[0].args[0],'a'*40);self.assertFalse(old.called);self.assertTrue(u.apply.called)
 def test_signed_fallback_if_git_unavailable(self):
  with tempfile.TemporaryDirectory() as d:
   u=self.fixture(d);u.config=self.config;u.apply=Mock();e,c=self.package()
   with patch('updater.latest_revision',side_effect=OSError('blocked')),patch('updater.download',side_effect=[json.dumps(e).encode(),c]) as fetch:
    u.run();self.assertEqual(fetch.call_count,2);self.assertTrue(u.apply.called)
 def test_html_idempotent(self):
  b=integrate_html(b'<body></body>',2);c=integrate_html(b,3);self.assertEqual(c.count(b'career_losses.js'),1);self.assertEqual(c.count(b'commission_percent.js'),1)
if __name__=='__main__':unittest.main()
