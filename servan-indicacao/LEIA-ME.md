# LP Indicação Servan — como colocar no ar (≈10 min)

Planilha: [Servan — Indicações Vaga Comercial (LP)](https://docs.google.com/spreadsheets/d/1zKrSYXdeSDsKxPbpyK9irYaOJu7OjONbgogDz8JICJc/edit) (pasta Servan no Drive)

## 1. Ligar a planilha (obrigatório)
1. Abra a planilha → **Extensões → Apps Script**.
2. Apague o conteúdo e cole o `Code.gs` desta pasta. Salve.
3. Selecione a função `testar` → **Executar** → autorize com a conta Leaderei. Confira a linha de teste na planilha e apague-a.
4. **Implantar → Nova implantação → Tipo: App da Web**
   - Executar como: **Eu**
   - Quem pode acessar: **Qualquer pessoa**
5. Copie a URL que termina em `/exec`.

## 2. Publicar a LP — escolha uma

**A) URL limpa (recomendado)** — Netlify Drop
1. Em `index.html`, troque `COLE_AQUI_A_URL_DO_APPS_SCRIPT` pela URL `/exec`.
2. Arraste a pasta em https://app.netlify.com/drop → gera o link. Renomeie o subdomínio (ex.: `indique-servan.netlify.app`).

**B) Zero hospedagem** — o próprio Apps Script serve a página
1. No Apps Script: **+ → HTML**, nome `index`, cole o conteúdo de `index.html`.
2. **Implantar → Gerenciar implantações → editar → Nova versão**. O link `/exec` já é a LP.
   Limitação: o Google pode exibir uma faixa "criado por usuário do Apps Script" no topo.

## 3. Identidade visual
Logo oficial já embutido no HTML. Paleta extraída do logo: petróleo `#18515C`, turquesa `#0A9DA3`, cinza `#5F605F` (bloco `:root` no topo do `index.html`).

## 4. Teste final
Envie uma indicação pelo celular → confira a linha na planilha → apague.
