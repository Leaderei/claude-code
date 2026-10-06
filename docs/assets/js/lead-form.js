/**
 * lead-form.js — formulário genérico das landing pages Leaderei.
 *
 * Uso na página:
 *   <form class="lead-form" data-endpoint="URL /exec do Apps Script" data-success="id-da-tela-de-obrigado" novalidate>
 *     ...campos com name="..." (required, type="tel", type="email" são validados)
 *     <input class="hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">  (anti-spam)
 *     <button type="submit">…</button>
 *     <p class="err" role="alert"></p>
 *   </form>
 *   <div id="id-da-tela-de-obrigado" hidden> … <button type="button" data-reset>Enviar outra</button></div>
 *
 * Os campos chegam ao Apps Script (doPost) como e.parameter.<name>.
 */
(function () {
  'use strict';

  var MSG = {
    required: 'Preencha os campos obrigatórios.',
    tel: 'Confira o WhatsApp informado (com DDD).',
    email: 'Confira o e-mail informado.',
    fail: 'Não foi possível enviar agora. Tente novamente em instantes.',
    sending: 'Enviando…'
  };

  function digits(v) { return (v || '').replace(/\D/g, ''); }

  function validate(form) {
    var fields = form.querySelectorAll('input, textarea, select');
    for (var i = 0; i < fields.length; i++) {
      var el = fields[i];
      if (!el.name || el.name === 'website') continue;
      var empty = el.type === 'radio'
        ? !form.querySelector('input[name="' + el.name + '"]:checked')
        : el.type === 'checkbox' ? !el.checked : !el.value.trim();
      if (el.required && empty) { el.focus(); return MSG.required; }
      if (el.type === 'tel' && el.value && digits(el.value).length < 10) { el.focus(); return MSG.tel; }
      if (el.type === 'email' && el.value && !/^\S+@\S+\.\S+$/.test(el.value)) { el.focus(); return MSG.email; }
    }
    return '';
  }

  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  /**
   * Envio resiliente:
   * 1) até 3 tentativas confirmadas (CORS: o Apps Script responde {"ok":true});
   * 2) se o navegador bloquear a leitura da resposta, última tentativa em no-cors.
   * Em falha, o formulário continua preenchido para a pessoa tentar de novo.
   */
  function send(endpoint, data) {
    var body = data.toString();
    var headers = { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' };
    function attempt(n) {
      return fetch(endpoint, { method: 'POST', headers: headers, body: body })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j && j.ok) return true;
          throw new Error((j && j.erro) || 'resposta inválida');
        })
        .catch(function (e) {
          if (n < 3) return wait(n * 1500).then(function () { return attempt(n + 1); });
          if (e instanceof TypeError) {
            return fetch(endpoint, { method: 'POST', mode: 'no-cors', headers: headers, body: body });
          }
          throw e;
        });
    }
    return attempt(1);
  }

  function setup(form) {
    var btn = form.querySelector('[type="submit"]');
    var label = btn.textContent;
    var err = form.querySelector('.err');
    var success = document.getElementById(form.dataset.success);

    function reset() {
      btn.disabled = false;
      btn.textContent = label;
    }

    function done() {
      form.hidden = true;
      if (success) {
        success.hidden = false;
        success.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    function fail() {
      reset();
      err.textContent = MSG.fail;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      err.textContent = '';
      if (form.website && form.website.value) return; // honeypot
      var msg = validate(form);
      if (msg) { err.textContent = msg; return; }

      var data = new URLSearchParams();
      new FormData(form).forEach(function (v, k) {
        if (k !== 'website') data.append(k, String(v).trim());
      });
      data.append('pagina', location.pathname);
      data.append('envio_id', Date.now().toString(36) + Math.random().toString(36).slice(2, 8));

      btn.disabled = true;
      btn.textContent = MSG.sending;
      send(form.dataset.endpoint, data).then(done, fail);
    });

    if (success) {
      var again = success.querySelector('[data-reset]');
      if (again) again.addEventListener('click', function () {
        form.reset();
        reset();
        success.hidden = true;
        form.hidden = false;
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  }

  document.querySelectorAll('form.lead-form').forEach(setup);

  // Rolagem suave para âncoras internas
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var t = document.querySelector(a.getAttribute('href'));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });
})();
