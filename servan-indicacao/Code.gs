/**
 * Servan — LP de indicação para vaga comercial
 * Recebe o formulário e grava na planilha "Servan — Indicações Vaga Comercial (LP)".
 *
 * Arquivo único: cole tudo em Extensões > Apps Script da planilha e implante como App da Web.
 * A URL /exec gerada É a landing page.
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

// Opção A: LP hospedada fora
function doPost(e) {
  try {
    salvarIndicacao(e.parameter);
    return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, erro: String(err) })).setMimeType(ContentService.MimeType.JSON);
  }
}

// A própria URL do app da Web serve a LP (HTML embutido abaixo)
function doGet() {
  return HtmlService.createHtmlOutput(PAGINA)
    .setTitle('Indique para o Servan')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// Rode 1x pelo editor para autorizar e testar (grava uma linha de teste)
function testar() {
  salvarIndicacao({ ind_nome: 'TESTE', ind_vinculo: 'Colaborador(a)', nome: 'TESTE — apagar', whatsapp: '67999999999', motivo: 'teste', sabe: 'Sim' });
}

// ===== LANDING PAGE (gerada a partir de index.html — não editar à mão) =====
const PAGINA = `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Indique para o Servan</title>
<meta name="description" content="Conhece alguém que combina com o Servan? Indique para a vaga na área comercial.">
<meta name="robots" content="noindex, nofollow">
<meta property="og:title" content="Conhece alguém que combina com o Servan?">
<meta property="og:description" content="Sua indicação pode nos ajudar a encontrar a pessoa certa para crescer junto com o Servan.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Exo+2:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  /* ==========================================================
     IDENTIDADE VISUAL — trocar aqui pelas cores oficiais Servan
     ========================================================== */
  :root {
    --brand: #18515C;         /* petróleo Servan (logo) */
    --brand-ink: #FFFFFF;     /* texto sobre a cor principal */
    --teal: #0A9DA3;          /* turquesa Servan (logo) — detalhes */
    --accent: #0A858A;        /* turquesa escurecido p/ botões (contraste AA) */
    --accent-hover: #18515C;
    --bg: #F3F7F7;            /* fundo da página */
    --surface: #FFFFFF;       /* cartões e formulário */
    --text: #1F2A2D;
    --muted: #5F605F;         /* cinza Servan (logo) */
    --line: #D5E0E1;
    --error: #B42318;
    --radius: 14px;
    --font-title: "Exo 2", "Segoe UI", system-ui, sans-serif;
    --font-body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  }

  /* ===== CONFIG: URL do app da Web do Apps Script (ver LEIA-ME.md) ===== */
</style>
<script>
  window.SERVAN_ENDPOINT = "COLE_AQUI_A_URL_DO_APPS_SCRIPT";
</script>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: var(--font-body); font-size: 17px; line-height: 1.6;
  }
  .wrap { max-width: 720px; margin: 0 auto; padding: 0 20px; }

  .topbar { background: var(--surface); border-bottom: 4px solid var(--teal); }
  .topbar .wrap { padding-top: 16px; padding-bottom: 16px; }
  .logo { display: flex; align-items: center; min-height: 44px; }
  .logo img { height: 44px; width: auto; display: block; }
  @media (min-width: 600px) { .logo img { height: 52px; } }
  .logo .wordmark { font-family: var(--font-title); font-style: italic; font-size: 26px; font-weight: 700; letter-spacing: .04em; color: var(--brand); }
  header.hero { background: var(--brand); color: var(--brand-ink); padding: 48px 0 64px; position: relative; overflow: hidden; }
  header.hero::after { content: ""; position: absolute; right: -120px; top: -80px; width: 320px; height: 320px; border-radius: 50%; border: 48px solid var(--teal); opacity: .18; pointer-events: none; }
  header.hero .wrap { position: relative; z-index: 1; }
  .eyebrow { color: #7FD3D6; }
  .logo .wordmark small { display: block; font-family: var(--font-body); font-size: 11px; font-weight: 500; letter-spacing: .18em; text-transform: uppercase; opacity: .75; }
  .eyebrow { font-size: 13px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; margin: 0 0 12px; }
  h1 { font-family: var(--font-title); font-weight: 700; font-size: clamp(32px, 7vw, 48px); line-height: 1.1; margin: 0 0 20px; }
  .hero p { font-size: 18px; opacity: .92; margin: 0 0 14px; max-width: 60ch; }
  .btn {
    display: inline-block; background: var(--accent); color: #fff; border: 0; cursor: pointer;
    font: 600 16px/1 var(--font-body); padding: 17px 30px; border-radius: 999px; text-decoration: none;
    transition: background .15s ease, transform .15s ease;
  }
  .btn:hover { background: var(--accent-hover); }
  .btn:active { transform: translateY(1px); }
  .btn:disabled { opacity: .6; cursor: wait; }
  .hero .btn { margin-top: 18px; }

  section { padding: 56px 0; }
  h2 { font-family: var(--font-title); font-weight: 600; color: var(--brand); font-size: clamp(26px, 5vw, 34px); line-height: 1.2; margin: 0 0 16px; }
  .intro p { margin: 0 0 14px; }
  .note { display: flex; gap: 12px; align-items: flex-start; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px 18px; margin-top: 22px; font-size: 15px; color: var(--muted); }
  .note svg { flex: none; margin-top: 3px; color: var(--accent); }

  .card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 28px 22px; }
  fieldset { border: 0; margin: 0 0 28px; padding: 0; }
  legend { font-family: var(--font-title); font-size: 21px; font-weight: 600; color: var(--brand); margin-bottom: 14px; padding: 0; }
  .field { margin-bottom: 16px; }
  label { display: block; font-size: 15px; font-weight: 500; margin-bottom: 6px; }
  label .opt { font-weight: 400; color: var(--muted); }
  input[type=text], input[type=email], input[type=tel], textarea, select {
    width: 100%; font: 400 16px/1.4 var(--font-body); color: var(--text);
    background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 13px 14px;
  }
  textarea { min-height: 110px; resize: vertical; }
  input:focus, textarea:focus, select:focus { outline: 2px solid var(--accent); outline-offset: 1px; border-color: var(--accent); }
  .row { display: grid; grid-template-columns: 1fr; gap: 0 14px; }
  @media (min-width: 600px) { .row { grid-template-columns: 1fr 1fr; } .card { padding: 36px 34px; } }
  .choices { display: flex; flex-wrap: wrap; gap: 10px; }
  .choice { position: relative; }
  .choice input { position: absolute; opacity: 0; inset: 0; }
  .choice span { display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 10px 18px; font-size: 15px; cursor: pointer; background: #fff; }
  .choice input:checked + span { background: var(--brand); color: var(--brand-ink); border-color: var(--brand); }
  .choice input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }
  .consent { display: flex; gap: 10px; align-items: flex-start; font-size: 14px; color: var(--muted); font-weight: 400; }
  .consent input { margin-top: 4px; width: 18px; height: 18px; flex: none; accent-color: var(--accent); }
  .privacy { margin-top: 24px; border-top: 1px solid var(--line); padding-top: 18px; font-size: 14px; color: var(--muted); }
  .privacy summary { cursor: pointer; font-weight: 600; color: var(--brand); }
  .privacy ul { padding-left: 18px; margin: 8px 0 0; }
  .privacy li { margin-bottom: 6px; }
  .consent a, .privacy a { color: var(--accent); }
  .hp { position: absolute; left: -9999px; }
  .err { color: var(--error); font-size: 14px; margin: 8px 0 0; min-height: 1em; }
  .submit { display: flex; flex-direction: column; gap: 10px; align-items: stretch; }
  @media (min-width: 600px) { .submit { align-items: flex-start; } }

  .thanks { display: none; text-align: center; padding: 48px 22px; }
  .thanks .check { width: 64px; height: 64px; border-radius: 50%; background: var(--teal); color: #fff; display: grid; place-items: center; margin: 0 auto 18px; }
  .thanks p { color: var(--muted); max-width: 46ch; margin: 0 auto 20px; }
  .link-btn { background: none; border: 0; color: var(--accent); font: 600 15px var(--font-body); cursor: pointer; text-decoration: underline; }

  footer { background: var(--brand); color: var(--brand-ink); padding: 40px 0; text-align: center; }
  footer p { font-family: var(--font-title); font-weight: 600; font-size: 20px; margin: 0; }
  footer small { display: block; margin-top: 10px; font-size: 13px; opacity: .7; }
</style>
</head>
<body>

<div class="topbar">
  <div class="wrap">
    <div class="logo">
      <img src="data:image/png;base64,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" alt="Servan Anestesiologia" onerror="this.remove(); document.getElementById('wm').hidden=false;">
      <div class="wordmark" id="wm" hidden>SERVAN<small>Anestesiologia</small></div>
    </div>
  </div>
</div>

<header class="hero">
  <div class="wrap">
    <p class="eyebrow">Programa de indicação</p>
    <h1>Conhece alguém que combina com o Servan?</h1>
    <p>Estamos buscando um novo talento para integrar nosso time na área comercial.</p>
    <p>Queremos encontrar alguém que tenha facilidade para se comunicar e criar boas relações. E quem melhor para nos ajudar nessa busca do que as pessoas que já fazem parte da nossa história?</p>
    <a class="btn" href="#indicar">Indicar agora</a>
  </div>
</header>

<section class="intro">
  <div class="wrap">
    <h2>Sua indicação é importante</h2>
    <p>Se você é sócio ou colaborador do Servan e conhece alguém em quem confia e que acredita ter esse perfil, queremos conhecer essa pessoa.</p>
    <p>Preencha o formulário com a sua indicação. Nossa equipe dará continuidade ao processo de forma reservada e entrará em contato com a pessoa indicada.</p>
    <div class="note">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
      <span>As informações são tratadas com sigilo e usadas somente neste processo seletivo.</span>
    </div>
  </div>
</section>

<section id="indicar" style="padding-top:0">
  <div class="wrap">
    <div class="card">
      <form id="form" novalidate>
        <fieldset>
          <legend>Seus dados</legend>
          <div class="field">
            <label for="ind_nome">Seu nome</label>
            <input type="text" id="ind_nome" name="ind_nome" autocomplete="name" required>
          </div>
          <div class="field">
            <label id="vinc_lbl">Você é</label>
            <div class="choices" role="radiogroup" aria-labelledby="vinc_lbl">
              <label class="choice"><input type="radio" name="ind_vinculo" value="Sócio(a)" required><span>Sócio(a)</span></label>
              <label class="choice"><input type="radio" name="ind_vinculo" value="Colaborador(a)"><span>Colaborador(a)</span></label>
            </div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Pessoa indicada</legend>
          <div class="field">
            <label for="nome">Nome completo</label>
            <input type="text" id="nome" name="nome" required>
          </div>
          <div class="row">
            <div class="field">
              <label for="whatsapp">WhatsApp</label>
              <input type="tel" id="whatsapp" name="whatsapp" inputmode="tel" placeholder="(67) 9 0000-0000" required>
            </div>
            <div class="field">
              <label for="email">E-mail <span class="opt">(opcional)</span></label>
              <input type="email" id="email" name="email">
            </div>
          </div>
          <div class="row">
            <div class="field">
              <label for="social">LinkedIn ou Instagram <span class="opt">(opcional)</span></label>
              <input type="text" id="social" name="social" placeholder="link ou @perfil">
            </div>
            <div class="field">
              <label for="atuacao">Onde trabalha hoje <span class="opt">(opcional)</span></label>
              <input type="text" id="atuacao" name="atuacao" placeholder="empresa ou função">
            </div>
          </div>
          <div class="field">
            <label for="motivo">Por que essa pessoa combina com o Servan?</label>
            <textarea id="motivo" name="motivo" placeholder="De onde vocês se conhecem, no que se destaca, como se relaciona com as pessoas…" required></textarea>
          </div>
          <div class="field">
            <label id="sabe_lbl">A pessoa sabe que você está indicando?</label>
            <div class="choices" role="radiogroup" aria-labelledby="sabe_lbl">
              <label class="choice"><input type="radio" name="sabe" value="Sim" required><span>Sim</span></label>
              <label class="choice"><input type="radio" name="sabe" value="Ainda não"><span>Ainda não</span></label>
            </div>
          </div>
        </fieldset>

        <div class="field">
          <label class="consent">
            <input type="checkbox" name="consentimento" value="Sim" required>
            <span>Declaro que compartilho estes dados de boa-fé, somente para este processo seletivo, e estou ciente de que a pessoa indicada poderá ser contatada pela equipe do Servan. <a href="#privacidade">Como usamos os dados</a>.</span>
          </label>
        </div>

        <input class="hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">

        <div class="submit">
          <button class="btn" type="submit" id="send">Enviar indicação</button>
          <p class="err" id="err" role="alert"></p>
        </div>
      </form>

      <details class="privacy" id="privacidade">
        <summary>Como usamos os dados (LGPD)</summary>
        <p>Os dados enviados aqui são usados <strong>exclusivamente</strong> para avaliar a indicação e, se houver interesse, convidar a pessoa indicada a participar do processo seletivo da área comercial do Servan.</p>
        <ul>
          <li><strong>Quem trata:</strong> Servan Anestesiologia, com apoio da consultoria que conduz o recrutamento.</li>
          <li><strong>Transparência:</strong> no primeiro contato, a pessoa indicada é informada de onde vieram seus dados e pode pedir a exclusão a qualquer momento.</li>
          <li><strong>Prazo:</strong> os dados são mantidos apenas até o encerramento do processo seletivo e depois excluídos.</li>
          <li><strong>Seleção:</strong> a avaliação considera somente competências e experiência para a função, sem distinção de gênero, idade, raça, estado civil ou qualquer outra característica pessoal.</li>
          <li><strong>Seus direitos:</strong> para acessar, corrigir ou excluir dados, fale com <a href="mailto:marketing@servan.com.br">marketing@servan.com.br</a>.</li>
        </ul>
      </details>

      <div class="thanks" id="thanks" aria-live="polite">
        <div class="check"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg></div>
        <h2>Indicação recebida. Obrigado!</h2>
        <p>Nossa equipe vai dar continuidade de forma reservada e entrará em contato com a pessoa indicada.</p>
        <button class="link-btn" type="button" id="again">Fazer outra indicação</button>
      </div>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    <p>Sua indicação pode nos ajudar a encontrar a pessoa certa para crescer junto com o Servan.</p>
    <small>Servan · Campo Grande/MS</small>
  </div>
</footer>

<script>
(function () {
  var form = document.getElementById('form');
  var btn = document.getElementById('send');
  var err = document.getElementById('err');
  var thanks = document.getElementById('thanks');

  function digits(v) { return (v || '').replace(/\\D/g, ''); }

  function validate() {
    var missing = [];
    form.querySelectorAll('[required]').forEach(function (el) {
      if (el.type === 'radio') {
        if (!form.querySelector('input[name="' + el.name + '"]:checked')) missing.push(el);
      } else if (el.type === 'checkbox') {
        if (!el.checked) missing.push(el);
      } else if (!el.value.trim()) missing.push(el);
    });
    if (missing.length) { missing[0].focus(); return 'Preencha os campos obrigatórios.'; }
    if (digits(form.whatsapp.value).length < 10) {
      return 'Confira o WhatsApp da pessoa indicada (com DDD).';
    }
    if (form.email.value && !/^\\S+@\\S+\\.\\S+$/.test(form.email.value)) return 'Confira o e-mail informado.';
    return '';
  }

  function done() {
    form.style.display = 'none';
    thanks.style.display = 'block';
    thanks.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function fail() {
    btn.disabled = false; btn.textContent = 'Enviar indicação';
    err.textContent = 'Não foi possível enviar agora. Tente novamente em instantes.';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    err.textContent = '';
    if (form.website.value) return; // honeypot anti-spam
    var msg = validate();
    if (msg) { err.textContent = msg; return; }

    var data = {};
    new FormData(form).forEach(function (v, k) { if (k !== 'website') data[k] = String(v).trim(); });

    btn.disabled = true; btn.textContent = 'Enviando…';

    // Servido pelo próprio Apps Script (doGet): usa google.script.run
    if (window.google && google.script && google.script.run) {
      google.script.run.withSuccessHandler(done).withFailureHandler(fail).salvarIndicacao(data);
      return;
    }
    // Hospedado fora (Netlify, GitHub Pages etc.): POST para o app da Web
    fetch(window.SERVAN_ENDPOINT, { method: 'POST', mode: 'no-cors', body: new URLSearchParams(data) })
      .then(done).catch(fail);
  });

  // Links internos com rolagem via JS (funciona também dentro do Apps Script)
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var t = document.querySelector(a.getAttribute('href'));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });

  document.querySelector('a[href="#privacidade"]').addEventListener('click', function () { document.getElementById('privacidade').open = true; });

  document.getElementById('again').addEventListener('click', function () {
    form.reset(); btn.disabled = false; btn.textContent = 'Enviar indicação';
    thanks.style.display = 'none'; form.style.display = 'block';
    document.getElementById('indicar').scrollIntoView({ behavior: 'smooth' });
  });
})();
</script>
</body>
</html>
`;
