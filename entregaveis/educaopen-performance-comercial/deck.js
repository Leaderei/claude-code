// Apresentação executiva — Educa Open · Performance Comercial (jun–set/2026)
// Sistema visual: leaderei-brand / references/deck-system.md
const fs = require('fs'), pptxgen = require('pptxgenjs');
const pres = new pptxgen(); pres.layout = 'LAYOUT_WIDE';
pres.author = 'Leaderei'; pres.company = 'Leaderei';
pres.title = 'Educa Open — Performance Comercial (jun–set/2026)';

const O = 'DF4E01', W = 'FFFFFF', G = 'A0A0A0', M = '6E6E76', HAIR = '2B2B2B', BAR = '5A5A5A', LIT = 'E9E9E9', F = 'Manrope';
const im = p => 'image/' + (p.endsWith('.png') ? 'png' : 'jpeg') + ';base64,' + fs.readFileSync('./assets/' + p).toString('base64');
const BG = { hero: im('bg_hero.jpg'), content: im('bg_content.jpg'), feature: im('bg_feature.jpg'), close: im('bg_close.jpg') };
const LOGO = im('logo_white.png'), GLOW = im('glow.png');

const S = k => { const s = pres.addSlide(); s.addImage({ data: BG[k || 'content'], x: 0, y: 0, w: 13.333, h: 7.5 }); return s; };
const glow = (s, x, y, d, t) => s.addImage({ data: GLOW, x: x - d / 2, y: y - d / 2, w: d, h: d, transparency: t === undefined ? 60 : t });
const mark = s => s.addImage({ data: LOGO, x: 11.93, y: 6.95, w: 0.9, h: 0.2, transparency: 35 });
const hair = (s, y, x, w, c) => s.addShape(pres.ShapeType.line, { x, y, w, h: 0, line: { color: c || HAIR, width: 0.75 } });
const vhair = (s, x, y, h, c) => s.addShape(pres.ShapeType.line, { x, y, w: 0, h, line: { color: c || HAIR, width: 0.75 } });
const dot = (s, x, y, d, c) => s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: c || O }, line: { color: c || O, width: 0 } });
const bar = (s, x, y, w, h, c) => s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: c }, line: { width: 0 } });
const T = (s, t, o) => s.addText(t, Object.assign({ fontFace: F, margin: 0, color: W }, o));
const label = (s, t, x, y, c) => {
  dot(s, x === undefined ? 0.72 : x, (y === undefined ? 0.62 : y) + 0.045, 0.075, c);
  T(s, t.toUpperCase(), { x: (x === undefined ? 0.72 : x) + 0.2, y: (y === undefined ? 0.62 : y) - 0.06, w: 11, h: 0.3, fontSize: 10, bold: true, color: c || O, charSpacing: 3.2, valign: 'middle' });
};
const head = (s, t, size, y) => T(s, t, { x: 0.7, y: y === undefined ? 1.0 : y, w: 11.9, h: 1.05, fontSize: size || 38, bold: true, lineSpacing: (size || 38) * 1.12, charSpacing: -0.7 });
const foot = (s, t, y) => T(s, t, { x: 0.7, y: y === undefined ? 7.02 : y, w: 11.0, h: 0.2, fontSize: 9, color: M, valign: 'middle' });

/* ══════════════ 1 · CAPA ══════════════ */
{
  const s = S('hero');
  s.addImage({ data: LOGO, x: 0.85, y: 0.85, w: 2.05, h: 0.45 });
  label(s, 'Reunião de performance · time comercial', 0.87, 2.60);
  T(s, 'Educa Open\nPerformance comercial', { x: 0.82, y: 2.95, w: 10.5, h: 2.0, fontSize: 54, bold: true, lineSpacing: 60, charSpacing: -1.2 });
  T(s, 'O que o funil mostra de junho a setembro de 2026 — onde estamos ganhando,\nonde estamos perdendo receita e o que precisa mudar até o fim do semestre.', { x: 0.85, y: 5.15, w: 9.0, h: 0.9, fontSize: 16, color: G, lineSpacing: 25 });
  hair(s, 6.35, 0.85, 5.0);
  T(s, 'PERÍODO JUN–SET/2026   ·   DADOS DO PIPEDRIVE ATÉ 04/09   ·   SETEMBRO PARCIAL', { x: 0.85, y: 6.55, w: 11, h: 0.28, fontSize: 9.5, bold: true, color: M, charSpacing: 2 });
  T(s, 'LEADEREI  ·  CONSULTORIA DE VENDAS B2B', { x: 0.85, y: 6.85, w: 11, h: 0.28, fontSize: 9.5, bold: true, color: M, charSpacing: 2 });
  s.addNotes('Abertura. A mensagem do deck é uma só: o topo de funil já responde, o problema migrou para o fechamento.');
}

/* ══════════════ 2 · PANORAMA (grade de KPIs) ══════════════ */
{
  const s = S();
  label(s, 'Panorama do período');
  head(s, 'Agosto bateu a meta.\nSetembro é o teste.', 40);
  hair(s, 2.62, 0.7, 11.93);
  const KPI = [
    ['36', W, 'Agendamentos em agosto', '129% da meta  ·  +64% vs. julho'],
    ['12', W, 'Negócios ganhos jun–set', 'R$ 498,5 mil em contratos'],
    ['19%', O, 'Fechamento / propostas', 'padrão Leaderei: 25–40%'],
    ['44', W, 'Meta de setembro', 'maior do semestre  ·  ritmo 48%'],
  ];
  KPI.forEach((k, i) => {
    const x = 0.7 + i * 3.0;
    if (i > 0) vhair(s, x - 0.3, 2.95, 1.25);
    T(s, k[0], { x, y: 2.95, w: 2.7, h: 0.8, fontSize: 50, bold: true, color: k[1], charSpacing: -1.8, valign: 'middle' });
    T(s, k[2].toUpperCase(), { x, y: 3.8, w: 2.75, h: 0.26, fontSize: 10, bold: true, color: G, charSpacing: 1.6, valign: 'middle' });
    T(s, k[3], { x, y: 4.08, w: 2.85, h: 0.26, fontSize: 11.5, color: M, valign: 'middle' });
  });
  hair(s, 4.6, 0.7, 11.93);
  const L = [
    ['O topo respondeu', 'De 4 reuniões em junho para 36 em agosto. A máquina de agendamento está de pé.'],
    ['O fundo travou', '62 propostas enviadas viraram 12 negócios ganhos. É onde a receita está parando.'],
    ['Resultado concentrado', 'Parcerias e indicações são 4% das entradas e 58% dos ganhos.'],
    ['Ticket abaixo do plano', 'R$ 41,5 mil de ticket médio contra os R$ 50 mil assumidos.'],
  ];
  L.forEach((l, i) => {
    const x = 0.7 + i * 3.0;
    if (i > 0) vhair(s, x - 0.3, 4.95, 1.3);
    dot(s, x, 5.06, 0.085);
    T(s, l[0], { x: x + 0.24, y: 4.95, w: 2.62, h: 0.28, fontSize: 14, bold: true, charSpacing: -0.3, valign: 'middle' });
    T(s, l[1], { x, y: 5.42, w: 2.72, h: 0.9, fontSize: 12, color: G, lineSpacing: 17 });
  });
  foot(s, 'Fontes: funil da Educa Open no Pipedrive e planilha de metas do 2º semestre. Setembro parcial: 4 de 21 dias úteis.');
  mark(s);
  s.addNotes('Slide de abertura da discussão. Deixe claro que a crítica não é ao topo de funil — agosto foi o melhor mês do projeto. A conversa do dia é sobre o que acontece depois da proposta.');
}

/* ══════════════ 3 · TOPO DE FUNIL X META (gráfico) ══════════════ */
{
  const s = S();
  label(s, 'Topo de funil');
  head(s, 'Nove vezes mais reuniões em três meses.', 36);
  const BASE = 5.35, HMAX = 2.5, K = HMAX / 44;
  const MESES = [['jun', 4, null, 'sem meta definida'], ['jul', 22, 39, '56% da meta'], ['ago', 36, 28, '129% da meta'], ['set*', 4, 44, 'ritmo: 48%']];
  MESES.forEach((m, i) => {
    const gx = 0.9 + i * 1.75, bw = 0.95, bx = gx + (1.55 - bw) / 2;
    const bh = Math.max(m[1] * K, 0.035);
    bar(s, bx, BASE - bh, bw, bh, i === 2 ? LIT : BAR);
    T(s, String(m[1]), { x: bx - 0.3, y: BASE - bh - 0.32, w: bw + 0.6, h: 0.28, fontSize: 15, bold: true, color: i === 2 ? W : G, align: 'center', valign: 'middle' });
    if (m[2] !== null) {
      const my = BASE - m[2] * K;
      s.addShape(pres.ShapeType.line, { x: bx - 0.16, y: my, w: bw + 0.32, h: 0, line: { color: O, width: 1.75 } });
      T(s, 'meta ' + m[2], { x: bx + bw + 0.22, y: my - 0.13, w: 0.85, h: 0.26, fontSize: 10, bold: true, color: O, valign: 'middle' });
    }
    T(s, m[0], { x: bx - 0.3, y: BASE + 0.08, w: bw + 0.6, h: 0.24, fontSize: 13, color: G, align: 'center', valign: 'middle' });
    T(s, m[3], { x: bx - 0.55, y: BASE + 0.34, w: bw + 1.1, h: 0.24, fontSize: 10, bold: true, color: i === 2 ? O : M, align: 'center', valign: 'middle' });
  });
  hair(s, BASE, 0.7, 7.1, '3A3A3A');
  vhair(s, 8.35, 2.35, 3.4);
  T(s, 'O QUE ISSO SIGNIFICA', { x: 8.75, y: 2.4, w: 3.9, h: 0.26, fontSize: 10, bold: true, color: O, charSpacing: 3 });
  T(s, 'A operação de pré-venda saiu do zero. Julho ficou em 56% da meta — mês de rampa. Agosto virou a chave e entregou 129%.', { x: 8.75, y: 2.85, w: 3.85, h: 1.3, fontSize: 15, color: W, lineSpacing: 22 });
  hair(s, 4.35, 8.75, 3.85);
  T(s, 'O ALERTA', { x: 8.75, y: 4.6, w: 3.9, h: 0.26, fontSize: 10, bold: true, color: O, charSpacing: 3 });
  T(s, 'A meta de setembro (44) é 57% maior que o realizado de agosto e a maior do semestre. Outubro e novembro pedem 56.', { x: 8.75, y: 5.05, w: 3.85, h: 1.3, fontSize: 15, color: G, lineSpacing: 22 });
  foot(s, 'Topo de funil = reuniões de diagnóstico criadas no mês (Pipedrive). Metas conforme planilha do 2º semestre.  *Setembro parcial: 4 de 21 dias úteis.');
  mark(s);
  s.addNotes('Reconheça a virada de agosto — é mérito do time. Em seguida, plante o alerta: a curva de metas do semestre sobe (44, 56, 56) e o ritmo de setembro está na metade do necessário.');
}

/* ══════════════ 4 · RECEITA (lista editorial) ══════════════ */
{
  const s = S('feature');
  label(s, 'Resultado financeiro');
  head(s, 'R$ 498,5 mil ganhos em quatro meses.', 36);
  const R = [
    ['jun', '4', 'R$ 205,0 mil', 'R$ 51,3 mil', 'Melhor mês em ticket médio'],
    ['jul', '2', 'R$ 9,5 mil', 'R$ 4,8 mil', 'Dois negócios pequenos — puxam a média para baixo'],
    ['ago', '5', 'R$ 249,0 mil', 'R$ 49,8 mil', 'Recorde em quantidade e em valor'],
    ['set*', '1', 'R$ 35,0 mil', 'R$ 35,0 mil', 'Parcial — 4 dias úteis'],
  ];
  T(s, 'MÊS', { x: 0.7, y: 2.5, w: 0.9, h: 0.24, fontSize: 9, bold: true, color: M, charSpacing: 1.5 });
  T(s, 'GANHOS', { x: 1.7, y: 2.5, w: 0.9, h: 0.24, fontSize: 9, bold: true, color: M, charSpacing: 1.5, align: 'right' });
  T(s, 'VALOR', { x: 2.9, y: 2.5, w: 1.6, h: 0.24, fontSize: 9, bold: true, color: M, charSpacing: 1.5, align: 'right' });
  T(s, 'TICKET MÉDIO', { x: 4.8, y: 2.5, w: 1.6, h: 0.24, fontSize: 9, bold: true, color: M, charSpacing: 1.5, align: 'right' });
  R.forEach((r, i) => {
    const y = 2.85 + i * 0.72;
    hair(s, y, 0.7, 11.93);
    T(s, r[0], { x: 0.7, y: y + 0.2, w: 0.9, h: 0.32, fontSize: 17, bold: true, color: G, valign: 'middle' });
    T(s, r[1], { x: 1.7, y: y + 0.2, w: 0.9, h: 0.32, fontSize: 17, bold: true, align: 'right', valign: 'middle' });
    T(s, r[2], { x: 2.9, y: y + 0.2, w: 1.6, h: 0.32, fontSize: 17, bold: true, align: 'right', valign: 'middle' });
    T(s, r[3], { x: 4.8, y: y + 0.2, w: 1.6, h: 0.32, fontSize: 17, color: G, align: 'right', valign: 'middle' });
    T(s, r[4], { x: 6.9, y: y + 0.22, w: 5.7, h: 0.32, fontSize: 13, color: M, valign: 'middle' });
  });
  hair(s, 2.85 + 4 * 0.72, 0.7, 11.93, O);
  T(s, 'total', { x: 0.7, y: 5.95, w: 0.9, h: 0.34, fontSize: 17, bold: true, color: O, valign: 'middle' });
  T(s, '12', { x: 1.7, y: 5.95, w: 0.9, h: 0.34, fontSize: 17, bold: true, color: O, align: 'right', valign: 'middle' });
  T(s, 'R$ 498,5 mil', { x: 2.9, y: 5.95, w: 1.6, h: 0.34, fontSize: 17, bold: true, color: O, align: 'right', valign: 'middle' });
  T(s, 'R$ 41,5 mil', { x: 4.8, y: 5.95, w: 1.6, h: 0.34, fontSize: 17, bold: true, color: O, align: 'right', valign: 'middle' });
  T(s, 'Ticket implícito do plano: R$ 50 mil. O realizado está 17% abaixo.', { x: 6.9, y: 5.96, w: 5.7, h: 0.34, fontSize: 13, bold: true, color: W, valign: 'middle' });
  foot(s, 'Valores conforme relatório de negócios ganhos do Pipedrive (arredondados na origem). Ticket implícito do plano = R$ 2.127.500 ÷ 42,55 clientes.');
  mark(s);
  s.addNotes('Julho distorce a média: dois negócios de R$ 4,8 mil. Junho e agosto mostram o ticket real da operação, próximo de R$ 50 mil — que é o que o plano assume.');
}

/* ══════════════ 5 · SAÚDE DO FUNIL (funil deitado) ══════════════ */
{
  const s = S();
  label(s, 'Saúde do funil · acumulado do projeto');
  head(s, 'O funil só quebra depois da proposta.', 36);
  const ET = [
    ['Pesquisa', 915, null, null], ['Em cadência', 815, '89%', '−100'], ['Engajado', 247, '30%', '−568'],
    ['Diagnóstico agendado', 125, '51%', '−122'], ['Diagnóstico realizado', 114, '91%', '−11'],
    ['Validação externa', 103, '90%', '−11'], ['Proposta enviada', 62, '60%', '−41'],
    ['Contrato enviado', 20, '32%', '−42'], ['Ganho', 12, '60%', '−8'],
  ];
  const XB = 3.05, WMAX = 5.9, KK = WMAX / 915;
  T(s, 'ETAPA', { x: 0.7, y: 2.25, w: 2.2, h: 0.22, fontSize: 8.5, bold: true, color: M, charSpacing: 1.3 });
  T(s, 'NEGÓCIOS', { x: 9.15, y: 2.25, w: 1.0, h: 0.22, fontSize: 8.5, bold: true, color: M, charSpacing: 1.3, align: 'right' });
  T(s, 'CONVERSÃO', { x: 10.35, y: 2.25, w: 1.15, h: 0.22, fontSize: 8.5, bold: true, color: M, charSpacing: 1.3, align: 'right' });
  T(s, 'PERDA', { x: 11.65, y: 2.25, w: 0.98, h: 0.22, fontSize: 8.5, bold: true, color: M, charSpacing: 1.3, align: 'right' });
  ET.forEach((e, i) => {
    const y = 2.55 + i * 0.42;
    hair(s, y, 0.7, 11.93);
    const crit = i === 7;
    const bw = Math.max(e[1] * KK, 0.06);
    bar(s, XB, y + 0.14, bw, 0.24, crit ? O : (i === 8 ? LIT : BAR));
    T(s, e[0], { x: 0.7, y: y + 0.12, w: 2.3, h: 0.28, fontSize: 13, bold: crit, color: crit ? W : G, valign: 'middle' });
    T(s, String(e[1]), { x: 9.15, y: y + 0.12, w: 1.0, h: 0.28, fontSize: 13.5, bold: true, color: W, align: 'right', valign: 'middle' });
    if (e[2]) T(s, e[2], { x: 10.35, y: y + 0.12, w: 1.15, h: 0.28, fontSize: 13.5, bold: crit, color: crit ? O : G, align: 'right', valign: 'middle' });
    if (e[3]) T(s, e[3], { x: 11.65, y: y + 0.12, w: 0.98, h: 0.28, fontSize: 13, color: crit ? O : M, align: 'right', valign: 'middle' });
  });
  hair(s, 2.55 + 9 * 0.42, 0.7, 11.93);
  T(s, 'Do diagnóstico à validação externa o funil segura 90% a cada passo. Da proposta para o contrato ele perde 68%.', { x: 0.7, y: 6.48, w: 11.9, h: 0.3, fontSize: 13.5, bold: true, color: W, valign: 'middle' });
  foot(s, 'Relatório de conversão do funil no Pipedrive, acumulado do projeto. Conversão = passagem da etapa anterior para a etapa da linha.', 6.95);
  mark(s);
  s.addNotes('Este é o slide central do deck. O meio do funil é forte: 91% de comparecimento, 90% de avanço para validação externa. A ruptura é proposta → contrato enviado: 62 para 20.');
}

/* ══════════════ 6 · CONTRA O PADRÃO (confronto tipográfico) ══════════════ */
{
  const s = S();
  label(s, 'Comparação com o padrão Leaderei');
  head(s, 'Dois indicadores acima do padrão.\nUm abaixo — e é o que vale dinheiro.', 34);
  const B = [
    ['9%', 'NO-SHOW SOBRE AGENDADOS', 'padrão: até 10–20%', 'Acima do padrão', W, '114 diagnósticos realizados de 125 agendados. Confirmação de reunião está funcionando.'],
    ['54%', 'REUNIÃO → PROPOSTA', 'padrão: 50–70%', 'Dentro do padrão', W, '62 propostas sobre 114 diagnósticos realizados. A qualificação está entregando.'],
    ['19%', 'FECHAMENTO SOBRE PROPOSTAS', 'padrão: 25–40%', 'Abaixo do padrão', O, '12 ganhos sobre 62 propostas. Cada ponto percentual aqui vale ~R$ 25 mil.'],
  ];
  B.forEach((b, i) => {
    const x = 0.7 + i * 4.07;
    if (i > 0) vhair(s, x - 0.36, 2.75, 3.3);
    T(s, b[0], { x, y: 2.8, w: 3.6, h: 0.85, fontSize: 58, bold: true, color: b[4], charSpacing: -2.2, valign: 'middle' });
    if (i === 2) glow(s, x + 0.55, 3.22, 2.6, 62);
    T(s, b[1], { x, y: 3.78, w: 3.7, h: 0.26, fontSize: 10, bold: true, color: G, charSpacing: 1.6, valign: 'middle' });
    T(s, b[2], { x, y: 4.06, w: 3.7, h: 0.26, fontSize: 12, color: M, valign: 'middle' });
    hair(s, 4.48, x, 3.6, i === 2 ? O : HAIR);
    T(s, b[3], { x, y: 4.62, w: 3.7, h: 0.28, fontSize: 14, bold: true, color: b[4], valign: 'middle' });
    T(s, b[5], { x, y: 5.0, w: 3.6, h: 0.9, fontSize: 12.5, color: G, lineSpacing: 17 });
  });
  T(s, 'Ressalva: 103 negócios em validação externa e 62 em proposta seguem em aberto — parte fecha e puxa os 19% para cima.', { x: 0.7, y: 6.35, w: 11.9, h: 0.3, fontSize: 12.5, color: G, valign: 'middle' });
  foot(s, 'Padrões: benchmarks de conversão Leaderei para processos bem executados. Base: funil acumulado da Educa Open no Pipedrive.', 7.02);
  mark(s);
  s.addNotes('Use os benchmarks para tirar o julgamento da conversa. O time está acima do padrão em duas das três métricas. Isso dá autoridade para cobrar a terceira. R$ 25 mil por ponto percentual = 62 propostas x 1% x ticket de R$ 41,5 mil.');
}

/* ══════════════ 7 · QUEM AGENDA X QUEM FECHA (matriz) ══════════════ */
{
  const s = S();
  label(s, 'Desempenho por canal · acumulado');
  head(s, 'Quem agenda não é quem fecha.', 36);
  const C = [
    ['Parcerias / Indicações', '30', '83%', '14', '50%', '7', 'Dobrar a aposta', O],
    ['Eventos', '38', '66%', '13', '8%', '1', 'Corrigir o fundo', W],
    ['ABM', '24', '8%', '2', '100%', '2', 'Falta volume, não qualidade', W],
    ['Dripify', '175', '4%', '3', '0%', '0', 'Revisar ou desligar', G],
    ['Webinar', '510', '3%', '4', '25%', '1', 'Revisar ou desligar', G],
  ];
  const CX = [[0.7, 2.6, 'left'], [3.4, 0.95, 'right'], [4.5, 1.45, 'right'], [6.1, 1.1, 'right'], [7.35, 1.35, 'right'], [8.8, 0.85, 'right'], [10.1, 2.53, 'left']];
  const CH = ['CANAL', 'ENTRADAS', 'VIRA REUNIÃO', 'PROPOSTAS', 'FECHA', 'GANHOS', 'LEITURA'];
  CH.forEach((h, i) => T(s, h, { x: CX[i][0], y: 2.42, w: CX[i][1], h: 0.24, fontSize: 8.5, bold: true, color: M, charSpacing: 1.3, align: CX[i][2] }));
  C.forEach((c, i) => {
    const y = 2.78 + i * 0.68;
    hair(s, y, 0.7, 11.93);
    const strong = i === 0;
    T(s, c[0], { x: CX[0][0], y: y + 0.18, w: CX[0][1], h: 0.32, fontSize: 16, bold: strong, color: strong ? W : G, valign: 'middle' });
    T(s, c[1], { x: CX[1][0], y: y + 0.18, w: CX[1][1], h: 0.32, fontSize: 16, color: G, align: 'right', valign: 'middle' });
    T(s, c[2], { x: CX[2][0], y: y + 0.18, w: CX[2][1], h: 0.32, fontSize: 16, bold: true, color: i < 2 ? W : M, align: 'right', valign: 'middle' });
    T(s, c[3], { x: CX[3][0], y: y + 0.18, w: CX[3][1], h: 0.32, fontSize: 16, color: G, align: 'right', valign: 'middle' });
    T(s, c[4], { x: CX[4][0], y: y + 0.18, w: CX[4][1], h: 0.32, fontSize: 16, bold: true, color: (i === 0 || i === 2) ? W : M, align: 'right', valign: 'middle' });
    T(s, c[5], { x: CX[5][0], y: y + 0.18, w: CX[5][1], h: 0.32, fontSize: 16, bold: strong, color: strong ? O : G, align: 'right', valign: 'middle' });
    T(s, c[6], { x: CX[6][0], y: y + 0.2, w: CX[6][1], h: 0.32, fontSize: 12.5, bold: strong, color: c[7], valign: 'middle' });
  });
  hair(s, 2.78 + 5 * 0.68, 0.7, 11.93);
  T(s, '4% das entradas geram 58% dos ganhos.  ·  88% do volume de entrada gerou 1 negócio.', { x: 0.7, y: 6.35, w: 11.9, h: 0.3, fontSize: 14, bold: true, color: W, valign: 'middle' });
  foot(s, 'Vira reunião = diagnósticos agendados ÷ entradas.  Fecha = ganhos ÷ propostas enviadas.  41% dos negócios de meio de funil estão sem canal de origem no CRM.', 7.02);
  mark(s);
  s.addNotes('O canal frio não é ruim por definição — o ABM fecha 100% do que agenda, só não agenda. Já Dripify e Webinar falham nas duas pontas. Eventos é o caso mais caro: agenda muito e não fecha.');
}

/* ══════════════ 8 · CANAIS FRIOS (split manifesto) ══════════════ */
{
  const s = S();
  label(s, 'Diagnóstico dos canais frios');
  T(s, '685 leads\nfrios.\n1 negócio\nganho.', { x: 0.7, y: 1.3, w: 5.3, h: 4.0, fontSize: 46, bold: true, lineSpacing: 54, charSpacing: -1.2 });
  hair(s, 5.6, 0.7, 4.9, O);
  T(s, 'Webinar (510) e Dripify (175) somam 88% de tudo que entrou no funil e entregaram um único negócio ganho, de R$ 35 mil.', { x: 0.7, y: 5.85, w: 5.0, h: 1.0, fontSize: 14, color: G, lineSpacing: 20 });
  vhair(s, 6.5, 1.35, 5.0);
  const D = [
    ['WEBINAR · O PROBLEMA É QUALIDADE', 'De 486 leads em cadência, só 31 engajaram (6%). Dos 15 que agendaram, 6 não apareceram — no-show de 40%, contra 9% do funil geral. Quem baixa material de webinar ainda não é comprador.'],
    ['DRIPIFY · O PROBLEMA É INTENÇÃO', '92% dos leads engajam no LinkedIn, mas só 7% viram reunião. Aceitar conexão e curtir não é interesse comercial — falta a ligação que qualifica de verdade.'],
    ['ABM · O PROBLEMA É VOLUME', 'Apenas 24 entradas no acumulado, mas 2 de 2 propostas viraram contrato. É o canal com melhor conversão de fundo e o menor investimento de esforço.'],
  ];
  D.forEach((d, i) => {
    const y = 1.38 + i * 1.85;
    T(s, d[0], { x: 6.95, y, w: 5.7, h: 0.26, fontSize: 10, bold: true, color: O, charSpacing: 2.4 });
    T(s, d[1], { x: 6.95, y: y + 0.42, w: 5.65, h: 1.3, fontSize: 14, color: W, lineSpacing: 21 });
    if (i < 2) hair(s, y + 1.64, 6.95, 5.7);
  });
  foot(s, 'Base: funis por canal no Pipedrive, acumulado do projeto. Dados de topo de funil do ABM sinalizados como inconsistentes na origem.');
  mark(s);
  s.addNotes('Aqui o objetivo é separar “canal ruim” de “execução incompleta”. Dripify não tem ligação na cadência — sem ligação, engajamento no LinkedIn não vira reunião. Webinar precisa de confirmação D-1.');
}

/* ══════════════ 9 · PLANO X RESULTADO (confronto) ══════════════ */
{
  const s = S('feature');
  label(s, 'Alocação de esforço');
  head(s, 'O plano de agosto apostou\nnos canais que menos fecham.', 34);
  T(s, 'ONDE O PLANO ALOCOU A META', { x: 0.7, y: 2.9, w: 5.3, h: 0.26, fontSize: 10, bold: true, color: O, charSpacing: 3 });
  const P = [['ABM', 12, '43%'], ['Dripify', 8, '29%'], ['Parceiros / Indicações', 8, '29%']];
  P.forEach((p, i) => {
    const y = 3.4 + i * 0.78;
    T(s, p[0], { x: 0.7, y, w: 3.0, h: 0.28, fontSize: 14, color: G, valign: 'middle' });
    T(s, p[1] + ' reuniões  ·  ' + p[2], { x: 3.7, y, w: 2.2, h: 0.28, fontSize: 13, bold: true, color: W, align: 'right', valign: 'middle' });
    bar(s, 0.7, y + 0.36, (p[1] / 12) * 5.2, 0.16, BAR);
  });
  vhair(s, 6.5, 2.85, 3.2);
  T(s, 'DE ONDE VIERAM OS 12 GANHOS', { x: 6.95, y: 2.9, w: 5.6, h: 0.26, fontSize: 10, bold: true, color: O, charSpacing: 3 });
  const Q = [['Parcerias / Indicações', 7, '58%', true], ['ABM', 2, '17%', false], ['Eventos', 1, '8%', false], ['Webinar', 1, '8%', false], ['Dripify', 0, '0%', false]];
  Q.forEach((q, i) => {
    const y = 3.4 + i * 0.47;
    T(s, q[0], { x: 6.95, y, w: 3.0, h: 0.26, fontSize: 13.5, bold: q[3], color: q[3] ? W : G, valign: 'middle' });
    T(s, q[1] + '  ·  ' + q[2], { x: 9.95, y, w: 1.5, h: 0.26, fontSize: 13, bold: true, color: q[3] ? O : G, align: 'right', valign: 'middle' });
    bar(s, 11.6, y + 0.07, Math.max((q[1] / 7) * 1.03, 0.03), 0.13, q[3] ? O : BAR);
  });
  hair(s, 6.12, 0.7, 11.93);
  T(s, 'O canal que carrega 58% do resultado recebeu 29% da meta. Dripify recebeu 29% da meta e não fechou nenhum negócio.', { x: 0.7, y: 6.35, w: 11.9, h: 0.3, fontSize: 14, bold: true, color: W, valign: 'middle' });
  foot(s, 'Plano de agosto: planilha semanal de metas por SDR (ABM 12, Dripify 8, Parceiros 8 = 28). Ganhos por canal: Pipedrive, acumulado — 1 dos 12 está sem origem.');
  mark(s);
  s.addNotes('Este é o slide de decisão de alocação. Não é sobre desligar canal frio — é sobre a meta semanal refletir onde o dinheiro está sendo feito hoje.');
}

/* ══════════════ 10 · A CONTA DA META (número dominante) ══════════════ */
{
  const s = S();
  label(s, 'Consistência do plano de metas');
  head(s, 'A meta de clientes não fecha\nna conversão atual.', 34);
  glow(s, 3.0, 4.35, 4.2, 58);
  T(s, '9,6%', { x: 0.7, y: 3.75, w: 4.6, h: 1.2, fontSize: 76, bold: true, color: O, charSpacing: -2.4, valign: 'middle' });
  T(s, 'DIAGNÓSTICO AGENDADO → GANHO (REALIZADO)', { x: 0.7, y: 5.05, w: 5.0, h: 0.26, fontSize: 10, bold: true, color: G, charSpacing: 2 });
  T(s, '12 negócios ganhos sobre 125 diagnósticos agendados.', { x: 0.7, y: 5.38, w: 5.0, h: 0.3, fontSize: 13, color: M });
  vhair(s, 6.3, 2.95, 3.3);
  const N = [
    ['18%', 'É a conversão que o plano assume', '42,55 clientes ÷ 234 agendamentos planejados de julho a dezembro.'],
    ['~443', 'Agendamentos necessários na taxa real', 'Quase o dobro dos 234 planejados para chegar aos mesmos 42,55 clientes.'],
    ['2 saídas', 'Subir a conversão ou rever a meta', 'Subir o fechamento de 19% para o padrão de 25–40% resolve sem dobrar o topo.'],
  ];
  N.forEach((n, i) => {
    const y = 3.05 + i * 1.15;
    T(s, n[0], { x: 6.8, y, w: 1.75, h: 0.42, fontSize: 26, bold: true, color: W, charSpacing: -0.8, valign: 'middle' });
    T(s, n[1], { x: 8.7, y: y + 0.02, w: 3.95, h: 0.32, fontSize: 14, bold: true, valign: 'middle' });
    T(s, n[2], { x: 8.7, y: y + 0.38, w: 3.9, h: 0.6, fontSize: 12, color: G, lineSpacing: 16 });
    if (i < 2) hair(s, y + 1.0, 6.8, 5.83);
  });
  T(s, 'Ressalva: 103 negócios em validação externa e 62 em proposta ainda podem fechar e elevar a taxa realizada.', { x: 0.7, y: 6.5, w: 11.9, h: 0.3, fontSize: 12.5, color: G, valign: 'middle' });
  foot(s, 'Planilha de metas do 2º semestre: 32 pontos × 1,33 cliente/ponto = 42,55 clientes, com 234 agendamentos planejados (jul–dez).');
  mark(s);
  s.addNotes('Não apresente isso como erro de quem montou a meta — apresente como ajuste de premissa depois de quatro meses de dado real. A saída barata é o fechamento, não mais topo de funil.');
}

/* ══════════════ 11 · SETEMBRO (timeline) ══════════════ */
{
  const s = S();
  label(s, 'Setembro · o que o mês exige');
  head(s, '2,1 reuniões por dia útil.\nO ritmo atual é 1,0.', 34);
  const Y = 3.9;
  hair(s, Y, 1.0, 11.1);
  const SEM = [['S1 · 01–04', '4 realizadas', '4 dias úteis', true], ['S2 · 08–11', '10 necessárias', '4 dias úteis', false], ['S3 · 14–18', '12 necessárias', '5 dias úteis', false], ['S4 · 21–25', '12 necessárias', '5 dias úteis', false], ['S5 · 28–30', '6 necessárias', '3 dias úteis', false]];
  SEM.forEach((w, i) => {
    const x = 1.0 + i * 2.5;
    T(s, w[0], { x: x - 0.06, y: Y - 0.95, w: 2.3, h: 0.26, fontSize: 10, bold: true, color: O, charSpacing: 2 });
    T(s, w[1], { x: x - 0.06, y: Y - 0.66, w: 2.3, h: 0.34, fontSize: 19, bold: true, color: w[3] ? G : W, charSpacing: -0.4 });
    dot(s, x - 0.07, Y - 0.07, 0.14, w[3] ? '5A5A5A' : O);
    T(s, w[2], { x: x - 0.06, y: Y + 0.28, w: 2.3, h: 0.26, fontSize: 12.5, color: M });
  });
  hair(s, 5.05, 0.7, 11.93);
  const K2 = [['44', 'META DO MÊS', 'a maior do semestre'], ['21', 'DIAS ÚTEIS', '07/09 é feriado'], ['4', 'REALIZADAS ATÉ 04/09', '1,0 por dia útil'], ['~21', 'PROJEÇÃO NO RITMO ATUAL', '48% da meta']];
  K2.forEach((k, i) => {
    const x = 0.7 + i * 3.0;
    if (i > 0) vhair(s, x - 0.3, 5.35, 1.0);
    T(s, k[0], { x, y: 5.35, w: 2.7, h: 0.6, fontSize: 38, bold: true, color: i === 3 ? O : W, charSpacing: -1.4, valign: 'middle' });
    T(s, k[1], { x, y: 6.0, w: 2.8, h: 0.24, fontSize: 9.5, bold: true, color: G, charSpacing: 1.5, valign: 'middle' });
    T(s, k[2], { x, y: 6.26, w: 2.8, h: 0.24, fontSize: 11.5, color: M, valign: 'middle' });
  });
  foot(s, 'Distribuição semanal calculada sobre os 40 agendamentos restantes em 17 dias úteis (2,4 por dia útil). Reuniões de diagnóstico criadas, conforme Pipedrive.');
  mark(s);
  s.addNotes('Passe a meta de mensal para diária. O time não consegue agir sobre “44 no mês”; consegue agir sobre “2 a 3 reuniões marcadas hoje”. Esse é o número do quadro do War Room.');
}

/* ══════════════ 12 · PLANO DE AÇÃO (grade de filetes) ══════════════ */
{
  const s = S();
  label(s, 'Plano de ação · próximas 4 semanas');
  head(s, 'Onde atacar primeiro.', 38);
  const A = [
    ['S1', 'Força-tarefa nas 42 propostas paradas', 'Classificar viva ou morta, motivo e próximo passo com data. É receita já qualificada esperando.'],
    ['S1', 'Processo pós-reunião estruturado', 'Próximo passo agendado dentro da própria reunião, gatilho de decisão e follow-up em D+2, D+5 e D+10.'],
    ['S2', 'Confirmação de reunião para leads de webinar', 'No-show do canal é 40% contra 9% do geral. Confirmação em D-1 por WhatsApp mais ligação.'],
    ['S2', 'Ligação obrigatória na cadência do Dripify', '92% engajam e 7% agendam. Sem ligação, engajamento no LinkedIn não vira reunião.'],
    ['S3', 'Realocar a meta semanal por canal', 'Puxar volume para ABM e parceria, que fecham. Reduzir peso de webinar e Dripify enquanto não maturam.'],
    ['S3', 'Canal de origem obrigatório no CRM', '41% dos negócios de meio de funil estão sem origem. Sem isso não dá para decidir onde investir.'],
  ];
  A.forEach((a, i) => {
    const col = i % 2, row = Math.floor(i / 2), x = 0.7 + col * 6.15, y = 2.35 + row * 1.5;
    hair(s, y, x, 5.75);
    T(s, a[0], { x, y: y + 0.24, w: 0.55, h: 0.28, fontSize: 11, bold: true, color: O, charSpacing: 1.5, valign: 'middle' });
    T(s, a[1], { x: x + 0.62, y: y + 0.2, w: 5.1, h: 0.36, fontSize: 16, bold: true, charSpacing: -0.3, valign: 'middle' });
    T(s, a[2], { x: x + 0.62, y: y + 0.63, w: 5.05, h: 0.72, fontSize: 12.5, color: G, lineSpacing: 17 });
  });
  hair(s, 2.35 + 3 * 1.5, 0.7, 5.75); hair(s, 2.35 + 3 * 1.5, 6.85, 5.75);
  T(s, 'As quatro primeiras ações não dependem de mais topo de funil. Elas atacam receita que já está dentro do funil.', { x: 0.7, y: 7.02, w: 11.0, h: 0.3, fontSize: 13, bold: true, color: W, valign: 'middle' });
  mark(s);
  s.addNotes('Sequência proposta, não fechada. Saia da reunião com dono e data para cada linha. As duas primeiras semanas são as que mudam o resultado de setembro.');
}

/* ══════════════ 13 · FECHAMENTO (3 decisões) ══════════════ */
{
  const s = S('close');
  label(s, 'O que precisa ser decidido hoje');
  head(s, 'Três decisões.', 44);
  const DEC = [
    ['01', 'Mantemos webinar e Dripify por mais um ciclo?', 'São 88% do volume de entrada e 1 negócio ganho. Ou entram ligação e confirmação na cadência, ou o esforço vai para ABM e parceria.'],
    ['02', 'A meta de setembro se mantém em 44?', 'Manter exige 2,4 reuniões por dia útil no restante do mês. Rever exige recalibrar a meta de clientes junto.'],
    ['03', 'Quem assume o processo pós-proposta?', 'São 42 propostas paradas e 19% de fechamento contra um padrão de 25% a 40%. Sem dono e sem cadência, esse número não sobe.'],
  ];
  DEC.forEach((d, i) => {
    const y = 2.65 + i * 1.35;
    hair(s, y, 0.7, 11.93);
    T(s, d[0], { x: 0.7, y: y + 0.3, w: 0.8, h: 0.3, fontSize: 11, bold: true, color: O, charSpacing: 1.5 });
    T(s, d[1], { x: 1.75, y: y + 0.25, w: 5.0, h: 0.7, fontSize: 21, bold: true, charSpacing: -0.4, lineSpacing: 26 });
    T(s, d[2], { x: 7.1, y: y + 0.26, w: 5.5, h: 0.9, fontSize: 13.5, color: G, lineSpacing: 19 });
  });
  hair(s, 2.65 + 3 * 1.35, 0.7, 11.93);
  T(s, 'O topo de funil já provou que responde. O próximo ganho de receita está entre a proposta e a assinatura.', { x: 0.7, y: 6.85, w: 11.0, h: 0.3, fontSize: 14, bold: true, color: W, valign: 'middle' });
  s.addImage({ data: LOGO, x: 11.93, y: 7.15, w: 0.9, h: 0.2, transparency: 35 });
  s.addNotes('Feche pedindo decisão, não concordância. Cada uma das três tem dono, prazo e impacto direto na meta do semestre.');
}

pres.writeFile({ fileName: 'educaopen-performance-comercial.pptx' }).then(() => console.log('ok'));
