"""Cliente de atualizacao: somente releases cifrados e assinados da origem fixada."""
from pathlib import Path,PurePosixPath
import base64,hashlib,io,json,os,subprocess,sys,time,urllib.request,zipfile,shutil,contextlib,logging
from datetime import datetime,timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
BASE='https://raw.githubusercontent.com/cconradolucato-rgb/FutureFarma/main/'
ALLOWED={'career_engine.py','career_qualification.py','encapsulation.py','google_production_sync.py','reader.py','history_reference.py','goal_engine.py','purchase_planning.py','inventory_connection.py','inventory_projection.py','recovery_engine.py','forecast_engine.py','performance_flags.py','order_details.py','business_insights.py','google_reviews.py','server.py','core.py','settings_encoding.py','purchase_store.py','operations_store.py','google_reviews_config.py'}
REQUIRED_VERSION='2026-11-27-dashboard-bonus'
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def valid_path(name):
 p=PurePosixPath(name)
 if '\\' in name or p.is_absolute() or '..' in p.parts or str(p)!=name:raise ValueError('Caminho de pacote invalido')
 if name not in ALLOWED and not (name.startswith('static/') and len(p.parts)==2 and p.suffix in ('.js','.css','.html','.svg','.png','.jpg','.woff2')):raise ValueError('Arquivo fora da lista permitida: '+name)
 return name

def decode_release(envelope,ciphertext,config,current=0):
 m=envelope['manifest'];Ed25519PublicKey.from_public_bytes(bytes.fromhex(config['public_key'])).verify(base64.b64decode(envelope['signature'],validate=True),canonical(m))
 if m.get('schema')!=1 or m.get('product')!='futurefarma-commercial':raise ValueError('Release de outro produto')
 if type(m.get('build')) is not int or m['build']<=current:raise ValueError('Release antigo ou repetido')
 if hashlib.sha256(ciphertext).hexdigest()!=m['cipher_sha256']:raise ValueError('Pacote corrompido')
 raw=AESGCM(bytes.fromhex(config['decrypt_key'])).decrypt(base64.b64decode(m['nonce'],validate=True),ciphertext,canonical({'build':m['build'],'product':m['product']}))
 files={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if len(z.infolist())>80 or sum(i.file_size for i in z.infolist())>12000000:raise ValueError('Pacote excede o tamanho permitido')
  for info in z.infolist():
   name=valid_path(info.filename)
   if name in files:raise ValueError('Arquivo duplicado')
   content=z.read(info)
   if name not in m['files'] or hashlib.sha256(content).hexdigest()!=m['files'][name]:raise ValueError('Hash do arquivo invalido')
   if name.endswith('.py'):compile(content.decode('utf-8'),name,'exec')
   files[name]=content
 if set(files)!=set(m['files']):raise ValueError('Lista de arquivos diverge do manifesto')
 return m,files

def download(relative,limit):
 if relative.startswith('/') or '..' in relative.split('/') or ':' in relative or '\\' in relative:raise ValueError('Origem do pacote invalida')
 req=urllib.request.Request(BASE+relative,headers={'User-Agent':'FutureFarma-Updater/1'})
 with urllib.request.urlopen(req,timeout=30) as r:
  if not r.url.startswith(BASE):raise ValueError('Redirecionamento fora da origem autorizada')
  data=r.read(limit+1)
  if len(data)>limit:raise ValueError('Resposta grande demais')
  return data

def write_atomic(path,content):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.update-tmp');tmp.write_bytes(content);tmp.replace(path)

def integrate_html(original,build):
 import re
 text=original.decode('utf-8-sig')
 if '</body>' not in text:raise ValueError('HTML do painel invalido')
 for name in ('career_losses.js','commission_percent.js'):
  text=re.sub(r'<script\b[^>]*src=["\'][^"\']*'+re.escape(name)+r'[^"\']*["\'][^>]*>\s*</script>','',text,flags=re.I)
 tags=''.join('<script src="/'+name+'?v='+str(build)+'"></script>' for name in ('career_losses.js','commission_percent.js'))
 return text.replace('</body>',tags+'\n</body>').encode('utf-8')

class Updater:
 def __init__(self,root):
  self.root=Path(root).resolve();self.home=self.root/'automatic_updates';self.config=json.loads((self.home/'config.json').read_text(encoding='utf-8-sig'));self.state_path=self.home/'state.json'
  self.state=json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
  for required in ('server.py','config.json','static/index.html'):
   if not (self.root/required).is_file():raise ValueError('A pasta nao e a instalacao do painel')
 def status(self,**values):
  values={'checked_at':datetime.now(timezone.utc).isoformat(),**self.state,**values};write_atomic(self.home/'status.json',json.dumps(values,ensure_ascii=False,indent=2).encode())
 def restart(self):
  script=self.home/'restart_panel.ps1'
  subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),'-Root',str(self.root)],check=True,timeout=45,capture_output=True)
 def health(self,version=None):
  # Login HTML e scripts precisam responder; prova de importacao e separada.
  deadline=time.monotonic()+40
  while time.monotonic()<deadline:
   try:
    with urllib.request.urlopen('http://127.0.0.1:8765/',timeout=3) as r:html=r.read(200000).decode('utf-8',errors='replace')
    if 'FUTURE' in html.upper() and 'FARMA' in html.upper():return True
   except Exception:pass
   time.sleep(2)
  return False
 def import_check(self):
  code="import career_engine,career_qualification,encapsulation,google_production_sync; print('IMPORT_OK')"
  r=subprocess.run([sys.executable,'-c',code],cwd=str(self.root),capture_output=True,text=True,timeout=30)
  if r.returncode or 'IMPORT_OK' not in r.stdout:raise RuntimeError('Modulos nao carregaram; verificacao local falhou')
 def apply(self,m,files):
  # Preparar todos os arquivos antes de parar o processo.
  files={**files,'static/index.html':integrate_html(files.get('static/index.html',(self.root/'static/index.html').read_bytes()),m['build'])}
  backup=self.home/'backups'/(str(m['build'])+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(parents=True)
  previous={}
  for name in files:
   dest=(self.root/name).resolve()
   if self.root not in dest.parents:raise ValueError('Arquivo fora da instalacao')
   previous[name]=dest.read_bytes() if dest.exists() else None
   if previous[name] is not None:write_atomic(backup/name,previous[name])
  write_atomic(backup/'files.json',json.dumps({n:v is not None for n,v in previous.items()}).encode())
  try:
   for name,content in files.items():write_atomic(self.root/name,content)
   for folder in (self.root/'__pycache__',):
    for name in files:
     if name.endswith('.py'):
      for p in folder.glob(Path(name).stem+'.*.pyc'):p.unlink()
   self.import_check();self.restart()
   if not self.health(m.get('rule_version')):raise RuntimeError('Painel nao respondeu apos atualizar')
  except Exception:
   for name,content in previous.items():
    if content is None:(self.root/name).unlink(missing_ok=True)
    else:write_atomic(self.root/name,content)
   for name in files:
    if name.endswith('.py'):
     for cache in (self.root/'__pycache__').glob(Path(name).stem+'.*.pyc'):cache.unlink()
   try:self.restart()
   except Exception:logging.exception('Falha ao reiniciar apos restaurar')
   self.status(result='restored',failed_build=m['build'],backup=str(backup));raise
  self.state={'build':m['build'],'version':m['version'],'updated_at':datetime.now(timezone.utc).isoformat(),'backup':str(backup)}
  write_atomic(self.state_path,json.dumps(self.state,indent=2).encode());self.status(result='updated');self.cleanup()
 def run(self):
  # O manifesto e validado antes de confiar na versao ou origem do payload.
  e=json.loads(download('releases/stable.json',150000));m=e['manifest']
  Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.config['public_key'])).verify(base64.b64decode(e['signature'],validate=True),canonical(m))
  if m['build']<=self.state.get('build',0):self.status(result='up_to_date');self.cleanup();return
  if m['build']==self.read_failed_build():self.status(result='failed_build_waiting_for_new_version');return
  raw=download(m['payload'],16000000);m,files=decode_release(e,raw,self.config,self.state.get('build',0))
  try:self.apply(m,files)
  except Exception:
   write_atomic(self.home/'failed_build.json',json.dumps({'build':m['build']}).encode());raise
 def cleanup(self):
  # Somente lixo gerado pelo proprio atualizador e cache Python antigo.
  removed=[];now=time.time()
  backups=self.home/'backups'
  folders=sorted((p for p in backups.iterdir() if p.is_dir() and not p.is_symlink()),key=lambda p:p.stat().st_mtime,reverse=True) if backups.exists() else []
  for p in folders[5:]:
   if now-p.stat().st_mtime>14*86400 and str(p)!=self.state.get('backup'):
    shutil.rmtree(p);removed.append(str(p.relative_to(self.root)))
  for p in self.home.glob('*.update-tmp'):
   if p.is_file() and not p.is_symlink() and now-p.stat().st_mtime>86400:p.unlink();removed.append(str(p.relative_to(self.root)))
  for folder in (self.root/'__pycache__',self.root/'static'/'__pycache__'):
   if folder.is_dir() and not folder.is_symlink():
    for p in folder.glob('*.pyc'):
     if p.is_file() and not p.is_symlink() and now-p.stat().st_mtime>7*86400:p.unlink();removed.append(str(p.relative_to(self.root)))
  write_atomic(self.home/'cleanup.json',json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'removed':removed,'preserved_backups_minimum':5},ensure_ascii=False,indent=2).encode())
 def read_failed_build(self):
  p=self.home/'failed_build.json'
  return json.loads(p.read_text()).get('build') if p.exists() else None

@contextlib.contextmanager
def single_instance(path):
 import msvcrt
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a+b') as f:
  f.seek(0);f.write(b'0');f.flush();f.seek(0)
  try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise RuntimeError('Atualizador ja esta em execucao')
  try:yield
  finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

def main():
 root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
 home=root/'automatic_updates';home.mkdir(exist_ok=True)
 from logging.handlers import RotatingFileHandler
 logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(home/'updater.log',maxBytes=1000000,backupCount=3,encoding='utf-8')],format='%(asctime)s %(levelname)s %(message)s')
 try:
  with single_instance(home/'updater.lock'):
   u=Updater(root);u.run()
 except Exception as error:
  logging.exception('Atualizacao nao concluida')
  # Sem conteudo de credenciais nos avisos.
  write_atomic(home/'last_error.txt',(type(error).__name__+': '+str(error)[:300]).encode());return 1
 return 0
if __name__=='__main__':sys.exit(main())
