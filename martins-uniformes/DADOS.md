# Onde ficam os dados do Sistema Martins (e regras para não perder nada)

**Casa dos dados:** banco da nuvem do artifact (capability `db`).
- Cada cadastro é um documento: `pedidos/`, `lotes/`, `pessoas/`, `produtos/`, `clientes/`, `arquivos/`, `usuarios/`, etc.
- As configurações ficam em `config/main`.
- O histórico fica em `log/` (um documento por semana e por aparelho).
- Imagens e arquivos grandes (mockups, artes, bordados) ficam em partes: `mock/<id>` (resumo) + `mockp/<id>~N` (conteúdo).
- O aparelho guarda uma cópia local para funcionar sem internet.

## Proteções
1. **Lixeira:** nada é apagado de vez. Antes de apagar um documento, o app grava uma cópia em `lixeira/` (60 dias). Dá para restaurar em Cadastros › Ajustes › Cópias de segurança.
2. **Cópia diária:** `backup/<AAAA-MM-DD>` + `backupp/` com o estado completo. Ficam 14 dias. Também há cópia antes de apagar exemplos e antes de restaurar.
3. **Cópia em arquivo:** botão "Baixar cópia em arquivo" (JSON) e "Restaurar de um arquivo".
4. **Trava de reinicialização:** a tela "Vamos começar" nunca aparece se já existir qualquer pedido, lote, pessoa, produto ou empresa na nuvem.
5. **Mockups e arquivos:** o envio é conferido. Se falhar, o app tenta de novo e conserta sozinho.

## Regras para qualquer atualização futura do código
- **Nunca** tirar um nome da lista `COLS`, nem renomear uma coleção. Só acrescentar.
- Migração de formato: **copiar primeiro, conferir, só depois deixar de usar o antigo**. Nunca apagar dado antigo na mesma versão.
- Novos campos entram com valor padrão em `normalizar()` e `cfgDefaults()`, sem remover campos existentes.
- Antes de publicar, rodar:
  - `NODE_PATH=$(npm root -g) node martins-uniformes/tests/dados-persistem.test.js`
  - `NODE_PATH=$(npm root -g) node martins-uniformes/tests/mockup-original.test.js`
- Para mudanças grandes, fazer um ensaio com uma cópia dos dados reais: baixar as coleções com o ArtifactData, carregar num banco falso e conferir que nada sumiu.
