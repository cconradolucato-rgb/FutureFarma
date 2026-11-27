"""Recupera somente a colisao identificada do config do primeiro instalador."""
from pathlib import Path
import hashlib,json,os,sys,zipfile
from datetime import datetime

MAX_FILES=5000
SKIP={'.venv','venv','.git','static','data','__pycache__','automatic_updates','automatic_recovery','node_modules'}
def parse(raw):
 try:return json.loads(raw.decode('utf-8-sig'))
 except (ValueError,UnicodeError):return None

def collision(cfg):return isinstance(cfg,dict) and isinstance(cfg.get('public_key'),str) and isinstance(cfg.get('decrypt_key'),str) and 'sql_server' not in cfg

def native_supported(root):
 reader=root/'reader.py';script=root/'coletar_servidor.ps1';helper=root/'coletor_json_nativo.ps1'
 if not all(p.is_file() for p in (reader,script,helper)):return False
 texts=[p.read_text(encoding='utf-8-sig',errors='replace') for p in (reader,script,helper)]
 return 'powershell_local' in texts[0] and '[FutureFarma.NativeCollector]::Run' in texts[1] and 'Integrated Security=True' in texts[1] and 'class NativeCollector' in texts[2]

def valid(cfg,root):
 if not isinstance(cfg,dict) or not isinstance(cfg.get('sql_server'),dict):return False
 db=cfg['sql_server']
 if db.get('enabled') is not True:return False
 if db.get('transport')=='powershell_local':return native_supported(root)
 # Nao troca para outro transporte ou reconstrói credenciais.
 return False

def candidates(root):
 found=[];count=0
 for current,dirs,files in os.walk(root):
  rel=Path(current).relative_to(root)
  dirs[:]=[d for d in dirs if d.lower() not in SKIP and len(rel.parts)<4]
  for name in files:
   count+=1
   if count>MAX_FILES:return found
   path=Path(current)/name
   if path==root/'config.json' or path.is_symlink():continue
   low=name.lower()
   if low.startswith('config') and (low.endswith(('.json','.bak','.backup')) or '.json.' in low):
    if path.stat().st_size>200000:continue
    raw=path.read_bytes();cfg=parse(raw)
    if valid(cfg,root):found.append((path.stat().st_mtime,str(path),raw,cfg))
   elif low.endswith('.zip') and path.stat().st_size<100000000:
    try:
     with zipfile.ZipFile(path) as z:
      for item in z.infolist()[:3000]:
       if Path(item.filename).name.lower()=='config.json' and item.file_size<=200000:
        raw=z.read(item);cfg=parse(raw)
        if valid(cfg,root):found.append((path.stat().st_mtime,str(path)+'!'+item.filename,raw,cfg))
    except (ValueError,OSError,zipfile.BadZipFile):pass
 return found

def recover(root):
 root=Path(root).resolve();target=root/'config.json'
 for required in ('server.py','reader.py','static/index.html'):
  if not (root/required).is_file():raise ValueError('Pasta incorreta; falta '+required)
 raw=target.read_bytes();current=parse(raw)
 if not collision(current):
  if isinstance(current,dict) and isinstance(current.get('sql_server'),dict):return {'result':'unchanged','message':'Configuracao do painel ja preservada.'}
  raise ValueError('Configuracao nao corresponde a colisao conhecida. Nenhum arquivo alterado.')
 copies=sorted(candidates(root),key=lambda x:x[0],reverse=True)
 if copies:
  _,source,new_raw,cfg=copies[0]
 else:
  if not native_supported(root):raise ValueError('Nao foi encontrada copia valida nem coletor nativo compativel; configuracao atual preservada.')
  source='Configuracao original conhecida: coletor local Windows, 30 segundos'
  cfg={'sql_server':{'enabled':True,'transport':'powershell_local','poll_seconds':30}}
  new_raw=(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode()
 # Apenas config.json e arquivos de registro desta recuperacao sao escritos.
 backup=root/'automatic_recovery'/datetime.now().strftime('%Y%m%d_%H%M%S_%f');backup.mkdir(parents=True)
 (backup/'config_do_pacote_antigo.json').write_bytes(raw)
 tmp=target.with_suffix('.recovery-tmp');tmp.write_bytes(new_raw);tmp.replace(target)
 result={'result':'restored','source':source,'backup':str(backup),'config_sha256':hashlib.sha256(new_raw).hexdigest(),'message':'Configuracao SQL restaurada. Senha, metas e historicos nao alterados.'}
 (backup/'recovery_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 return result
if __name__=='__main__':
 try:
  result=recover(sys.argv[1]);print(result['message']);print('Origem:',result.get('source','configuracao atual'));print('Backup:',result.get('backup','nao necessario'))
 except Exception as error:print(type(error).__name__+': '+str(error));sys.exit(1)
