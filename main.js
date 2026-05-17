/* ═══════════════════════════════════════════════════════════
   LectureMind AI — main.js
   Drag-and-drop · API calls · Animations · Toasts · Copy
═══════════════════════════════════════════════════════════ */

'use strict';

// ── DOM refs ────────────────────────────────────────────────
const navbar        = document.getElementById('navbar');
const hamburger     = document.getElementById('hamburger');
const navLinks      = document.getElementById('navLinks');
const tabUpload     = document.getElementById('tabUpload');
const tabPaste      = document.getElementById('tabPaste');
const panelUpload   = document.getElementById('panelUpload');
const panelPaste    = document.getElementById('panelPaste');
const dropZone      = document.getElementById('dropZone');
const fileInput     = document.getElementById('fileInput');
const filePreview   = document.getElementById('filePreview');
const textInput     = document.getElementById('textInput');
const charCount     = document.getElementById('charCount');
const summarizeBtn  = document.getElementById('summarizeBtn');
const loadingOverlay= document.getElementById('loadingOverlay');
const loadingText   = document.getElementById('loadingText');
const loadingFill   = document.getElementById('loadingFill');
const outputSection = document.getElementById('output');
const outputGrid    = document.getElementById('outputGrid');
const outputMeta    = document.getElementById('outputMeta');
const toastContainer= document.getElementById('toastContainer');
const demoSection   = document.getElementById('demoSection');

let selectedFile = null;
let lastResult   = null;

/* ══ NAVBAR ════════════════════════════════════════════════ */
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 40);
});

hamburger.addEventListener('click', () => {
  hamburger.classList.toggle('open');
  navLinks.classList.toggle('open');
});

// Close mobile menu on link click
navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  hamburger.classList.remove('open');
  navLinks.classList.remove('open');
}));

/* ══ TABS ══════════════════════════════════════════════════ */
tabUpload.addEventListener('click', () => switchTab('upload'));
tabPaste.addEventListener('click',  () => switchTab('paste'));

function switchTab(which) {
  tabUpload.classList.toggle('active', which === 'upload');
  tabPaste.classList.toggle('active',  which === 'paste');
  panelUpload.classList.toggle('active', which === 'upload');
  panelPaste.classList.toggle('active',  which === 'paste');
}

/* ══ CHARACTER COUNT ═══════════════════════════════════════ */
textInput.addEventListener('input', () => {
  const n = textInput.value.length;
  charCount.textContent = `${n.toLocaleString()} character${n !== 1 ? 's' : ''}`;
});

/* ══ FILE DRAG & DROP ══════════════════════════════════════ */
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', ()  => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
  const allowed = ['application/pdf','text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
  if (!allowed.includes(file.type) && !file.name.match(/\.(pdf|docx|txt)$/i)) {
    toast('Please upload a PDF, DOCX, or TXT file.', 'error');
    return;
  }
  if (file.size > 16 * 1024 * 1024) {
    toast('File exceeds 16 MB limit.', 'error');
    return;
  }
  selectedFile = file;
  const icon = file.name.endsWith('.pdf') ? 'fa-file-pdf' :
               file.name.endsWith('.docx') ? 'fa-file-word' : 'fa-file-lines';
  filePreview.innerHTML = `
    <div class="file-item">
      <i class="fa-regular ${icon}"></i>
      <span>${file.name}</span>
      <span style="color:var(--text-muted);font-size:0.78rem;">(${(file.size/1024).toFixed(1)} KB)</span>
      <button onclick="clearFile()" style="background:none;border:none;color:var(--accent-3);cursor:pointer;font-size:1rem;padding:0 4px;">×</button>
    </div>`;
}

window.clearFile = function() {
  selectedFile = null;
  filePreview.innerHTML = '';
  fileInput.value = '';
};

/* ══ SCROLL HELPER ═════════════════════════════════════════ */
window.scrollToUpload = function() {
  document.getElementById('summarize').scrollIntoView({ behavior: 'smooth' });
};

/* ══ LOADING ANIMATION ═════════════════════════════════════ */
const loadingMessages = [
  'Reading your notes...',
  'Extracting key concepts...',
  'Generating quiz questions...',
  'Crafting exam notes...',
  'Almost ready...'
];

function showLoading() {
  loadingOverlay.classList.add('active');
  loadingFill.style.width = '0';
  let msgIdx = 0;
  loadingText.textContent = loadingMessages[0];

  const msgTimer = setInterval(() => {
    msgIdx = (msgIdx + 1) % loadingMessages.length;
    loadingText.textContent = loadingMessages[msgIdx];
  }, 1200);

  // Animate progress bar
  let pct = 0;
  const barTimer = setInterval(() => {
    pct = Math.min(pct + Math.random() * 12, 88);
    loadingFill.style.width = pct + '%';
    if (pct >= 88) clearInterval(barTimer);
  }, 300);

  return { msgTimer, barTimer };
}

function hideLoading(timers) {
  clearInterval(timers.msgTimer);
  clearInterval(timers.barTimer);
  loadingFill.style.width = '100%';
  setTimeout(() => loadingOverlay.classList.remove('active'), 400);
}

/* ══ MAIN SUMMARIZE HANDLER ════════════════════════════════ */
window.handleSummarize = async function() {
  const mode = document.getElementById('summaryMode').value;
  const activeTab = panelUpload.classList.contains('active') ? 'upload' : 'paste';

  // Validate input
  if (activeTab === 'upload' && !selectedFile) {
    toast('Please select a file to upload.', 'error');
    return;
  }
  if (activeTab === 'paste' && !textInput.value.trim()) {
    toast('Please paste some text first.', 'error');
    return;
  }

  const timers = showLoading();

  try {
    let response;

    if (activeTab === 'upload') {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('mode', mode);
      response = await fetch('/summarize', { method: 'POST', body: formData });
    } else {
      response = await fetch('/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: textInput.value, mode })
      });
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${response.status}`);
    }

    lastResult = await response.json();
    hideLoading(timers);
    renderOutput(lastResult, mode);

  } catch (err) {
    hideLoading(timers);
    toast(`Error: ${err.message}`, 'error');
    console.error(err);
  }
};

/* ══ RENDER OUTPUT ═════════════════════════════════════════ */
function renderOutput(data, mode) {
  // Meta badges
  outputMeta.innerHTML = `
    <div class="meta-badge"><i class="fa-solid fa-file-lines"></i> ${data.word_count ?? '—'} words</div>
    <div class="meta-badge"><i class="fa-regular fa-clock"></i> ~${data.reading_time ?? 1} min read</div>
    <div class="meta-badge"><i class="fa-solid fa-wand-magic-sparkles"></i> AI-generated</div>
  `;

  outputGrid.innerHTML = '';

  // Summary card
  if (data.summary && (mode === 'summary' || mode === 'all')) {
    outputGrid.appendChild(makeCard(
      'fa-align-left', 'Summary', data.summary, 'text'
    ));
  }

  // Key concepts card
  if (data.key_concepts?.length && (mode === 'concepts' || mode === 'all')) {
    outputGrid.appendChild(makeCard(
      'fa-lightbulb', 'Key Concepts', data.key_concepts, 'list'
    ));
  }

  // Quiz card
  if (data.quiz_questions?.length && (mode === 'quiz' || mode === 'all')) {
    outputGrid.appendChild(makeCard(
      'fa-circle-question', 'Quiz Questions', data.quiz_questions, 'quiz'
    ));
  }

  // Exam notes card
  if (data.exam_notes && (mode === 'exam' || mode === 'all')) {
    outputGrid.appendChild(makeCard(
      'fa-pen-to-square', 'Exam Notes', data.exam_notes, 'pre'
    ));
  }

  // Hide demo, show output
  demoSection.style.display = 'none';
  outputSection.style.display = 'block';
  outputSection.scrollIntoView({ behavior: 'smooth' });
  toast('Summary generated! ✨', 'success');
}

function makeCard(iconClass, title, content, type) {
  const card = document.createElement('div');
  card.className = 'output-card glass';

  let body = '';
  if (type === 'text') {
    body = `<p>${content}</p>`;
  } else if (type === 'list') {
    body = `<ul class="concept-list">${
      content.map(c => `<li><i class="fa-solid fa-circle-dot"></i>${c}</li>`).join('')
    }</ul>`;
  } else if (type === 'quiz') {
    body = content.map(q => `
      <div class="quiz-item" style="margin-bottom:14px;">
        <p class="quiz-q"><strong>Q:</strong> ${q.q}</p>
        <p class="quiz-a"><strong>A:</strong> ${q.a}</p>
      </div>`).join('');
  } else if (type === 'pre') {
    body = `<pre class="exam-notes">${content}</pre>`;
  }

  card.innerHTML = `
    <div class="card-header">
      <span class="card-icon"><i class="fa-solid ${iconClass}"></i></span>
      <span class="card-title">${title}</span>
    </div>
    ${body}
  `;
  return card;
}

/* ══ COPY & DOWNLOAD ═══════════════════════════════════════ */
window.copyAll = function() {
  if (!lastResult) return;
  const text = [
    '=== SUMMARY ===', lastResult.summary ?? '',
    '\n=== KEY CONCEPTS ===', (lastResult.key_concepts ?? []).join('\n'),
    '\n=== QUIZ QUESTIONS ===',
    (lastResult.quiz_questions ?? []).map((q,i) => `Q${i+1}: ${q.q}\nA: ${q.a}`).join('\n\n'),
    '\n=== EXAM NOTES ===', lastResult.exam_notes ?? ''
  ].join('\n');

  navigator.clipboard.writeText(text)
    .then(() => toast('Copied to clipboard!', 'success'))
    .catch(() => toast('Copy failed — try manually.', 'error'));
};

window.downloadSummary = function() {
  if (!lastResult) return;
  const text = [
    'LECTUREMIND AI — GENERATED SUMMARY',
    '='.repeat(40),
    '', 'SUMMARY:', lastResult.summary ?? '',
    '', 'KEY CONCEPTS:', (lastResult.key_concepts ?? []).map(c => '• ' + c).join('\n'),
    '', 'QUIZ QUESTIONS:',
    (lastResult.quiz_questions ?? []).map((q,i) => `Q${i+1}: ${q.q}\nA: ${q.a}`).join('\n\n'),
    '', 'EXAM NOTES:', lastResult.exam_notes ?? ''
  ].join('\n');

  const blob = new Blob([text], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'lecturemind-summary.txt';
  a.click();
  toast('Downloaded!', 'success');
};

/* ══ TOAST ══════════════════════════════════════════════════ */
function toast(message, type = 'success') {
  const icon = type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation';
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
  toastContainer.appendChild(el);

  setTimeout(() => {
    el.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

/* ══ SCROLL-TRIGGERED CARD ANIMATION ════════════════════════ */
const observer = new IntersectionObserver(entries => {
  entries.forEach((e, i) => {
    if (e.isIntersecting) {
      e.target.style.animationDelay = `${i * 0.08}s`;
      e.target.classList.add('fade-in-up');
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.12 });

function observeCards() {
  document.querySelectorAll('.feature-card, .demo-card, .step, .output-card').forEach(el => {
    el.style.opacity = '0';
    observer.observe(el);
  });
}

// Inject the keyframe once
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeInUp {
    from { opacity:0; transform: translateY(28px); }
    to   { opacity:1; transform: translateY(0); }
  }
  .fade-in-up {
    animation: fadeInUp 0.55s ease forwards;
  }
`;
document.head.appendChild(style);

// Run after DOM paint
requestAnimationFrame(() => {
  observeCards();
  toast('LectureMind AI ready! Upload notes or paste text.', 'success');
});