# Future Farma — canal de atualizações

Este repositório hospeda o cliente genérico de atualização e releases **criptografados e assinados** do painel comercial. Não contém configurações, senhas, registros de vendas ou históricos da empresa.

O servidor verifica `releases/stable.json` a cada dois minutos. A instalação inicial fixa a chave pública de assinatura e mantém a chave de decifragem somente no servidor autorizado. Alterar este repositório não autoriza um pacote sem assinatura válida.

O atualizador preserva `config.json`, a pasta `data` e as configurações editadas pelo dashboard. Antes de instalar, faz backup dos arquivos afetados; se as verificações falharem, restaura a versão anterior.

Limpeza: temporários do atualizador após um dia, cache Python após sete dias e backups próprios com mais de 14 dias, preservando pelo menos cinco e o backup da versão atual. Não remove arquivos desconhecidos.

A tarefa do Windows executa com a conta usada na instalação. Essa conta precisa continuar com sessão iniciada; desconectar o RDP é permitido, encerrar a sessão pausa as verificações até o próximo login. Não abre portas de entrada na rede.

## Desenvolvimento

```bash
cd autoupdate
python -m unittest test_updater -v
```

Publicação de um novo pacote: veja `AGENTS.md`. A chave privada e a chave de decifragem nunca devem ser incluídas em commits ou logs.
