// ── Tabs ───────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab + '-tab').classList.remove('hidden');
  });
});

// ── Upload ─────────────────────────────────────────────
const dropZone  = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const selectBtn = document.getElementById('select-btn');

selectBtn.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
});

fileInput.addEventListener('change', e => {
  if (e.target.files[0]) handleUpload(e.target.files[0]);
});

function handleUpload(file) {
  const formData = new FormData();
  formData.append('file', file);
  showLoading('Extracting and analyzing code...');

  fetch('/api/upload', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      hideLoading();
      if (data.error) { showError(data.error); return; }
      renderResults(data);
      refreshPrevious();
    })
    .catch(err => { hideLoading(); showError(err.message); });
}

// ── GitHub ─────────────────────────────────────────────
document.getElementById('analyze-btn').addEventListener('click', () => {
  const url = document.getElementById('github-url').value.trim();
  if (!url) { alert('Please enter a GitHub URL'); return; }
  showLoading('Cloning repository and analyzing code...');

  fetch('/api/github', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: url })
  })
    .then(r => r.json())
    .then(data => {
      hideLoading();
      if (data.error) { showError(data.error); return; }
      renderResults(data);
      refreshPrevious();
    })
    .catch(err => { hideLoading(); showError(err.message); });
});

// ── Render Results ─────────────────────────────────────
function renderResults(data) {
  const score   = data.quality_score || 0;
  const metrics = data.metrics       || {};
  const issues  = data.issues        || [];

  // Score banner
  document.getElementById('score-project').textContent =
    data.project_name || 'Unknown Project';
  document.getElementById('score-value').textContent = score.toFixed(1);
  document.getElementById('score-ring-num').textContent = score.toFixed(1);

  // Animate ring
  const arc        = document.getElementById('score-arc');
  const circumf    = 314;
  const offset     = circumf - (score / 10) * circumf;
  arc.style.strokeDashoffset = offset;

  // Ring colour by score
  arc.style.stroke = score >= 8 ? '#3fb950' : score >= 6 ? '#ffa657' : '#f85149';

  // KPIs
  document.getElementById('kpi-files').textContent =
    (metrics.total_files || 0).toLocaleString();
  document.getElementById('kpi-lines').textContent =
    (metrics.total_lines || 0).toLocaleString();
  document.getElementById('kpi-funcs').textContent =
    (metrics.total_functions || 0).toLocaleString();
  document.getElementById('kpi-classes').textContent =
    (metrics.total_classes || 0).toLocaleString();
  document.getElementById('kpi-issues').textContent = issues.length;

  // Issues
  const issuesList = document.getElementById('issues-list');
  if (issues.length === 0) {
    issuesList.innerHTML =
      '<div class="no-issues">✅ No major issues found!</div>';
  } else {
    issuesList.innerHTML = issues.map(issue => {
      const sev    = (issue.severity || 'low').toLowerCase();
      const badge  = `badge-${sev}`;
      return `
        <div class="issue-row">
          <span class="issue-badge ${badge}">${sev}</span>
          <div>
            <div class="issue-desc">${issue.description}</div>
            ${issue.count ? `<div class="issue-count">${issue.count} item${issue.count > 1 ? 's' : ''} affected</div>` : ''}
          </div>
        </div>`;
    }).join('');
  }

  // AI Recommendations
  document.getElementById('recs-text').textContent = data.analysis || '';

  // Show section
  document.getElementById('results').classList.remove('hidden');
  document.getElementById('results').scrollIntoView({
    behavior: 'smooth', block: 'start'
  });
}

// ── Load Previous ──────────────────────────────────────
function loadAnalysis(id) {
  showLoading('Loading analysis...');
  fetch('/api/analysis/' + id)
    .then(r => r.json())
    .then(data => {
      hideLoading();
      if (data.error) { showError(data.error); return; }
      renderResults({
        project_name:  data.project_name,
        quality_score: data.quality_score,
        metrics:       data.metrics,
        issues:        data.issues,
        analysis:      data.analysis
      });
    })
    .catch(err => { hideLoading(); showError(err.message); });
}

function refreshPrevious() {
  fetch('/api/analyses')
    .then(r => r.json())
    .then(analyses => {
      const list = document.getElementById('prev-list');
      if (!analyses.length) {
        list.innerHTML = '<p class="empty-msg">No analyses yet.</p>';
        return;
      }
      list.innerHTML = analyses.map(a => {
        const scoreClass = a.quality_score >= 8 ? 'score-high'
                         : a.quality_score >= 6 ? 'score-mid'
                         : 'score-low';
        return `
          <div class="prev-item" onclick="loadAnalysis(${a.id})">
            <div class="prev-left">
              <span class="prev-name">${a.project_name}</span>
              <span class="prev-type">${a.upload_type}</span>
            </div>
            <div class="prev-right">
              <span class="prev-score ${scoreClass}">${parseFloat(a.quality_score).toFixed(1)}/10</span>
              <span class="prev-date">${new Date(a.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})}</span>
            </div>
          </div>`;
      }).join('');
    });
}

// ── UI Helpers ─────────────────────────────────────────
function showLoading(msg) {
  document.getElementById('loading-msg').textContent = msg || 'Analyzing...';
  document.getElementById('loading').classList.remove('hidden');
  document.getElementById('results').classList.add('hidden');
}

function hideLoading() {
  document.getElementById('loading').classList.add('hidden');
}

function showError(msg) {
  document.getElementById('results').classList.remove('hidden');
  document.getElementById('results').innerHTML =
    `<div class="card" style="border-color:#f85149;color:#f85149;padding:1.5rem">
       ⚠ Error: ${msg}
     </div>`;
}