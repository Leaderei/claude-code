# LP Indicação Servan — colocar no ar (5 min)

Tudo está em um arquivo só: `Code.gs` (script + página).

1. Abra a planilha "Servan — Indicações Vaga Comercial (LP)" → **Extensões → Apps Script**.
2. Apague o que estiver lá, cole todo o `Code.gs`, clique em **Salvar**.
3. Escolha a função `testar` → **Executar** → autorize (Avançado → Acessar projeto). Apague a linha TESTE da planilha.
4. **Implantar → Nova implantação → engrenagem → App da Web** · Executar como: **Eu** · Quem pode acessar: **Qualquer pessoa** → Implantar.
5. Copie a URL `/exec`: esse é o link da LP.

Alterou o código? **Implantar → Gerenciar implantações → lápis → Versão: Nova versão**. O link não muda.

Obs.: `Code.gs` embute o `index.html` (constante `PAGINA`). Editou o HTML? Regere o `Code.gs`.
