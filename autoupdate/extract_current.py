from pathlib import Path
import json,sys
from updater import decode_release
from publish import keys,REPO
if __name__=='__main__':
 dest=Path(sys.argv[1]).resolve()
 if dest==REPO or REPO in dest.parents:raise SystemExit('Extraia somente para fora do repositorio publico.')
 e=json.loads((REPO/'releases/stable.json').read_text());k=keys();m,files=decode_release(e,(REPO/e['manifest']['payload']).read_bytes(),k)
 for n,b in files.items():p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 print('Fonte decifrada localmente:',len(files),'arquivos, versao',m['version'])
