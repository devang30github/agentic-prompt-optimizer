const API = 'http://localhost:8000';
let chartInstance = null;

// ── Main pipeline runner ──
async function runPipeline() {
  const rawInput    = document.getElementById('rawInput').value.trim();
  const sampleInput = document.getElementById('sampleInput').value.trim();

  if (!rawInput) { showToast('Please enter a requirement.'); return; }

  setRunning(true);
  resetStages();
  hideResults();

  // Simulate stage progression while waiting for API
  activateStage('stageAnalyst');
  const stageTimer = simulateStages();

  try {
    const res = await fetch(`${API}/optimize`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        raw_input:    rawInput,
        sample_input: sampleInput || 'Hello, can you help me?',
      }),
    });

    clearInterval(stageTimer);

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Pipeline failed.');
    }

    const data = await res.json();
    markAllDone();
    renderResults(data);

  } catch (err) {
    clearInterval(stageTimer);
    resetStages();
    showToast(err.message);
  } finally {
    setRunning(false);
  }
}

// ── Render all results ──
function renderResults(data) {
  // Score header
  document.getElementById('scoreValue').textContent  = data.final_score.toFixed(1);
  document.getElementById('roundsLabel').textContent = `${data.total_rounds} round${data.total_rounds !== 1 ? 's' : ''}`;

  const badge = document.getElementById('badgePassed');
  badge.textContent = data.passed ? 'PASSED' : 'MAX ROUNDS';
  badge.className   = 'badge' + (data.passed ? '' : ' failed');

  // Score chart
  renderChart(data.score_history);

  // Scorecard
  renderScorecard(data.scorecard);

  // Final prompt
  document.getElementById('finalPrompt').textContent = data.final_prompt;

  // Executor output
  document.getElementById('executorOutput').textContent = data.executor_output || '—';

  // Iterations log
  renderIterations(data.iterations);

  // Show results
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('results').style.display    = 'block';
  document.getElementById('statusPill').textContent   = 'done';
  document.getElementById('statusPill').className     = 'status-pill done';
}

// ── Chart ──
function renderChart(scoreHistory) {
  const ctx = document.getElementById('scoreChart').getContext('2d');
  if (chartInstance) chartInstance.destroy();

  const labels = scoreHistory.map((_, i) => `Round ${i + 1}`);

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data:            scoreHistory,
        borderColor:     '#a3e635',
        backgroundColor: 'rgba(163,230,53,0.08)',
        pointBackgroundColor: '#a3e635',
        pointRadius:     5,
        pointHoverRadius: 7,
        borderWidth:     2,
        fill:            true,
        tension:         0.4,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1a1f',
          borderColor:     '#2a2a32',
          borderWidth:     1,
          titleColor:      '#6b6b7a',
          bodyColor:       '#e8e8f0',
          callbacks: {
            label: ctx => ` Score: ${ctx.parsed.y}/10`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#6b6b7a', font: { family: 'DM Mono', size: 11 } },
          grid:  { color: '#1a1a1f' },
        },
        y: {
          min:   0,
          max:   10,
          ticks: { color: '#6b6b7a', font: { family: 'DM Mono', size: 11 }, stepSize: 2 },
          grid:  { color: '#2a2a32' },
        },
      },
    },
  });
}

function activateStage(id) {
  document.getElementById(id).className = 'stage active';
}

// ── Scorecard ──
function renderScorecard(scorecard) {
  const dims = [
    { key: 'clarity',            label: 'Clarity' },
    { key: 'completeness',       label: 'Completeness' },
    { key: 'hallucination_risk', label: 'Hallucination risk' },
    { key: 'edge_case_handling', label: 'Edge case handling' },
    { key: 'token_efficiency',   label: 'Token efficiency' },
  ];

  const grid = document.getElementById('scorecardGrid');
  grid.innerHTML = '';

  dims.forEach(({ key, label }) => {
    const val = scorecard[key] ?? 0;
    const pct = (val / 10) * 100;
    grid.innerHTML += `
      <div class="scorecard-item">
        <span class="scorecard-item-label">${label}</span>
        <div class="scorecard-bar-wrap">
          <div class="scorecard-bar" style="width:0%" data-width="${pct}%"></div>
        </div>
        <span class="scorecard-item-score">${val}/10</span>
      </div>`;
  });

  // Animate bars after render
  requestAnimationFrame(() => {
    document.querySelectorAll('.scorecard-bar').forEach(bar => {
      bar.style.width = bar.dataset.width;
    });
  });

  document.getElementById('scorecardSummary').textContent = scorecard.summary || '';
}

// ── Iterations log ──
function renderIterations(iterations) {
  const log = document.getElementById('iterationsLog');
  log.innerHTML = iterations.map(it => `
    <div class="iteration-item">
      <div class="iteration-header">
        <span class="iteration-round">Round ${it.iteration}</span>
        <span class="iteration-score">${it.score}/10</span>
      </div>
      <div class="iteration-feedback">${it.critic_feedback}</div>
    </div>
  `).join('');
}

// ── Copy prompt ──
function copyPrompt() {
  const text = document.getElementById('finalPrompt').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'copied!';
    setTimeout(() => btn.textContent = 'copy', 1500);
  });
}

// ── Stage simulation ──
function simulateStages() {
  const stages = ['stageAnalyst', 'stageHub', 'stageExecutor', 'stageScorer'];
  let i = 0;
  return setInterval(() => {
    if (i > 0) document.getElementById(stages[i - 1]).className = 'stage done';
    if (i < stages.length) {
      document.getElementById(stages[i]).className = 'stage active';
      i++;
    }
  }, 4000);
}

function resetStages() {
  ['stageAnalyst','stageHub','stageExecutor','stageScorer'].forEach(id => {
    document.getElementById(id).className = 'stage';
  });
}

function markAllDone() {
  ['stageAnalyst','stageHub','stageExecutor','stageScorer'].forEach(id => {
    document.getElementById(id).className = 'stage done';
  });
}

// ── UI helpers ──
function setRunning(val) {
  const btn  = document.getElementById('runBtn');
  const pill = document.getElementById('statusPill');
  btn.disabled = val;
  document.getElementById('btnText').textContent = val ? 'Running...' : 'Run pipeline';
  pill.textContent = val ? 'running' : 'idle';
  pill.className   = 'status-pill' + (val ? ' running' : '');
}

function hideResults() {
  document.getElementById('emptyState').style.display = 'flex';
  document.getElementById('results').style.display    = 'none';
}

function showToast(msg) {
  const t = document.createElement('div');
  t.className   = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}