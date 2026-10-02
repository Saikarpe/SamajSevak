// Builds docs/SamajSevak_Hack2Ignite_AI-04.pptx  (node docs/build_ppt.js)
const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const fa = require('react-icons/fa6');
const path = require('path');

const SHOTS = process.env.SHOTS || path.join(__dirname, 'screenshots');
const OUT = process.env.OUT || path.join(__dirname, 'SamajSevak_Hack2Ignite_AI-04.pptx');

// same palette as the app: one blue, neutral greys, colour only for meaning
const C = { navy: '0F1F3D', blue: '2563EB', blue2: '1D4ED8', soft: 'E8F0FE', light: 'F2F5FB', ink: '18212D', muted: '627084', line: 'E3E7ED', green: '16A34A', red: 'DC2626', amber: 'D97706', orange: 'EA580C', white: 'FFFFFF', sky: 'BFDBFE' };
const H = 'Arial', B = 'Calibri';
const STAGE = [['Complaint', '627084', 'Concerned department'], ['Warning', 'D97706', 'Still the concerned department'], ['Strike 1', 'EA580C', 'Higher authority of the department'], ['Strike 2', 'DC2626', 'Deputy Collector'], ['Strike 3', '991B1B', 'Final escalation body: IAS officers + opposition party leaders']];

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
  let page = 1;

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
  const slide = (bg = C.light, numbered = true) => {
    const s = pres.addSlide(); s.background = { color: bg }; page += 1;
    if (numbered) s.addText(`SamajSevak · AI-04  |  ${page}`, { x: 9.8, y: 7.0, w: 3.0, h: 0.3, fontFace: B, fontSize: 10, color: C.muted, align: 'right', margin: 0, isTextBox: true });
    return s;
  };
  const shot = (s, name, x, y, w) => s.addImage({ path: path.join(SHOTS, name + '.png'), x, y, w, h: w / 1.6, shadow: shadow() });
  // numbered points beside a screenshot
  const points = (s, pts, x, y0, step, w) => pts.forEach((p, i) => {
    const y = y0 + i * step;
    s.addShape(pres.shapes.OVAL, { x, y: y + 0.05, w: 0.42, h: 0.42, fill: { color: C.blue }, line: { color: C.blue } });
    s.addText(String(i + 1), { x, y: y + 0.05, w: 0.42, h: 0.42, fontFace: H, fontSize: 14, bold: true, color: C.white, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
    s.addText(p[0], { x: x + 0.6, y, w, h: 0.42, fontFace: H, fontSize: 15, bold: true, color: C.ink, margin: 0, isTextBox: true });
    s.addText(p[1], { x: x + 0.6, y: y + 0.42, w, h: step - 0.5, fontFace: B, fontSize: 12.5, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
  });

  // 1. Title ---------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.navy };
    s.addShape(pres.shapes.OVAL, { x: 9.2, y: -1.6, w: 6, h: 6, fill: { color: C.blue, transparency: 20 }, line: { color: C.blue, transparency: 100 } });
    s.addShape(pres.shapes.OVAL, { x: 10.6, y: 4.4, w: 4, h: 4, fill: { color: C.blue2, transparency: 45 }, line: { color: C.blue2, transparency: 100 } });
    await circleIcon(s, fa.FaShieldHalved, 0.8, 0.9, 1.0, C.white, C.blue);
    s.addText('Hack2Ignite  ·  Problem Statement AI-04', { x: 0.8, y: 2.25, w: 9, h: 0.4, fontFace: B, fontSize: 16, color: C.sky, bold: true, margin: 0, isTextBox: true });
    s.addText('SamajSevak', { x: 0.8, y: 2.7, w: 10, h: 1.1, fontFace: H, fontSize: 60, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText('AI-powered public grievance analysis, resolution recommendation and accountability platform', { x: 0.8, y: 3.85, w: 8.6, h: 1.0, fontFace: B, fontSize: 24, color: C.sky, margin: 0, isTextBox: true });
    s.addText('One real problem, one issue — prioritised, resolved, confirmed by the citizen, escalated if not.', { x: 0.8, y: 5.0, w: 8.6, h: 0.5, fontFace: B, fontSize: 16, italic: true, color: 'CBD5E1', margin: 0, isTextBox: true });
    s.addText('Team Viper', { x: 0.8, y: 6.3, w: 6, h: 0.45, fontFace: B, fontSize: 18, bold: true, color: C.white, margin: 0, isTextBox: true });
  }

  // 2. Problem -------------------------------------------------------------
  {
    const s = slide();
    title(s, 'The problem', 'Citizens complain. Systems file. Problems repeat.');
    const items = [
      [fa.FaInbox, 'Manual triage', 'Thousands of free-text complaints, in several languages, read and sorted by hand.'],
      [fa.FaShuffle, 'Wrong routing', 'Complaints bounce between departments before reaching the right team.'],
      [fa.FaTriangleExclamation, 'No real prioritisation', 'A live wire near a school waits in the same queue as a broken bench.'],
      [fa.FaClone, 'Duplicates', 'The same pothole reported 20 times means 20 tickets and wasted field visits.'],
      [fa.FaMagnifyingGlassChart, 'No root-cause insight', 'Clusters and spikes (e.g. a dengue outbreak) go unnoticed until too late.'],
      [fa.FaCommentSlash, 'No accountability', '"Resolved" is declared by the department, and an ignored complaint simply goes quiet.'],
    ];
    for (let i = 0; i < items.length; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 1.9 + row * 2.5;
      card(s, x, y, 3.8, 2.2);
      await circleIcon(s, items[i][0], x + 0.3, y + 0.3, 0.7, 'FEE2E2', C.red);
      s.addText(items[i][1], { x: x + 1.15, y: y + 0.35, w: 2.5, h: 0.6, fontFace: H, fontSize: 17, bold: true, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(items[i][2], { x: x + 0.3, y: y + 1.1, w: 3.25, h: 0.95, fontFace: B, fontSize: 14, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
    }
  }

  // 3. Solution ------------------------------------------------------------
  {
    const s = slide(C.white);
    title(s, 'Our solution: SamajSevak', 'An AI co-pilot for grievance cells — for citizens, officers and administrators.');
    const pillars = [
      [fa.FaBrain, 'Understand', C.blue, C.soft, 'Reads English, Hindi, Marathi and Hinglish. Classifies category and department, extracts ward, landmark, duration, risk words and vulnerable groups.'],
      [fa.FaGaugeHigh, 'Prioritise', C.orange, 'FFEDD5', 'Explainable 0–100 urgency score. Reports of the same real-world problem are gathered into one master issue using text, GPS and photo evidence.'],
      [fa.FaLightbulb, 'Resolve', C.green, 'DCFCE7', 'Step-by-step action plan from SOPs plus what fixed similar past cases, an ETA, a drafted reply and photo proof of the fix.'],
      [fa.FaScaleBalanced, 'Hold accountable', C.red, 'FEE2E2', 'The citizen confirms the fix. Unresolved issues move through Complaint, Warning and three strikes, every step in an audit trail.'],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.08;
      card(s, x, 1.95, 2.85, 4.2);
      await circleIcon(s, pillars[i][0], x + 0.3, 2.25, 0.9, pillars[i][3], pillars[i][2]);
      s.addText(pillars[i][1], { x: x + 0.3, y: 3.35, w: 2.4, h: 0.5, fontFace: H, fontSize: 20, bold: true, color: C.ink, margin: 0, isTextBox: true });
      s.addText(pillars[i][4], { x: x + 0.3, y: 3.9, w: 2.3, h: 2.1, fontFace: B, fontSize: 13.5, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
    }
    s.addText('Works fully offline with local ML; plugs into Gemini / OpenAI when a key is available.', { x: 0.6, y: 6.4, w: 12, h: 0.4, fontFace: B, fontSize: 15, italic: true, color: C.blue2, margin: 0, isTextBox: true });
  }

  // 4. Citizen portal -------------------------------------------------------
  {
    const s = slide();
    title(s, 'Citizen portal: evidence first, live AI while you type', null);
    shot(s, 'submit', 0.6, 1.4, 7.9);
    points(s, [
      ['Photo, GPS or map pin', 'The photo is evidence; the location tells one pothole from another.'],
      ['Type or speak, in your language', 'English, हिंदी, मराठी or Hinglish. The page and the Speak button switch language.'],
      ['"Already reported nearby?"', 'Open issues that match are shown before submitting; one tap joins the existing issue.'],
      ['Instant, explained triage', 'Department, priority, ETA and the reasons, shown before the complaint is filed.'],
      ['Name + mobile is the account', 'Officers only ever see an internal citizen ID.'],
    ], 8.85, 1.35, 1.08, 3.3);
  }

  // 5. Master issue ---------------------------------------------------------
  {
    const s = slide(C.white);
    title(s, 'One real problem = one master issue', 'Many citizens can report it; the department works on it once. No report is ever deleted.');
    shot(s, 'detail', 0.6, 1.8, 6.9);
    const steps = [
      ['1', 'Citizen joins first', 'Shown the open issue while typing and taps "Join". Recorded as CITIZEN; the AI makes no merge decision for that report.', C.blue],
      ['2', 'AI fallback after submission', 'Only if nothing was joined. Links on combined evidence: within 300 m + matching wording or photo; without GPS, same ward + strong wording + same landmark.', C.orange],
      ['3', 'Never on a weak signal', 'Same ward, same category or the same keyword alone does not merge. The same words 2 km away stay a separate issue.', C.red],
      ['4', 'Officer has the last word', 'Sees the evidence for every link and can confirm, detach or re-link. Each action is in the audit trail.', C.green],
    ];
    steps.forEach((r, i) => {
      const y = 1.8 + i * 1.12;
      card(s, 7.8, y, 4.95, 1.0);
      s.addShape(pres.shapes.OVAL, { x: 7.95, y: y + 0.29, w: 0.42, h: 0.42, fill: { color: r[3] }, line: { color: r[3] } });
      s.addText(r[0], { x: 7.95, y: y + 0.29, w: 0.42, h: 0.42, fontFace: H, fontSize: 13, bold: true, color: C.white, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
      s.addText([{ text: r[1], options: { bold: true, color: C.ink, fontSize: 13.5, breakLine: true } }, { text: r[2], options: { color: C.muted, fontSize: 11 } }],
        { x: 8.5, y: y + 0.05, w: 4.15, h: 0.9, fontFace: B, margin: 0, valign: 'middle', isTextBox: true });
    });
    s.addText('Photo reuse is detected with a file hash and a perceptual hash: it compares pictures, it does not understand them. The example above is an English report and a Marathi report of the same fallen wire, 46 m apart.', { x: 0.6, y: 6.3, w: 12.1, h: 0.6, fontFace: B, fontSize: 12.5, italic: true, color: C.muted, margin: 0, isTextBox: true });
  }

  // 6. Accountability --------------------------------------------------------
  {
    const s = slide();
    title(s, 'Accountability: the citizen confirms, the issue escalates', 'Resolved means "awaiting citizen confirmation". Silence is never read as satisfied.');
    STAGE.forEach((r, i) => {
      const x = 0.6 + i * 2.45;
      card(s, x, 1.85, 2.25, 1.75);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.2, y: 2.05, w: 0.6, h: 0.1, rectRadius: 0.05, fill: { color: r[1] }, line: { color: r[1] } });
      s.addText(r[0], { x: x + 0.2, y: 2.2, w: 1.9, h: 0.45, fontFace: H, fontSize: 18, bold: true, color: r[1], margin: 0, isTextBox: true });
      s.addText(r[2], { x: x + 0.2, y: 2.65, w: 1.9, h: 0.85, fontFace: B, fontSize: 12, color: C.ink, margin: 0, valign: 'top', isTextBox: true });
      if (i < 4) s.addText('›', { x: x + 2.22, y: 2.4, w: 0.26, h: 0.5, fontFace: H, fontSize: 22, color: '94A3B8', align: 'center', margin: 0, isTextBox: true });
    });
    shot(s, 'track', 0.6, 3.95, 4.55);
    const rules = [
      ['A warning never leaves the department.', 'Only the strikes go upward. A strike marks how long an issue has gone unresolved; it is not a score of any officer, department or party.'],
      ['Satisfied closes. Not satisfied reopens.', 'The issue reopens for every citizen on it and the escalation clock continues where it stopped.'],
      ['One escalation per master issue.', 'Three citizens reporting one wire means one ladder, not three.'],
      ['Timers live in one place.', 'By default the Complaint period is the category SLA and each later stage half of it. They are placeholders, not legal deadlines.'],
    ];
    rules.forEach((r, i) => {
      const y = 3.95 + i * 0.72;
      s.addText([{ text: r[0] + '  ', options: { bold: true, color: C.ink } }, { text: r[1], options: { color: C.muted } }], { x: 5.45, y, w: 7.3, h: 0.66, fontFace: B, fontSize: 12.5, margin: 0, valign: 'top', isTextBox: true });
    });
    s.addText('This ladder is the prototype’s own workflow, not a verified legal or government procedure. Escalation updates records and screens; nothing is sent to a real authority yet.', { x: 5.45, y: 6.85, w: 4.3, h: 0.5, fontFace: B, fontSize: 10.5, italic: true, color: C.amber, margin: 0, isTextBox: true });
  }

  // 7. Officer console ------------------------------------------------------
  {
    const s = slide();
    title(s, 'Officer console: decide faster, act smarter', null);
    shot(s, 'dashboard', 0.6, 1.35, 6.0);
    shot(s, 'queue', 6.75, 1.35, 6.0);
    s.addText('Command Center — KPIs, open issues by escalation stage, AI alerts', { x: 0.6, y: 5.2, w: 6.0, h: 0.5, fontFace: B, fontSize: 13, color: C.muted, margin: 0, isTextBox: true });
    s.addText('Priority queue — one row per master issue, with stage and who holds it', { x: 6.75, y: 5.2, w: 6.0, h: 0.5, fontFace: B, fontSize: 13, color: C.muted, margin: 0, isTextBox: true });
    const chips = ['Login required', 'Auto-routing', 'Master issues', 'Confirm / correct AI', 'Photo proof on resolve', 'Full audit trail'];
    chips.forEach((c, i) => {
      const x = 0.6 + i * 2.05;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 6.05, w: 1.9, h: 0.5, rectRadius: 0.25, fill: { color: C.soft }, line: { color: C.soft } });
      s.addText(c, { x, y: 6.05, w: 1.9, h: 0.5, fontFace: B, fontSize: 12, bold: true, color: C.blue2, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
    });
  }

  // 8. AI pipeline -----------------------------------------------------------
  {
    const s = slide(C.white);
    title(s, 'The AI pipeline', 'Every complaint passes through 8 stages in about 30 ms on a laptop CPU.');
    const st = [
      [fa.FaLanguage, 'Detect language', 'English, Hinglish, Hindi, Marathi fully; other scripts flagged for human review'],
      [fa.FaTags, 'Classify & route', 'TF-IDF + multilingual sentence embeddings, averaged → 11 categories'],
      [fa.FaLocationDot, 'Extract entities', 'Ward, landmark, duration, risk words, vulnerable groups, in all four languages'],
      [fa.FaFaceFrown, 'Sentiment', 'Lexicon + intensifiers + !/CAPS → distress score'],
      [fa.FaClone, 'Find the same issue', 'Meaning-level similarity across languages + GPS distance + photo hash'],
      [fa.FaGaugeHigh, 'Score priority', 'Explainable 0–100 from 7 weighted factors, a rule engine not a black box'],
      [fa.FaListCheck, 'Recommend', 'SOP playbook + proven past fixes + median ETA'],
      [fa.FaTowerBroadcast, 'Detect spikes', 'Ward × category vs 3-week baseline → alerts'],
    ];
    for (let i = 0; i < 8; i++) {
      const col = i % 4, row = Math.floor(i / 4);
      const x = 0.6 + col * 3.1, y = 1.95 + row * 2.45;
      card(s, x, y, 2.8, 2.1, i < 4 ? 'F7FAFF' : 'FFFBF5');
      await circleIcon(s, st[i][0], x + 0.25, y + 0.25, 0.62, i < 4 ? C.soft : 'FFEDD5', i < 4 ? C.blue : C.orange);
      s.addText(`${i + 1}. ${st[i][1]}`, { x: x + 1.0, y: y + 0.28, w: 1.7, h: 0.56, fontFace: H, fontSize: 14, bold: true, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(st[i][2], { x: x + 0.25, y: y + 1.0, w: 2.35, h: 0.95, fontFace: B, fontSize: 13, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
      if (col < 3) s.addText('›', { x: x + 2.8, y: y + 0.75, w: 0.3, h: 0.5, fontFace: H, fontSize: 24, color: 'CBD5E1', align: 'center', margin: 0, isTextBox: true });
    }
    s.addText('+ optional GenAI (Gemini / OpenAI) drafts replies and checks the photo against the complaint. Advisory only: it never decides category, priority or routing.', { x: 0.6, y: 6.75, w: 9.1, h: 0.5, fontFace: B, fontSize: 12.5, italic: true, color: C.blue2, margin: 0, isTextBox: true });
  }

  // 9. Explainable priority -------------------------------------------------
  {
    const s = slide();
    title(s, 'Explainable priority, not a black box', 'Officers see exactly why a case is urgent — and can defend the decision.');
    card(s, 0.6, 1.9, 6.1, 4.9);
    s.addText('Example complaint', { x: 0.9, y: 2.1, w: 5.5, h: 0.4, fontFace: H, fontSize: 14, bold: true, color: C.muted, margin: 0, isTextBox: true });
    s.addText('“Live electric wire has fallen near the primary school in Kothrud since yesterday. Children walk here daily, extremely dangerous!”', { x: 0.9, y: 2.5, w: 5.5, h: 1.1, fontFace: B, fontSize: 15, italic: true, color: C.ink, margin: 0, valign: 'top', isTextBox: true });
    const f = [['Category severity (Electricity)', 22.5], ['Risk keywords: live electric wire, dangerous', 26], ['Vulnerable groups: children, school', 12], ['2 similar open complaints nearby', 8], ['Issue persisting ~1 day', 3.2], ['Citizen distress', 1.2]];
    f.forEach((r, i) => {
      const y = 3.8 + i * 0.47;
      s.addText(r[0], { x: 0.9, y, w: 3.4, h: 0.4, fontFace: B, fontSize: 13, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.4, y: y + 0.13, w: 1.5, h: 0.14, rectRadius: 0.07, fill: { color: 'E2E8F0' }, line: { color: 'E2E8F0' } });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.4, y: y + 0.13, w: Math.max(0.1, 1.5 * r[1] / 30), h: 0.14, rectRadius: 0.07, fill: { color: C.red }, line: { color: C.red } });
      s.addText('+' + r[1], { x: 5.95, y, w: 0.6, h: 0.4, fontFace: H, fontSize: 13, bold: true, color: C.ink, align: 'right', margin: 0, valign: 'middle', isTextBox: true });
    });
    card(s, 7.0, 1.9, 5.7, 2.3, C.navy);
    s.addText('73', { x: 7.3, y: 2.05, w: 2.2, h: 1.4, fontFace: H, fontSize: 72, bold: true, color: 'FCA5A5', margin: 0, isTextBox: true });
    s.addText('/100  CRITICAL', { x: 7.3, y: 3.4, w: 3, h: 0.5, fontFace: H, fontSize: 18, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText('Routed to Electricity Board · ETA 12 h · SLA 24 h', { x: 9.6, y: 2.3, w: 2.9, h: 1.6, fontFace: B, fontSize: 15, color: C.sky, margin: 0, valign: 'middle', isTextBox: true });
    card(s, 7.0, 4.45, 5.7, 2.35);
    s.addText([
      { text: 'Critical ≥ 60   ·   High ≥ 42   ·   Medium ≥ 25   ·   Low', options: { bold: true, color: C.ink, breakLine: true } },
      { text: 'The same Hindi or Marathi complaint produces the same factors: local-language risk words map to one shared vocabulary.', options: { color: C.muted, breakLine: true } },
      { text: 'Low confidence (< 40%), an unsupported language, or the citizen and AI disagreeing on category sends the case to human triage.', options: { color: C.blue2 } },
    ], { x: 7.3, y: 4.65, w: 5.1, h: 2.0, fontFace: B, fontSize: 14, margin: 0, valign: 'top', paraSpaceAfter: 8, isTextBox: true });
  }

  // 10. Privacy & trust -------------------------------------------------------
  {
    const s = slide(C.white);
    title(s, 'Privacy and trust by design', 'What each side can and cannot see.');
    const items = [
      [fa.FaUserShield, 'Citizen identity stays hidden', 'Login is name + mobile. Officers see an internal ID such as CIT-00013: never the name or the number, on any screen or API.'],
      [fa.FaLock, 'Officer console behind a login', 'Salted password hash and signed 8-hour tokens. The audit trail records who did what.'],
      [fa.FaEye, 'Public page shows counts only', 'Received, resolved, pending, by stage, department and ward. No complaint text, people or locations. No rankings or scores.'],
      [fa.FaFlag, 'Abuse signals, not verdicts', 'A reused photo, a burst from one account or network, identical text. Two signals raise a review flag; nothing is rejected automatically.'],
      [fa.FaRobot, 'The LLM never decides', 'Category, priority, routing and escalation stay deterministic and explainable. GenAI only drafts and advises.'],
      [fa.FaClockRotateLeft, 'Everything is auditable', 'Every join, link, correction, resolution, citizen answer and escalation is an event with actor, time, previous and new state.'],
    ];
    for (let i = 0; i < items.length; i++) {
      const col = i % 3, row = Math.floor(i / 3);
      const x = 0.6 + col * 4.1, y = 1.9 + row * 2.5;
      card(s, x, y, 3.8, 2.25);
      await circleIcon(s, items[i][0], x + 0.3, y + 0.3, 0.7, C.soft, C.blue);
      s.addText(items[i][1], { x: x + 1.15, y: y + 0.3, w: 2.5, h: 0.7, fontFace: H, fontSize: 15.5, bold: true, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(items[i][2], { x: x + 0.3, y: y + 1.1, w: 3.25, h: 1.05, fontFace: B, fontSize: 12.5, color: C.muted, margin: 0, valign: 'top', isTextBox: true });
    }
  }

  // 11. Architecture ----------------------------------------------------------
  {
    const s = slide(C.white, false);
    title(s, 'System architecture', null);
    const box = (x, y, w, h, head, body, fill, headColor) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: fill }, line: { color: C.line, width: 0.75 } });
      s.addText(head, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.4, fontFace: H, fontSize: 14, bold: true, color: headColor, margin: 0, isTextBox: true });
      s.addText(body, { x: x + 0.15, y: y + 0.5, w: w - 0.3, h: h - 0.6, fontFace: B, fontSize: 12, color: C.ink, margin: 0, valign: 'top', isTextBox: true });
    };
    const arrow = (x1, y1, x2, y2, dash) => s.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color: '94A3B8', width: 1.5, endArrowType: 'triangle', dashType: dash ? 'dash' : 'solid' } });
    box(0.6, 1.5, 2.4, 2.1, 'Channels', 'Web portal (3 languages)\nVoice · photo · GPS / map pin\nWhatsApp / IVR (planned)', 'FFF7ED', 'C2410C');
    box(0.6, 4.1, 2.4, 2.1, 'Users', 'Citizens (name + mobile)\nOfficers (login)\nPublic (aggregate page)\nHigher authorities (stages)', 'FFF7ED', 'C2410C');
    box(3.6, 1.5, 2.6, 4.7, 'React UI (Vite)', 'Raise grievance + join issue\nTrack, confirm, rate\nMy complaints\nPublic accountability\nCommand Center\nPriority queue\nCase workspace\nHotspot map · AI Engine', C.soft, C.blue2);
    box(6.8, 1.5, 2.6, 4.7, 'FastAPI backend', 'REST API + OpenAPI docs\nCitizen + officer auth\nMaster-issue service\nSatisfaction workflow\nEscalation engine\nAbuse signals\nAnalytics & alerts\nAudit trail', 'EFF6FF', C.blue2);
    box(10.0, 1.5, 2.75, 2.75, 'AI Engine', 'TF-IDF + multilingual\nembeddings (ONNX, CPU)\nEntities · sentiment\nSimilarity + GPS + photo hash\nPriority scorer\nRecommender · spike detector', 'F0FDF4', '166534');
    box(10.0, 4.5, 1.3, 1.7, 'Data', 'SQLite: reports, events, citizens, officers', 'F8FAFC', C.ink);
    box(11.45, 4.5, 1.3, 1.7, 'Knowledge', 'SOPs, SLAs, lexicons, stage config', 'F8FAFC', C.ink);
    arrow(3.0, 2.55, 3.6, 2.55); arrow(3.0, 5.15, 3.6, 5.15);
    arrow(6.2, 3.85, 6.8, 3.85); arrow(9.4, 2.9, 10.0, 2.9); arrow(9.4, 5.35, 10.0, 5.35);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.8, y: 6.45, w: 5.95, h: 0.6, rectRadius: 0.1, fill: { color: 'FAF5FF' }, line: { color: 'D8B4FE', dashType: 'dash' } });
    s.addText('Optional: Gemini 2.0 Flash / GPT-4o-mini — reply drafting and photo check, template fallback offline', { x: 6.95, y: 6.45, w: 5.7, h: 0.6, fontFace: B, fontSize: 12, color: '6B21A8', valign: 'middle', margin: 0, isTextBox: true });
    arrow(8.1, 6.2, 8.1, 6.45, true);
    s.addText('Flow: report → join or AI-link to a master issue → route & prioritise → officer resolves with proof → citizen confirms → closed, or reopened and escalated', { x: 0.6, y: 6.45, w: 5.9, h: 0.7, fontFace: B, fontSize: 12, italic: true, color: C.muted, margin: 0, valign: 'middle', isTextBox: true });
  }

  // 12. Tech stack ------------------------------------------------------------
  {
    const s = slide();
    title(s, 'Tech stack', 'Lightweight, open-source and deployable on a single government server.');
    const groups = [
      [fa.FaReact, 'Frontend', C.blue, C.soft, ['React 19 + Vite', 'React Router', 'Recharts', 'Leaflet + OpenStreetMap', 'Web Speech API (voice)']],
      [fa.FaPython, 'Backend', C.blue2, 'DBEAFE', ['Python 3.11', 'FastAPI + Uvicorn', 'SQLite (PostgreSQL-ready)', 'PBKDF2 + HMAC tokens (stdlib)', 'pytest: 17 tests']],
      [fa.FaBrain, 'AI / ML', C.green, 'DCFCE7', ['scikit-learn: TF-IDF, LogReg', 'fastembed + ONNX Runtime', 'Multilingual MiniLM, CPU only', 'Pillow: photo hashes', 'Gemini / OpenAI (optional)']],
      [fa.FaDocker, 'Deploy', C.orange, 'FFEDD5', ['Docker single container', 'Render / any VM', 'OpenAPI docs at /docs', 'Env-based keys and timers', 'Runs offline, no GPU']],
    ];
    for (let i = 0; i < 4; i++) {
      const x = 0.6 + i * 3.08;
      card(s, x, 1.9, 2.85, 4.8);
      await circleIcon(s, groups[i][0], x + 0.3, 2.15, 0.85, groups[i][3], groups[i][2]);
      s.addText(groups[i][1], { x: x + 1.3, y: 2.15, w: 1.4, h: 0.85, fontFace: H, fontSize: 19, bold: true, color: C.ink, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(groups[i][4].map((t, j, a) => ({ text: t, options: { bullet: true, breakLine: j < a.length - 1 } })),
        { x: x + 0.25, y: 3.25, w: 2.45, h: 3.2, fontFace: B, fontSize: 14, color: C.ink, paraSpaceAfter: 10, valign: 'top', margin: 0, isTextBox: true });
    }
  }

  // 13. Insights --------------------------------------------------------------
  {
    const s = slide(C.white);
    title(s, 'From complaints to prevention', 'Hotspots, emerging-issue alerts and department accountability.');
    shot(s, 'insights', 0.6, 1.8, 7.2);
    card(s, 8.15, 1.8, 4.6, 2.35, 'FEF2F2');
    s.addText([
      { text: 'Emerging hotspot detected', options: { bold: true, color: C.red, fontSize: 16, breakLine: true } },
      { text: 'Drainage and public-health complaints in Hadapsar this week — far above the 3-week baseline (planted in the demo data).', options: { color: C.ink, fontSize: 14, breakLine: true } },
      { text: 'Recommendation: a ward-level drive instead of case-by-case fixes.', options: { color: C.muted, fontSize: 13 } },
    ], { x: 8.4, y: 1.95, w: 4.15, h: 2.1, fontFace: B, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
    const b = [['Ward risk ranking', 'Open & urgent load per ward, top issue'], ['SLA compliance by department', 'Lowest performers surface first'], ['Public accountability page', 'Aggregate counts by stage, department and ward']];
    b.forEach((r, i) => {
      const y = 4.4 + i * 0.65;
      s.addText([{ text: r[0] + '  ', options: { bold: true, color: C.ink } }, { text: r[1], options: { color: C.muted } }], { x: 8.15, y, w: 4.6, h: 0.55, fontFace: B, fontSize: 13, margin: 0, valign: 'middle', isTextBox: true });
    });
  }

  // 14. Results ----------------------------------------------------------------
  {
    const s = slide(C.navy, false);
    s.addText('Prototype results', { x: 0.6, y: 0.4, w: 12, h: 0.75, fontFace: H, fontSize: 32, bold: true, color: C.white, margin: 0, isTextBox: true });
    s.addText('Measured on the working prototype (backend/models/metrics.json, 17 automated tests)', { x: 0.6, y: 1.12, w: 12, h: 0.45, fontFace: B, fontSize: 16, color: 'CBD5E1', margin: 0, isTextBox: true });
    const st = [
      ['87.9%', 'category accuracy on 66 hand-written English + Hinglish complaints kept unseen until the templates were frozen (58/66). TF-IDF alone: 80.3%'],
      ['90.9% · 84.8%', 'Hindi · Marathi (Devanagari, 33 each) before any training text in those languages existed. 100% · 97.0% after, which is optimistic'],
      ['~30 ms', 'full AI analysis per complaint on a laptop CPU, no GPU'],
      ['4 + 5', 'languages with the full pipeline, and five escalation stages with every transition tested'],
    ];
    st.forEach((r, i) => {
      const x = 0.6 + i * 3.1;
      s.addText(r[0], { x, y: 2.0, w: 2.95, h: 1.0, fontFace: H, fontSize: i === 1 ? 30 : 46, bold: true, color: i % 2 ? C.sky : C.white, margin: 0, valign: 'bottom', isTextBox: true });
      s.addText(r[1], { x, y: 3.1, w: 2.8, h: 1.4, fontFace: B, fontSize: 13, color: 'CBD5E1', margin: 0, valign: 'top', isTextBox: true });
    });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.7, w: 12.1, h: 2.2, rectRadius: 0.12, fill: { color: '1E293B' }, line: { color: '334155' } });
    s.addText([
      { text: 'What the demo shows', options: { bold: true, color: C.white, fontSize: 17, breakLine: true } },
      { text: 'About 460 seeded reports across 12 Pune wards forming master issues · an English and a Marathi report of the same fallen wire linked automatically · open issues spread over all five stages · citizen "not satisfied" reopening an issue · hotspot spike alert in Hadapsar.', options: { color: 'CBD5E1', fontSize: 14, breakLine: true } },
      { text: 'Honest notes: all data is synthetic, so no real-world accuracy is claimed; no real complaints have been collected yet. The officer-verification loop that retrains on real corrections is built. Citizen login has no OTP. Escalation changes records and screens only. The photo check needs an LLM key.', options: { color: 'FCD34D', fontSize: 12.5, italic: true } },
    ], { x: 0.9, y: 4.85, w: 11.5, h: 1.95, fontFace: B, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
  }

  // 15. Impact & roadmap -------------------------------------------------------
  {
    const s = slide();
    title(s, 'Impact & roadmap', null);
    card(s, 0.6, 1.4, 5.9, 5.35);
    await circleIcon(s, fa.FaHandHoldingHeart, 0.9, 1.65, 0.7, 'DCFCE7', C.green);
    s.addText('Impact', { x: 1.75, y: 1.65, w: 4, h: 0.7, fontFace: H, fontSize: 22, bold: true, color: C.ink, valign: 'middle', margin: 0, isTextBox: true });
    const imp = ['Life-safety issues reach the right team first', 'One workload per real problem, not one per complaint', 'Officers get a proven action plan, not a blank page', 'An issue is closed by the citizen, not by the department', 'Ignored issues escalate on a visible, audited ladder', 'Citizens report in their own language and stay anonymous to officers'];
    s.addText(imp.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < imp.length - 1 } })), { x: 0.95, y: 2.6, w: 5.3, h: 3.9, fontFace: B, fontSize: 15, color: C.ink, paraSpaceAfter: 10, valign: 'top', margin: 0, isTextBox: true });
    const road = [
      ['Next', 'Accounts and notifications for each escalation authority; OTP for citizens'],
      ['Next', 'Real complaint data through the officer-verification loop; more Indian languages'],
      ['Scale', 'WhatsApp chatbot & IVR intake; CPGRAMS / municipal ERP integration'],
      ['Scale', 'Offline image model for photo evidence; PostgreSQL + PostGIS'],
      ['Future', 'Predictive maintenance: forecast issues before complaints arrive'],
    ];
    road.forEach((r, i) => {
      const y = 1.4 + i * 1.08;
      card(s, 6.8, y, 5.9, 0.9);
      const col = r[0] === 'Next' ? C.blue : r[0] === 'Scale' ? C.orange : C.green;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.0, y: y + 0.25, w: 0.9, h: 0.4, rectRadius: 0.2, fill: { color: col }, line: { color: col } });
      s.addText(r[0], { x: 7.0, y: y + 0.25, w: 0.9, h: 0.4, fontFace: H, fontSize: 11, bold: true, color: C.white, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
      s.addText(r[1], { x: 8.05, y: y + 0.05, w: 4.5, h: 0.8, fontFace: B, fontSize: 13, color: C.ink, valign: 'middle', margin: 0, isTextBox: true });
    });
  }

  // 16. Thank you ---------------------------------------------------------------
  {
    const s = pres.addSlide(); s.background = { color: C.navy };
    s.addShape(pres.shapes.OVAL, { x: -1.5, y: 4.2, w: 5, h: 5, fill: { color: C.blue, transparency: 20 }, line: { color: C.blue, transparency: 100 } });
    await circleIcon(s, fa.FaShieldHalved, 6.17, 1.1, 1.0, C.white, C.blue);
    s.addText('Thank you', { x: 0.6, y: 2.3, w: 12.1, h: 1.1, fontFace: H, fontSize: 54, bold: true, color: C.white, align: 'center', margin: 0, isTextBox: true });
    s.addText('SamajSevak — every voice heard, every issue followed through.', { x: 0.6, y: 3.4, w: 12.1, h: 0.6, fontFace: B, fontSize: 20, color: C.sky, align: 'center', margin: 0, isTextBox: true });
    s.addText([
      { text: 'GitHub: ', options: { bold: true, color: C.sky } }, { text: 'github.com/<your-username>/samajsevak', options: { color: C.white, breakLine: true } },
      { text: 'Run: ', options: { bold: true, color: C.sky } }, { text: 'docker build -t samajsevak . && docker run -p 8000:8000 samajsevak', options: { color: C.white } },
    ], { x: 2.2, y: 4.5, w: 8.9, h: 1.0, fontFace: B, fontSize: 16, align: 'center', margin: 0, paraSpaceAfter: 6, isTextBox: true });
    s.addText('Team Viper  ·  Hack2Ignite  ·  AI-04', { x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontFace: B, fontSize: 14, color: '94A3B8', align: 'center', margin: 0, isTextBox: true });
  }

  await pres.writeFile({ fileName: OUT });
  console.log('wrote', OUT);
})();
