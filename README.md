# Leaderei · Landing pages

Páginas da Leaderei e de clientes, publicadas via GitHub Pages em **https://leaderei.github.io/pagina-aplicacao/**.

| Página | Link | Planilha |
|---|---|---|
| Servan · Indicação vaga comercial | https://leaderei.github.io/pagina-aplicacao/servan/indicacao/ | [Sheets](https://docs.google.com/spreadsheets/d/1zKrSYXdeSDsKxPbpyK9irYaOJu7OjONbgogDz8JICJc/edit) |

## Estrutura

```
docs/                      ← tudo aqui vira site (GitHub Pages: branch main, pasta /docs)
  assets/js/lead-form.js   ← formulário genérico (validação, anti-spam, envio p/ Sheets)
  <cliente>/<pagina>/      ← uma pasta por página: index.html, styles.css, imagens
apps-script/               ← backend de cada formulário (cola na planilha, não é publicado)
  <cliente>-<pagina>.gs
```

## Nova página em 4 passos

1. Copie `docs/servan/indicacao/` para `docs/<cliente>/<pagina>/` e troque textos, logo e cores (`:root` no `styles.css`).
2. Crie a planilha, abra **Extensões → Apps Script**, cole um `.gs` de `apps-script/` (ajuste `SHEET_ID` e `COLUNAS` com os `name` dos campos) e implante como **App da Web** (Executar como: Eu · Acesso: Qualquer pessoa).
3. Coloque a URL `/exec` no `data-endpoint` do `<form class="lead-form">`.
4. Commit no `main` → no ar em ~1 min em `https://leaderei.github.io/pagina-aplicacao/<cliente>/<pagina>/`.

Páginas têm `noindex` e `robots.txt` bloqueia buscadores: só acessa quem recebe o link.
