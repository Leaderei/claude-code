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

      btn.disabled = true;
      btn.textContent = MSG.sending;
      // no-cors: o Apps Script não devolve CORS; a resposta é opaca
      fetch(form.dataset.endpoint, { method: 'POST', mode: 'no-cors', body: data })
        .then(done)
        .catch(fail);
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
