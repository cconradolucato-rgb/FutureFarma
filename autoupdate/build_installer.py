"""Gera instalador privado, sempre fora da arvore publica."""
from pathlib import Path
import json,shutil,sys,zipfile
from publish import keys,REPO

def build(destination):
 dest=Path(destination).resolve()
 if dest==REPO or REPO in dest.parents:raise ValueError('Instalador contem chave de leitura; destino deve ficar fora do repositorio publico.')
 dest.mkdir(parents=True,exist_ok=True)
 for name in ('updater.py','restart_panel.ps1','install.ps1'):shutil.copy2(REPO/'autoupdate'/name,dest/name)
 k=keys();config=dest/'update_channel.json';config.write_text(json.dumps({n:k[n] for n in ('public_key','decrypt_key')},indent=2));config.chmod(0o600)
 (dest/'INSTALAR.bat').write_text('@echo off\ncd /d "%~dp0"\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"\npause\n',encoding='ascii')
 (dest/'LEIA_PRIMEIRO.txt').write_text('''INSTALADOR CORRIGIDO 2026.11.27.2
1. Dentro da Area de Trabalho Remota do servidor 192.168.0.32, extraia TODO este
   pacote em Downloads\\AtualizadorFutureFarma. Nao e preciso copiar para a pasta do painel.
2. Execute INSTALAR.bat e aceite a janela de administrador.
3. Selecione a pasta PRINCIPAL FutureFarma_Servidor com server.py, config.json,
   static, data e .venv. Nao selecione a pasta do chat AvisosFutura.
4. Aguarde INSTALACAO CONCLUIDA. O painel e atualizado na primeira execucao.
5. No navegador, Ctrl+F5; confirme Comissao: regra 27/11 ativa.

Verifica novas versoes assinadas a cada 2 minutos, com backup e restauracao.
Nenhuma configuracao de senha, meta, taxa ou data/* e substituida.
O arquivo update_channel.json configura SOMENTE o atualizador. Nao e o config do painel.
Mantenha a conta do Windows com sessao iniciada; pode desconectar o RDP.
Nao encerre a sessao se quiser manter o atualizador ativo.

Se houver falha, a mensagem COMPLETA fica em instalacao.log nesta pasta.
Esse arquivo e o necessario para diagnosticar qualquer falha de instalacao.
Status apos instalar: automatic_updates\\status.json dentro da pasta do painel.
Historico de erros: automatic_updates\\updater.log e last_error.txt.

Este pacote e privado e contem a chave de leitura do canal. Guarde-o na empresa.
Para pausar: desative FutureFarma-Atualizacao-Automatica no Agendador de Tarefas.
''',encoding='utf-8')
 expected={'updater.py','restart_panel.ps1','install.ps1','update_channel.json','INSTALAR.bat','LEIA_PRIMEIRO.txt'}
 zip_path=dest.parent/(dest.name+'.zip')
 with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
  for name in sorted(expected):z.write(dest/name,name)
 with zipfile.ZipFile(zip_path) as z:
  assert z.testzip() is None and set(z.namelist())==expected
 print('Instalador privado gerado:',zip_path)
 return zip_path
if __name__=='__main__':build(sys.argv[1])
