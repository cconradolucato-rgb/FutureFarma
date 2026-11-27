# Atualizações do painel Future Farma

O usuário autorizou um canal automático para aplicar as alterações do painel que solicitar. A versão publicada em releases/stable.json será instalada no servidor Windows. Não publique experimentos ou alterações fora do pedido do usuário.

- Antes de publicar, leia o manifesto atual e preserve as configurações do dashboard como fonte de metas/taxas. Dados do cliente, senhas, config.json e data/* nunca entram no pacote.
- Este repositório é público. O código de negócio do painel só pode ser publicado dentro do payload cifrado gerado por autoupdate/publish.py. Não adicione fontes decifrados ao Git.
- As chaves estão fora do Git em /workspace/work/auto_update_private/release_keys.json (permissão 600). Se ausentes, não gere uma nova chave silenciosamente: o servidor mantém a chave antiga fixada. Explique o bloqueio e recupere o acesso autorizado.
- Para preparar a fonte atual, use autoupdate/extract_current.py. Os arquivos decifrados devem ficar fora deste repositório, por exemplo /workspace/work/auto_release_payload.
- Teste a mudança e execute os testes de autoupdate. Use build inteiro estritamente maior que o último publicado, por exemplo 2026112702 depois de 2026112701.
- Gere o payload com `python autoupdate/publish.py /workspace/work/auto_release_payload BUILD VERSAO`. Revise a lista exata de arquivos e hashes. Publique o .bin e stable.json juntos em um commit na main.
- Após push, leia os arquivos publicados, confirme assinatura, decifragem e hashes. Não afirme que o Windows instalou apenas porque o push deu certo: a conexão atual não fornece o status do servidor. Peça o status local apenas quando necessário.
- A política de limpeza remove somente temporários/cache e backups administrados pelo atualizador, mantendo os mais recentes. Não amplie para arquivos desconhecidos ou dados comerciais.

- Desde 2026.11.27.5, o cliente consulta a referencia Git main e baixa o manifesto pela revisao imutavel, evitando cache. Em falha da consulta Git, mantem o fallback assinado. O reader inclui migracao versionada do cliente original para CLIENT_BUILD=2026112705 e ajusta a tarefa existente para 60 segundos, validando caminho e preservando identidade/configuracao. Nao remova essa migracao sem considerar servidores ainda na versao inicial.
