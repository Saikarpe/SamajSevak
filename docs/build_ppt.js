// Builds docs/SamajSevak_Hack2Ignite_AI-04.pptx  (node docs/build_ppt.js)
const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const fa = require('react-icons/fa6');
const path = require('path');

const SHOTS = process.env.SHOTS || path.join(__dirname, 'screenshots');
const OUT = process.env.OUT || path.join(__dirname, 'SamajSevak_Hack2Ignite_AI-04.pptx');

const C = { navy: '0F1B3D', navy2: '1E3A8A', saffron: 'F97316', light: 'F4F6FB', ink: '0F172A', muted: '64748B', line: 'E2E8F0', green: '16A34A', red: 'DC2626', indigo: '4F46E5', white: 'FFFFFF', sky: 'DBEAFE' };
const H = 'Arial', B = 'Calibri';

async function icon(Comp, color) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: '#' + color, size: 256 }));
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}
const shadow = () => ({ type: 'outer', color: '000000', blur: 8, offset: 2, angle: 90, opacity: 0.12 });

(async () => {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
  pres.title = 'SamajSevak — AI Grievance Intelligence';

  const title = (s, t, sub) => {
    s.addText(t, { x: 0.6, y: 0.4, w: 12.1, h: 0.75, fontFace: H, fontSize: 32, bold: true, color: C.ink, margin: 0, isTextBox: true });
    if (sub) s.addText(sub, { x: 0.6, y: 1.12, w: 12.1, h: 0.45, fontFace: B, fontSize: 16, color: C.muted, margin: 0, isTextBox: true });
  };
  const circleIcon = async (s, Comp, x, y, d, bg, fg) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg } });
    s.addImage({ data: await icon(Comp, fg), x: x + d * 0.25, y: y + d * 0.25, w: d * 0.5, h: d * 0.5 });
  };
  const card = (s, x, y, w, h, fill = C.white) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: C.line, width: 0.75 }, shadow: shadow() });
  const pageNo = (s, n) => s.addText(`SamajSevak · AI-04  |  ${n}`, { x: 9.8, y: 7.0, w: 3.0, h: 0.3, fontFace: B, fontSize: 10, color: C.muted, align: 'right', margin: 0, isTextBox: true });

  // 1. Title ---------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.navy };
    s.addShape(pres.shapes.OVAL, { x: 9.2, y: -1.6, w: 6, h: 6, fill: { color: C.saffron, transparency: 15 }, line: { color: C.saffron, transparency: 100 } });
    s.addShape(pres.shapes.OVAL, { x: 10.6, y: 4.4, w: 4, h: 4, fill: { color: C.navy2, transparency: 30 }, line: { color: C.navy2, transparency: 100 } });
    await circleIcon(s, fa.FaShieldHalved, 0.8, 0.9, 1.0, C.white, C.saffron);
    s.addText('Hack2Ignite  ·  Problem Statement AI-04', { x: 0.8, y: 2.25, w: 9, h: 0.4, fontFace: B, fontSize: 16, color: 'FDBA74', bold: true, margin: 0, isTextBox: true });
    s.addText('SamajSevak', { x: 0.8, y: 2.7, w: 10, h: 1.1, fontFace: H, fontSize: 60, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText('AI-powered public grievance analysis & resolution recommendation platform', { x: 0.8, y: 3.85, w: 8.6, h: 1.0, fontFace: B, fontSize: 24, color: C.sky, margin: 0, isTextBox: true });
    s.addText('From raw complaint to prioritised, routed and resolved — with explainable AI.', { x: 0.8, y: 5.0, w: 8.6, h: 0.5, fontFace: B, fontSize: 16, italic: true, color: 'CBD5E1', margin: 0, isTextBox: true });
    s.addText('Team Viper', { x: 0.8, y: 6.3, w: 6, h: 0.45, fontFace: B, fontSize: 18, bold: true, color: C.white, margin: 0, isTextBox: true });
  }

  // 2. Problem -------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.light };
    title(s, 'The problem', 'Citizens complain. Systems file. Problems repeat.');
    const items = [
      [fa.FaInbox, 'Manual triage', 'Thousands of free-text complaints read and sorted by hand — slow and inconsistent.'],
      [fa.FaShuffle, 'Wrong routing', 'Complaints bounce between departments before reaching the right team.'],
      [fa.FaTriangleExclamation, 'No real prioritisation', 'A live wire near a school waits in the same queue as a broken bench.'],
      [fa.FaClone, 'Duplicates', 'The same pothole reported 20 times means 20 tickets and wasted field visits.'],
      [fa.FaMagnifyingGlassChart, 'No root-cause insight', 'Clusters and spikes (e.g. a dengue outbreak) go unnoticed until too late.'],
      [fa.FaCommentSlash, 'Low trust', 'Generic replies, no ETA and no feedback loop — citizens stop reporting.'],
    ];
    for (let i = 0; i < items.length; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 1.9 + row * 2.5;
      card(s, x, y, 3.8, 2.2);
      await circleIcon(s, items[i][0], x + 0.3, y + 0.3, 0.7, 'FEE2E2', C.red);
      s.addText(items[i][1], { x: x + 1.15, y: y + 0.35, w: 2.5, h: 0.6, fontFace: H, fontSize: 17, bold: true, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(items[i][2], { x: x + 0.3, y: y + 1.1, w: 3.25, h: 0.95, fontFace: B, fontSize: 14, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
    }
    pageNo(s, 2);
  }

  // 3. Solution ------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.white };
    title(s, 'Our solution: SamajSevak', 'An AI co-pilot for grievance cells — for citizens, officers and administrators.');
    const pillars = [
      [fa.FaBrain, 'Understand', C.indigo, 'EEF2FF', 'Classifies category & department, extracts ward, landmark, duration, risk words and vulnerable groups, reads sentiment.'],
      [fa.FaGaugeHigh, 'Prioritise', C.saffron, 'FFF7ED', 'Explainable 0–100 urgency score, duplicate merging and automatic escalation of critical cases.'],
      [fa.FaLightbulb, 'Resolve', C.green, 'DCFCE7', 'Step-by-step action plan from SOPs + what fixed similar past cases, ETA and an AI-drafted citizen reply.'],
      [fa.FaChartLine, 'Learn & Prevent', C.red, 'FEE2E2', 'Hotspot map, emerging-issue alerts, SLA monitoring and department performance from citizen feedback.'],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.08;
      card(s, x, 1.95, 2.85, 4.2);
      await circleIcon(s, pillars[i][0], x + 0.3, 2.25, 0.9, pillars[i][3], pillars[i][2]);
      s.addText(pillars[i][1], { x: x + 0.3, y: 3.35, w: 2.3, h: 0.5, fontFace: H, fontSize: 20, bold: true, color: C.ink, margin: 0, isTextBox: true });
      s.addText(pillars[i][4], { x: x + 0.3, y: 3.9, w: 2.3, h: 2.1, fontFace: B, fontSize: 14, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
    }
    s.addText('Works fully offline with local ML; plugs into Gemini / OpenAI when available.', { x: 0.6, y: 6.4, w: 12, h: 0.4, fontFace: B, fontSize: 15, italic: true, color: C.navy2, margin: 0, isTextBox: true });
    pageNo(s, 3);
  }

  // 4. Product walkthrough (citizen) ---------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.light };
    title(s, 'Citizen portal: live AI while you type', null);
    s.addImage({ path: path.join(SHOTS, 'submit.png'), x: 0.6, y: 1.35, w: 8.0, h: 5.0, shadow: shadow() });
    const pts = [
      ['Free text or voice', 'English, Hindi or Hinglish — no forms full of dropdowns.'],
      ['Instant triage preview', 'Department, priority, ETA and SLA shown before submitting.'],
      ['Transparent', '"Why this priority?" breaks the score into factors.'],
      ['Track & rate', 'Tracking ID, status timeline and 1–5 star feedback.'],
    ];
    pts.forEach((p, i) => {
      const y = 1.45 + i * 1.25;
      s.addShape(pres.shapes.OVAL, { x: 9.0, y: y + 0.05, w: 0.42, h: 0.42, fill: { color: C.saffron }, line: { color: C.saffron } });
      s.addText(String(i + 1), { x: 9.0, y: y + 0.05, w: 0.42, h: 0.42, fontFace: H, fontSize: 14, bold: true, color: C.white, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
      s.addText(p[0], { x: 9.6, y, w: 3.2, h: 0.45, fontFace: H, fontSize: 16, bold: true, color: C.ink, margin: 0, isTextBox: true });
      s.addText(p[1], { x: 9.6, y: y + 0.45, w: 3.2, h: 0.7, fontFace: B, fontSize: 13, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
    });
    pageNo(s, 4);
  }

  // 5. Officer console ------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.light };
    title(s, 'Officer console: decide faster, act smarter', null);
    s.addImage({ path: path.join(SHOTS, 'dashboard.png'), x: 0.6, y: 1.35, w: 6.0, h: 3.75, shadow: shadow() });
    s.addImage({ path: path.join(SHOTS, 'detail.png'), x: 6.75, y: 1.35, w: 6.0, h: 3.75, shadow: shadow() });
    s.addText('Command Center — KPIs, 30-day inflow, AI alerts and the AI-ranked queue', { x: 0.6, y: 5.2, w: 6.0, h: 0.5, fontFace: B, fontSize: 13, color: C.muted, margin: 0, isTextBox: true });
    s.addText('Case view — AI triage, explainable score, duplicates, action plan, AI reply, audit trail', { x: 6.75, y: 5.2, w: 6.0, h: 0.5, fontFace: B, fontSize: 13, color: C.muted, margin: 0, isTextBox: true });
    const chips = ['Auto-routing', 'Duplicate merge', 'SLA breach tracking', 'One-click status updates', 'AI-drafted replies', 'Full audit trail'];
    chips.forEach((c, i) => {
      const x = 0.6 + i * 2.05;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 6.05, w: 1.9, h: 0.5, rectRadius: 0.25, fill: { color: 'E0E7FF' }, line: { color: 'E0E7FF' } });
      s.addText(c, { x, y: 6.05, w: 1.9, h: 0.5, fontFace: B, fontSize: 12, bold: true, color: '3730A3', align: 'center', valign: 'middle', margin: 0, isTextBox: true });
    });
    pageNo(s, 5);
  }

  // 6. AI pipeline -----------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.white };
    title(s, 'The AI pipeline', 'Every complaint passes through 8 stages in ~4 ms on a laptop CPU.');
    const st = [
      [fa.FaBroom, 'Clean', 'Strip greetings & boilerplate; Hinglish-aware'],
      [fa.FaTags, 'Classify & route', 'TF-IDF word+char n-grams → Logistic Regression, 11 categories'],
      [fa.FaLocationDot, 'Extract entities', 'Ward, landmark, duration, risk words, vulnerable groups'],
      [fa.FaFaceFrown, 'Sentiment', 'Lexicon + intensifiers + !/CAPS → distress score'],
      [fa.FaClone, 'Find duplicates', 'Cosine similarity, category-aware re-rank, same ward'],
      [fa.FaGaugeHigh, 'Score priority', 'Explainable 0–100 from 7 weighted factors'],
      [fa.FaListCheck, 'Recommend', 'SOP playbook + proven past fixes + median ETA'],
      [fa.FaTowerBroadcast, 'Detect spikes', 'Ward×category vs 3-week baseline → alerts'],
    ];
    for (let i = 0; i < 8; i++) {
      const col = i % 4, row = Math.floor(i / 4);
      const x = 0.6 + col * 3.1, y = 1.95 + row * 2.45;
      card(s, x, y, 2.8, 2.1, i < 4 ? 'F8FAFF' : 'FFFBF5');
      await circleIcon(s, st[i][0], x + 0.25, y + 0.25, 0.62, i < 4 ? 'E0E7FF' : 'FFEDD5', i < 4 ? C.indigo : C.saffron);
      s.addText(`${i + 1}. ${st[i][1]}`, { x: x + 1.0, y: y + 0.28, w: 1.7, h: 0.56, fontFace: H, fontSize: 14, bold: true, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(st[i][2], { x: x + 0.25, y: y + 1.0, w: 2.35, h: 0.95, fontFace: B, fontSize: 13, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
      if (col < 3) s.addText('›', { x: x + 2.8, y: y + 0.75, w: 0.3, h: 0.5, fontFace: H, fontSize: 24, color: 'CBD5E1', align: 'center', margin: 0, isTextBox: true });
    }
    s.addText('+ optional GenAI (Gemini / OpenAI) drafts empathetic replies grounded in this analysis', { x: 0.6, y: 6.8, w: 9, h: 0.35, fontFace: B, fontSize: 13, italic: true, color: C.navy2, margin: 0, isTextBox: true });
    pageNo(s, 6);
  }

  // 7. Explainable priority -------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.light };
    title(s, 'Explainable priority, not a black box', 'Officers see exactly why a case is urgent — and can defend the decision.');
    card(s, 0.6, 1.9, 6.1, 4.9);
    s.addText('Example complaint', { x: 0.9, y: 2.1, w: 5.5, h: 0.4, fontFace: H, fontSize: 14, bold: true, color: C.muted, margin: 0, isTextBox: true });
    s.addText('“Live electric wire has fallen near the primary school in Kothrud since yesterday. Children walk here daily, extremely dangerous!”', { x: 0.9, y: 2.5, w: 5.5, h: 1.1, fontFace: B, fontSize: 15, italic: true, color: C.ink, margin: 0, valign: 'top', isTextBox: true });
    const f = [['Category severity (Electricity)', 22.5], ['Risk keywords: live electric wire, dangerous', 26], ['Vulnerable groups: children, school', 12], ['Issue persisting ~1 day', 3.2], ['Similar open complaint nearby', 4], ['Citizen distress', 1.2]];
    f.forEach((r, i) => {
      const y = 3.8 + i * 0.47;
      s.addText(r[0], { x: 0.9, y, w: 3.4, h: 0.4, fontFace: B, fontSize: 13, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.4, y: y + 0.13, w: 1.5, h: 0.14, rectRadius: 0.07, fill: { color: 'E2E8F0' }, line: { color: 'E2E8F0' } });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.4, y: y + 0.13, w: Math.max(0.1, 1.5 * r[1] / 30), h: 0.14, rectRadius: 0.07, fill: { color: C.red }, line: { color: C.red } });
      s.addText('+' + r[1], { x: 5.95, y, w: 0.6, h: 0.4, fontFace: H, fontSize: 13, bold: true, color: C.ink, align: 'right', margin: 0, valign: 'middle', isTextBox: true });
    });
    // score callout
    card(s, 7.0, 1.9, 5.7, 2.3, C.navy);
    s.addText('69', { x: 7.3, y: 2.05, w: 2.2, h: 1.4, fontFace: H, fontSize: 72, bold: true, color: 'FCA5A5', margin: 0, isTextBox: true });
    s.addText('/100  CRITICAL', { x: 7.3, y: 3.4, w: 3, h: 0.5, fontFace: H, fontSize: 18, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText('Auto-escalated to Electricity Board within 2 h · ETA 12 h · SLA 24 h', { x: 9.6, y: 2.3, w: 2.9, h: 1.6, fontFace: B, fontSize: 15, color: C.sky, margin: 0, valign: 'middle', isTextBox: true });
    card(s, 7.0, 4.45, 5.7, 2.35);
    s.addText([
      { text: 'Critical ≥ 60   ·   High ≥ 42   ·   Medium ≥ 25   ·   Low', options: { bold: true, color: C.ink, breakLine: true } },
      { text: 'Factors: category severity, risk keywords, vulnerable groups, sentiment distress, duration, cluster size, repeat complaint.', options: { color: C.muted, breakLine: true } },
      { text: 'Low classifier confidence (< 40%) sends the case to human triage — AI assists, officers decide.', options: { color: C.navy2 } },
    ], { x: 7.3, y: 4.65, w: 5.1, h: 2.0, fontFace: B, fontSize: 14, margin: 0, valign: 'top', paraSpaceAfter: 8, isTextBox: true });
    pageNo(s, 7);
  }

  // 8. Architecture ----------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.white };
    title(s, 'System architecture', null);
    const box = (x, y, w, h, head, body, fill, headColor) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: fill }, line: { color: C.line, width: 0.75 } });
      s.addText(head, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.4, fontFace: H, fontSize: 14, bold: true, color: headColor, margin: 0, isTextBox: true });
      s.addText(body, { x: x + 0.15, y: y + 0.5, w: w - 0.3, h: h - 0.6, fontFace: B, fontSize: 12, color: C.ink, margin: 0, valign: 'top', isTextBox: true });
    };
    const arrow = (x1, y1, x2, y2, dash) => s.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color: '94A3B8', width: 1.5, endArrowType: 'triangle', dashType: dash ? 'dash' : 'solid' } });
    box(0.6, 1.5, 2.4, 2.1, 'Channels', 'Web portal\nMobile app\nWhatsApp / Call centre\nVoice input', 'FFF7ED', 'C2410C');
    box(0.6, 4.1, 2.4, 2.1, 'Users', 'Citizens\nField officers\nDepartment heads\nCommissioner', 'FFF7ED', 'C2410C');
    box(3.6, 1.5, 2.6, 4.7, 'React UI (Vite)', 'Citizen portal\nTrack & feedback\nCommand Center\nPriority queue\nCase workspace\nHotspot map (Leaflet)\nAnalytics (Recharts)', 'EEF2FF', '3730A3');
    box(6.8, 1.5, 2.6, 4.7, 'FastAPI backend', 'REST API + OpenAPI docs\nGrievance service\nWorkflow & SLA engine\nAnalytics & alerts\nAudit trail\nServes built UI (Docker)', 'EFF6FF', C.navy2);
    box(10.0, 1.5, 2.75, 2.75, 'AI Engine (scikit-learn)', 'Classifier · Sentiment\nEntity extraction\nSimilarity index\nPriority scorer\nRecommender\nSpike detector', 'F0FDF4', '166534');
    box(10.0, 4.5, 1.3, 1.7, 'Data', 'SQLite → PostgreSQL', 'F8FAFC', C.ink);
    box(11.45, 4.5, 1.3, 1.7, 'SOP KB', 'Playbooks, SLAs, past fixes', 'F8FAFC', C.ink);
    arrow(3.0, 2.55, 3.6, 2.55); arrow(3.0, 5.15, 3.6, 5.15);
    arrow(6.2, 3.85, 6.8, 3.85); arrow(9.4, 2.9, 10.0, 2.9); arrow(9.4, 5.35, 10.0, 5.35);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.8, y: 6.45, w: 5.95, h: 0.6, rectRadius: 0.1, fill: { color: 'FAF5FF' }, line: { color: 'D8B4FE', dashType: 'dash' } });
    s.addText('Optional: Gemini 2.0 Flash / GPT-4o-mini — grounded reply drafting, template fallback offline', { x: 6.95, y: 6.45, w: 5.7, h: 0.6, fontFace: B, fontSize: 12, color: '6B21A8', valign: 'middle', margin: 0, isTextBox: true });
    arrow(8.1, 6.2, 8.1, 6.45, true);
    s.addText('Flow: complaint → analyse (~4 ms) → auto-route & escalate → officer acts on recommendation → citizen feedback → analytics & alerts', { x: 0.6, y: 6.45, w: 5.9, h: 0.7, fontFace: B, fontSize: 12, italic: true, color: C.muted, margin: 0, valign: 'middle', isTextBox: true });
  }

  // 9. Tech stack ------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.light };
    title(s, 'Tech stack', 'Lightweight, open-source and deployable on a single government server.');
    const groups = [
      [fa.FaReact, 'Frontend', C.indigo, 'EEF2FF', ['React 19 + Vite', 'React Router', 'Recharts', 'Leaflet + OpenStreetMap', 'Web Speech API (voice)']],
      [fa.FaPython, 'Backend', C.navy2, 'DBEAFE', ['Python 3.11', 'FastAPI + Uvicorn', 'Pydantic validation', 'SQLite (PostgreSQL-ready)', 'pytest']],
      [fa.FaBrain, 'AI / ML', C.green, 'DCFCE7', ['scikit-learn: TF-IDF, LogReg', 'Cosine similarity retrieval', 'Rule-augmented NLP (NER, sentiment)', 'NumPy · joblib', 'Gemini / OpenAI (optional)']],
      [fa.FaDocker, 'Deploy', C.saffron, 'FFEDD5', ['Docker single container', 'Render / Railway / any VM', 'GitHub for version control', 'OpenAPI docs at /docs', 'Env-based API keys']],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.08;
      card(s, x, 1.9, 2.85, 4.8);
      await circleIcon(s, groups[i][0], x + 0.3, 2.15, 0.85, groups[i][3], groups[i][2]);
      s.addText(groups[i][1], { x: x + 1.3, y: 2.15, w: 1.4, h: 0.85, fontFace: H, fontSize: 19, bold: true, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(groups[i][4].map((t, j, a) => ({ text: t, options: { bullet: true, breakLine: j < a.length - 1 } })),
        { x: x + 0.25, y: 3.25, w: 2.45, h: 3.2, fontFace: B, fontSize: 14, color: C.ink, paraSpaceAfter: 10, valign: 'top', margin: 0, isTextBox: true });
    }
    pageNo(s, 9);
  }

  // 10. Insights --------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.white };
    title(s, 'From complaints to prevention', 'Hotspots, emerging-issue alerts and department accountability.');
    s.addImage({ path: path.join(SHOTS, 'insights.png'), x: 0.6, y: 1.8, w: 7.2, h: 4.5, shadow: shadow() });
    card(s, 8.15, 1.8, 4.6, 2.35, 'FEF2F2');
    s.addText([
      { text: 'Emerging hotspot detected', options: { bold: true, color: C.red, fontSize: 16, breakLine: true } },
      { text: '12 public-health complaints in Hadapsar this week — far above its 3-week baseline.', options: { color: C.ink, fontSize: 14, breakLine: true } },
      { text: 'Recommendation: ward-level fever survey & fogging drive instead of case-by-case fixes.', options: { color: C.muted, fontSize: 13 } },
    ], { x: 8.4, y: 1.95, w: 4.15, h: 2.1, fontFace: B, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
    const b = [['Ward risk ranking', 'Open & urgent load per ward, top issue'], ['SLA compliance by department', 'Lowest performers surface first'], ['Sentiment tracking', 'Distress feeds back into priority']];
    b.forEach((r, i) => {
      const y = 4.4 + i * 0.65;
      s.addText([{ text: r[0] + '  ', options: { bold: true, color: C.ink } }, { text: r[1], options: { color: C.muted } }], { x: 8.15, y, w: 4.6, h: 0.55, fontFace: B, fontSize: 13, margin: 0, valign: 'middle', isTextBox: true });
    });
    pageNo(s, 10);
  }

  // 11. Results ----------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.navy };
    s.addText('Prototype results', { x: 0.6, y: 0.4, w: 12, h: 0.75, fontFace: H, fontSize: 32, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText('Measured on the working prototype in the GitHub repo', { x: 0.6, y: 1.12, w: 12, h: 0.45, fontFace: B, fontSize: 16, color: 'CBD5E1', margin: 0, isTextBox: true });
    const st = [['95.5%', 'category accuracy on hand-written unseen complaints (21/22)'], ['~4 ms', 'full AI analysis per complaint on CPU'], ['11', 'categories auto-routed to departments with SLAs'], ['8', 'AI stages: classify → recommend → detect spikes']];
    st.forEach((r, i) => {
      const x = 0.6 + i * 3.1;
      s.addText(r[0], { x, y: 2.1, w: 2.9, h: 1.2, fontFace: H, fontSize: 54, bold: true, color: i % 2 ? 'FDBA74' : C.white, margin: 0, isTextBox: true });
      s.addText(r[1], { x, y: 3.3, w: 2.7, h: 0.9, fontFace: B, fontSize: 15, color: 'CBD5E1', margin: 0, valign: 'top', isTextBox: true });
    });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.7, w: 12.1, h: 1.75, rectRadius: 0.12, fill: { color: '1E293B' }, line: { color: '334155' } });
    s.addText([
      { text: 'What the demo shows', options: { bold: true, color: C.white, fontSize: 17, breakLine: true } },
      { text: '450+ realistic seeded grievances across 12 Pune wards · critical cases escalated automatically · duplicate detection on resubmission · hotspot spike alert in Hadapsar · end-to-end workflow from submission to citizen rating.', options: { color: 'CBD5E1', fontSize: 14, breakLine: true } },
      { text: 'Honest note: training data is synthetic; production retrains on real, officer-verified complaints.', options: { color: 'FDBA74', fontSize: 13, italic: true } },
    ], { x: 0.9, y: 4.85, w: 11.5, h: 1.8, fontFace: B, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
  }

  // 12. Impact & roadmap -------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.light };
    title(s, 'Impact & roadmap', null);
    card(s, 0.6, 1.4, 5.9, 5.35);
    await circleIcon(s, fa.FaHandHoldingHeart, 0.9, 1.65, 0.7, 'DCFCE7', C.green);
    s.addText('Impact', { x: 1.75, y: 1.65, w: 4, h: 0.7, fontFace: H, fontSize: 22, bold: true, color: C.ink, valign: 'middle', margin: 0, isTextBox: true });
    const imp = ['Life-safety issues reach the right team first', 'Fewer duplicate field visits and misrouted tickets', 'Officers get a proven action plan, not a blank page', 'Administrators spot outbreaks & systemic failures early', 'Citizens get transparent ETAs and personalised replies', 'Data-driven department accountability via SLA & ratings'];
    s.addText(imp.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < imp.length - 1 } })), { x: 0.95, y: 2.6, w: 5.3, h: 3.9, fontFace: B, fontSize: 15, color: C.ink, paraSpaceAfter: 10, valign: 'top', margin: 0, isTextBox: true });
    const road = [
      ['Next', 'Multilingual transformer (IndicBERT / MuRIL) for Marathi, Hindi & regional languages'],
      ['Next', 'Photo evidence: detect potholes, garbage, waterlogging from images'],
      ['Scale', 'WhatsApp chatbot & IVR intake; CPGRAMS / municipal ERP integration'],
      ['Scale', 'Active learning from officer corrections; PostgreSQL + PostGIS'],
      ['Future', 'Predictive maintenance: forecast issues before complaints arrive'],
    ];
    road.forEach((r, i) => {
      const y = 1.4 + i * 1.08;
      card(s, 6.8, y, 5.9, 0.9);
      const col = r[0] === 'Next' ? C.indigo : r[0] === 'Scale' ? C.saffron : C.green;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.0, y: y + 0.25, w: 0.9, h: 0.4, rectRadius: 0.2, fill: { color: col }, line: { color: col } });
      s.addText(r[0], { x: 7.0, y: y + 0.25, w: 0.9, h: 0.4, fontFace: H, fontSize: 11, bold: true, color: C.white, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
      s.addText(r[1], { x: 8.05, y: y + 0.05, w: 4.5, h: 0.8, fontFace: B, fontSize: 13, color: C.ink, valign: 'middle', margin: 0, isTextBox: true });
    });
    pageNo(s, 12);
  }

  // 13. Thank you ---------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.navy };
    s.addShape(pres.shapes.OVAL, { x: -1.5, y: 4.2, w: 5, h: 5, fill: { color: C.saffron, transparency: 15 }, line: { color: C.saffron, transparency: 100 } });
    await circleIcon(s, fa.FaShieldHalved, 6.17, 1.1, 1.0, C.white, C.saffron);
    s.addText('Thank you', { x: 0.6, y: 2.3, w: 12.1, h: 1.1, fontFace: H, fontSize: 54, bold: true, color: C.white, align: 'center', margin: 0, isTextBox: true });
    s.addText('SamajSevak — every voice heard, every grievance resolved smarter.', { x: 0.6, y: 3.4, w: 12.1, h: 0.6, fontFace: B, fontSize: 20, color: C.sky, align: 'center', margin: 0, isTextBox: true });
    s.addText([
      { text: 'GitHub: ', options: { bold: true, color: 'FDBA74' } }, { text: 'github.com/<your-username>/samajsevak', options: { color: C.white, breakLine: true } },
      { text: 'Run: ', options: { bold: true, color: 'FDBA74' } }, { text: 'docker build -t samajsevak . && docker run -p 8000:8000 samajsevak', options: { color: C.white } },
    ], { x: 2.2, y: 4.5, w: 8.9, h: 1.0, fontFace: B, fontSize: 16, align: 'center', margin: 0, paraSpaceAfter: 6, isTextBox: true });
    s.addText('Team Viper  ·  Hack2Ignite  ·  AI-04', { x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontFace: B, fontSize: 14, color: '94A3B8', align: 'center', margin: 0, isTextBox: true });
  }

  await pres.writeFile({ fileName: OUT });
  console.log('wrote', OUT);
})();
