/**
 * Servan — LP de indicação para vaga comercial
 * Recebe o formulário e grava na planilha "Servan — Indicações Vaga Comercial (LP)".
 *
 * Backend do formulário de https://leaderei.github.io/servan/indicacao/
 * Fica em Extensões > Apps Script da planilha, implantado como App da Web
 * (Executar como: Eu · Acesso: Qualquer pessoa). A página faz POST para a URL /exec.
 */

const SHEET_ID = '1zKrSYXdeSDsKxPbpyK9irYaOJu7OjONbgogDz8JICJc';

// Ordem das colunas na planilha (cabeçalho da linha 1)
const COLUNAS = [
  ['Data/hora', (d) => new Date()],
  ['Quem indica — Nome', (d) => d.ind_nome],
  ['Quem indica — Vínculo', (d) => d.ind_vinculo],
  ['Pessoa indicada — Nome', (d) => d.nome],
  ['Pessoa indicada — WhatsApp', (d) => d.whatsapp],
  ['Pessoa indicada — E-mail', (d) => d.email],
  ['Pessoa indicada — LinkedIn/Instagram', (d) => d.social],
  ['Pessoa indicada — Atuação atual', (d) => d.atuacao],
  ['Por que combina com o Servan', (d) => d.motivo],
  ['Pessoa indicada sabe da indicação?', (d) => d.sabe],
  ['Status', (d) => 'Nova'],
  ['Responsável', (d) => ''],
  ['Próximo passo', (d) => ''],
  ['Observações', (d) => ''],
];

function salvarIndicacao(d) {
  d = d || {};
  if (d.website) return { ok: true }; // honeypot
  if (!d.ind_nome || !d.nome || !d.whatsapp) throw new Error('Campos obrigatórios ausentes');

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
    // Mantém o cabeçalho da linha 1 sempre igual a COLUNAS
    const cab = COLUNAS.map((c) => c[0]);
    const atual = sh.getLastRow() ? sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0] : [];
    if (atual.join('|') !== cab.join('|')) {
      if (atual.length > cab.length) sh.getRange(1, cab.length + 1, 1, atual.length - cab.length).clearContent();
      sh.getRange(1, 1, 1, cab.length).setValues([cab]).setFontWeight('bold');
      sh.setFrozenRows(1);
    }
    // Prefixo ' evita que o Sheets interprete telefone/fórmula
    const linha = COLUNAS.map((c, i) => {
      const v = c[1](d);
      if (i === 0) return v;
      return typeof v === 'string' && /^[=+\-@0-9(]/.test(v) ? "'" + v.slice(0, 2000) : (v || '').toString().slice(0, 2000);
    });
    sh.appendRow(linha);
  } finally {
    lock.releaseLock();
  }
  return { ok: true };
}

// Recebe o POST do formulário (lead-form.js)
function doPost(e) {
  try {
    salvarIndicacao(e.parameter);
    return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, erro: String(err) })).setMimeType(ContentService.MimeType.JSON);
  }
}

// O link antigo (/exec) agora só aponta para a página no GitHub Pages
const URL_PAGINA = 'https://leaderei.github.io/servan/indicacao/';
function doGet() {
  return HtmlService.createHtmlOutput(
    '<p style="font-family:sans-serif">A página mudou de endereço: ' +
    '<a href="' + URL_PAGINA + '" target="_top">clique aqui para indicar</a>.</p>' +
    '<script>window.open("' + URL_PAGINA + '", "_top");</script>'
  ).setTitle('Indique para o Servan');
}

// Rode 1x pelo editor para autorizar e testar (grava uma linha de teste)
function testar() {
  salvarIndicacao({ ind_nome: 'TESTE', ind_vinculo: 'Colaborador(a)', nome: 'TESTE — apagar', whatsapp: '67999999999', motivo: 'teste', sabe: 'Sim' });
}
