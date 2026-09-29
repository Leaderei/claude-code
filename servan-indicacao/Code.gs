/**
 * Servan — LP de indicação para vaga comercial
 * Recebe o formulário e grava na planilha "Servan — Indicações Vaga Comercial (LP)".
 *
 * Funciona de dois jeitos (escolha um no LEIA-ME):
 *  A) LP hospedada fora (Netlify/GitHub Pages) -> POST para doPost
 *  B) LP servida pelo próprio Apps Script      -> doGet + google.script.run
 */

const SHEET_ID = '1zKrSYXdeSDsKxPbpyK9irYaOJu7OjONbgogDz8JICJc';

// Ordem das colunas na planilha (cabeçalho da linha 1)
const COLUNAS = [
  ['Data/hora', (d) => new Date()],
  ['Quem indica — Nome', (d) => d.ind_nome],
  ['Quem indica — Vínculo', (d) => d.ind_vinculo],
  ['Indicada — Nome', (d) => d.nome],
  ['Indicada — WhatsApp', (d) => d.whatsapp],
  ['Indicada — E-mail', (d) => d.email],
  ['Indicada — LinkedIn/Instagram', (d) => d.social],
  ['Indicada — Atuação atual', (d) => d.atuacao],
  ['Por que combina com o Servan', (d) => d.motivo],
  ['Indicada sabe da indicação?', (d) => d.sabe],
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

// Opção A: LP hospedada fora
function doPost(e) {
  try {
    salvarIndicacao(e.parameter);
    return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, erro: String(err) })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Opção B: a própria URL do Apps Script serve a LP (arquivo HTML "index" no projeto)
function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('Indique para o Servan')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// Rode 1x pelo editor para autorizar e testar (grava uma linha de teste)
function testar() {
  salvarIndicacao({ ind_nome: 'TESTE', ind_vinculo: 'Colaborador(a)', nome: 'TESTE — apagar', whatsapp: '67999999999', motivo: 'teste', sabe: 'Sim' });
}
