// Slide executivo — Educa Open · Performance Comercial (Leaderei)
// Sistema visual: leaderei-brand / references/deck-system.md
const fs = require('fs'), pptxgen = require('pptxgenjs');
const pres = new pptxgen(); pres.layout = 'LAYOUT_WIDE';
pres.author = 'Leaderei'; pres.company = 'Leaderei';
pres.title = 'Educa Open — Performance Comercial (jun–set/2026)';

const O = 'DF4E01', W = 'FFFFFF', G = 'A0A0A0', M = '6E6E76', HAIR = '2B2B2B', F = 'Manrope';
const im = p => 'image/' + (p.endsWith('.png') ? 'png' : 'jpeg') + ';base64,' + fs.readFileSync('./assets/' + p).toString('base64');
const BG = { content: im('bg_content.jpg') };
const LOGO = im('logo_white.png');

const S = k => { const s = pres.addSlide(); s.addImage({ data: BG[k || 'content'], x: 0, y: 0, w: 13.333, h: 7.5 }); return s; };
const mark = s => s.addImage({ data: LOGO, x: 11.93, y: 7.05, w: 0.9, h: 0.2, transparency: 35 });
const hair = (s, y, x, w, c) => s.addShape(pres.ShapeType.line, { x, y, w, h: 0, line: { color: c || HAIR, width: 0.75 } });
const vhair = (s, x, y, h, c) => s.addShape(pres.ShapeType.line, { x, y, w: 0, h, line: { color: c || HAIR, width: 0.75 } });
const dot = (s, x, y, d, c) => s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: c || O }, line: { color: c || O, width: 0 } });
const T = (s, t, o) => s.addText(t, Object.assign({ fontFace: F, margin: 0, color: W }, o));
const label = (s, t, x, y, c) => {
  dot(s, x, y + 0.045, 0.075, c);
  T(s, t.toUpperCase(), { x: x + 0.2, y: y - 0.06, w: 10, h: 0.3, fontSize: 10, bold: true, color: c || O, charSpacing: 3.2, valign: 'middle' });
};

const s = S('content');

/* ─────────── CABEÇALHO ─────────── */
label(s, 'Educa Open · Performance comercial', 0.72, 0.62);
T(s, 'JUN–SET/2026   ·   FONTE: PIPEDRIVE, ATÉ 04/09', { x: 7.6, y: 0.5, w: 5.03, h: 0.3, fontSize: 9.5, bold: true, color: M, charSpacing: 2, align: 'right', valign: 'middle' });
T(s, 'Agosto bateu a meta. Setembro é o teste.', { x: 0.7, y: 1.0, w: 12, h: 0.62, fontSize: 34, bold: true, charSpacing: -0.7, valign: 'middle' });

/* ─────────── FAIXA A · KPIs ─────────── */
hair(s, 1.85, 0.7, 11.93);
const KPI = [
  ['36', W, 'Agendamentos em agosto', '129% da meta (28)  ·  +64% vs. julho'],
  ['12', W, 'Negócios ganhos jun–set', 'R$ 498,5 mil em contratos fechados'],
  ['9,6%', W, 'Diag. agendado → ganho', 'plano de metas assume 18%'],
  ['44', O, 'Meta de setembro', 'maior do semestre  ·  ritmo: 48%'],
];
KPI.forEach((k, i) => {
  const x = 0.7 + i * 3.0;
  if (i > 0) vhair(s, x - 0.28, 2.02, 0.98);
  T(s, k[0], { x, y: 2.0, w: 2.7, h: 0.62, fontSize: 42, bold: true, color: k[1], charSpacing: -1.4, valign: 'middle' });
  T(s, k[2].toUpperCase(), { x, y: 2.66, w: 2.7, h: 0.24, fontSize: 9.5, bold: true, color: G, charSpacing: 1.6, valign: 'middle' });
  T(s, k[3], { x, y: 2.9, w: 2.75, h: 0.24, fontSize: 11, color: M, valign: 'middle' });
});
hair(s, 3.22, 0.7, 11.93);

/* ─────────── FAIXA B · esquerda: topo de funil x meta ─────────── */
T(s, 'TOPO DE FUNIL  ·  REALIZADO (BARRA) X META (TRAÇO)', { x: 0.7, y: 3.45, w: 5.6, h: 0.24, fontSize: 10, bold: true, color: O, charSpacing: 2.2, valign: 'middle' });

const BASE = 5.28, HMAX = 1.40, VMAX = 44, K = HMAX / VMAX;
const MESES = [
  ['jun', 4, null, ''], ['jul', 22, 39, '56% da meta'], ['ago', 36, 28, '129% da meta'], ['set*', 4, 44, 'ritmo: 48%'],
];
MESES.forEach((m, i) => {
  const gx = 0.72 + i * 1.4, bw = 0.66, bx = gx + (1.26 - bw) / 2;
  const bh = m[1] * K;
  s.addShape(pres.ShapeType.rect, { x: bx, y: BASE - bh, w: bw, h: bh, fill: { color: i === 2 ? 'E9E9E9' : '5A5A5A' }, line: { width: 0 } });
  T(s, String(m[1]), { x: bx - 0.25, y: BASE - bh - 0.28, w: bw + 0.5, h: 0.24, fontSize: 12.5, bold: true, color: i === 2 ? W : G, align: 'center', valign: 'middle' });
  if (m[2] !== null) {
    const my = BASE - m[2] * K;
    s.addShape(pres.ShapeType.line, { x: bx - 0.13, y: my, w: bw + 0.26, h: 0, line: { color: O, width: 1.5 } });
    T(s, String(m[2]), { x: bx + bw + 0.17, y: my - 0.12, w: 0.5, h: 0.24, fontSize: 10, bold: true, color: O, valign: 'middle' });
  }
  T(s, m[0], { x: bx - 0.3, y: BASE + 0.06, w: bw + 0.6, h: 0.22, fontSize: 11.5, color: G, align: 'center', valign: 'middle' });
  if (m[3]) T(s, m[3], { x: bx - 0.45, y: BASE + 0.28, w: bw + 0.9, h: 0.22, fontSize: 9.5, bold: true, color: i === 2 ? O : (i === 3 ? W : M), align: 'center', valign: 'middle' });
});
hair(s, BASE, 0.7, 5.6, '3A3A3A');

/* ─────────── FAIXA B · direita: canais ─────────── */
vhair(s, 6.62, 3.42, 2.35);
T(s, 'DE ONDE VEM O RESULTADO  ·  ACUMULADO DO PROJETO', { x: 6.98, y: 3.45, w: 5.65, h: 0.24, fontSize: 10, bold: true, color: O, charSpacing: 2.2, valign: 'middle' });

const COLS = [[6.98, 2.05, 'left'], [9.05, 1.0, 'right'], [10.10, 1.15, 'right'], [11.33, 0.7, 'right'], [12.06, 0.57, 'right']];
const HEAD = ['CANAL', 'ENTRADAS', 'AGENDADAS', 'GANHOS', 'TAXA'];
HEAD.forEach((h, i) => T(s, h, { x: COLS[i][0], y: 3.80, w: COLS[i][1], h: 0.22, fontSize: 8.5, bold: true, color: M, charSpacing: 1.2, align: COLS[i][2], valign: 'middle' }));

const CANAIS = [
  ['Parcerias / Indicações', '30', '25', '7', '23%', true],
  ['Eventos', '38', '25', '1', '3%', false],
  ['ABM*', '24', '2', '2', '8%', false],
  ['Dripify', '175', '7', '0', '0%', false],
  ['Webinar', '510', '15', '1', '0,2%', false],
];
CANAIS.forEach((c, i) => {
  const y = 4.08 + i * 0.30;
  hair(s, y - 0.04, 6.98, 5.65);
  const col = c[5] ? W : G;
  for (let j = 0; j < 5; j++) {
    T(s, c[j], {
      x: COLS[j][0], y: y + 0.01, w: COLS[j][1], h: 0.26,
      fontSize: 12, bold: c[5], color: j === 4 && c[5] ? O : col,
      align: COLS[j][2], valign: 'middle',
    });
  }
});
hair(s, 4.08 + 5 * 0.30 - 0.04, 6.98, 5.65);
T(s, '4% das entradas geram 58% dos ganhos.', { x: 6.98, y: 5.62, w: 5.65, h: 0.22, fontSize: 10.5, bold: true, color: W, valign: 'middle' });

hair(s, 5.86, 0.7, 11.93);

/* ─────────── FAIXA C · leitura ─────────── */
const LEIT = [
  ['Resultado concentrado em indicação', 'Webinar e Dripify são 88% das entradas e entregaram 1 ganho no total.'],
  ['O funil trava na proposta', '62 propostas viraram 20 contratos enviados — 32%. Maior perda depois do topo.'],
  ['Setembro pede 2,1 reuniões por dia útil', 'Em 4 dias úteis: 4 agendadas (1,0/dia). No ritmo atual, fecha em ~21 de 44.'],
];
LEIT.forEach((l, i) => {
  const x = 0.7 + i * 4.07;
  dot(s, x, 6.10, 0.085);
  T(s, l[0], { x: x + 0.26, y: 5.99, w: 3.7, h: 0.28, fontSize: 14, bold: true, charSpacing: -0.3, valign: 'middle' });
  T(s, l[1], { x: x + 0.26, y: 6.32, w: 3.65, h: 0.5, fontSize: 11, color: G, lineSpacing: 15 });
});

/* ─────────── RODAPÉ ─────────── */
T(s, 'Fontes: funil da Educa Open no Pipedrive e planilha de metas do 2º semestre.  *Setembro parcial: 4 de 21 dias úteis.  *Entradas de ABM inconsistentes na origem.', { x: 0.7, y: 6.98, w: 11.1, h: 0.2, fontSize: 9, color: M, valign: 'middle' });
T(s, 'Topo de funil = reuniões de diagnóstico criadas no mês; canais = negócios por etapa, acumulado. Meta implícita de 18% = 42,55 clientes ÷ 234 agendamentos planejados (jul–dez).', { x: 0.7, y: 7.16, w: 11.1, h: 0.2, fontSize: 9, color: M, valign: 'middle' });
mark(s);

s.addNotes([
  'Abertura: agosto foi o melhor mês do projeto — 36 diagnósticos (129% da meta) e 5 negócios ganhos, R$ 249 mil. O topo saiu de 4 em junho para 36 em agosto.',
  'Ponto 1 — concentração: parcerias e indicações são 30 entradas (4% do total) e 7 dos 12 ganhos. Webinar (510) e Dripify (175) entregaram 1 ganho somado. Decisão a tomar: manter o investimento nos canais frios ou realocar esforço para indicação enquanto os frios não maturam.',
  'Ponto 2 — fundo de funil: 62 propostas → 20 contratos enviados (32%). Antes disso o funil está saudável (91% e 90% entre diagnóstico e validação). O gargalo é pós-proposta: follow-up estruturado, próximos passos e gatilho de decisão.',
  'Ponto 3 — setembro: meta de 44 é a maior do semestre e exige 2,1 reuniões por dia útil. O ritmo dos 4 primeiros dias é metade disso.',
  'Alerta de conversão: 12 ganhos em 125 diagnósticos agendados = 9,6%. O plano de metas assume ~18% (42,55 clientes com 234 agendamentos). Se a conversão real ficar em 9,6%, seriam necessários ~443 agendamentos para a meta de clientes. Ressalva: há 103 negócios em validação externa e 62 em proposta que ainda podem fechar e elevar essa taxa.',
].join('\n\n'));

pres.writeFile({ fileName: 'educaopen-performance-comercial.pptx' }).then(() => console.log('ok'));
