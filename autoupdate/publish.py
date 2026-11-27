"""Publica somente payload cifrado. Chaves ficam fora do repositorio."""
from pathlib import Path
import argparse,base64,hashlib,io,json,os,zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from updater import canonical,valid_path
REPO=Path(__file__).resolve().parent.parent
SECRET=Path('/workspace/work/auto_update_private/release_keys.json')
def keys():
 if not SECRET.exists():raise SystemExit('Chaves privadas ausentes. Nao gere outra chave para servidor ja instalado.')
 return json.loads(SECRET.read_text())
def publish(source,build,version):
 k=keys();files={}
 source=Path(source)
 for p in sorted(source.rglob('*')):
  if p.is_file():
   n=p.relative_to(source).as_posix();valid_path(n);files[n]=p.read_bytes()
 if not files:raise ValueError('Pacote vazio')
 for n,b in files.items():
  if n.endswith('.py'):compile(b.decode('utf-8'),n,'exec')
 raw=io.BytesIO()
 with zipfile.ZipFile(raw,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in files.items():z.writestr(n,b)
 product='futurefarma-commercial';nonce=os.urandom(12)
 encrypted=AESGCM(bytes.fromhex(k['decrypt_key'])).encrypt(nonce,raw.getvalue(),canonical({'build':build,'product':product}))
 rel='releases/'+str(build)+'.bin'
 manifest={'schema':1,'product':product,'build':build,'version':version,'rule_version':'2026-11-27-dashboard-bonus','payload':rel,'nonce':base64.b64encode(nonce).decode(),'cipher_sha256':hashlib.sha256(encrypted).hexdigest(),'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
 private=Ed25519PrivateKey.from_private_bytes(bytes.fromhex(k['sign_private']))
 sig=private.sign(canonical(manifest))
 (REPO/rel).write_bytes(encrypted)
 (REPO/'releases/stable.json').write_bytes(canonical({'manifest':manifest,'signature':base64.b64encode(sig).decode()}))
 print('Release cifrado preparado:',build,'arquivos:',len(files))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('build',type=int);p.add_argument('version');a=p.parse_args();publish(a.source,a.build,a.version)
