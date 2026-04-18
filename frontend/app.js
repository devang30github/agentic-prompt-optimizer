const API = window.location.origin;
let chartInstance = null;

// ── Main pipeline runner ──
async function runPipeline() {
  const rawInput    = document.getElementById('rawInput').value.trim();
  const sampleInput = document.getElementById('sampleInput').value.trim();

  if (!rawInput) { showToast('Please enter a requirement.'); return; }

  setRunning(true);
  resetStages();
  hideResults();

  try {
    const res = await fetch(`${API}/optimize/stream`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        raw_input:    rawInput,
        sample_input: sampleInput || 'Hello, can you help me?',
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Pipeline failed.');
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const event = JSON.parse(line.slice(6));
        handleEvent(event);
      }
    }

  } catch (err) {
    resetStages();
    showToast(err.message);
  } finally {
    setRunning(false);
  }
}

// ── Handle SSE events ──
function handleEvent(event) {
  if (event.error) {
    showToast(event.error);
    resetStages();
    return;
  }

  const stageMap = {
    analyst:  'stageAnalyst',
    hub:      'stageHub',
    executor: 'stageExecutor',
    scorer:   'stageScorer',
  };

  if (event.stage && event.stage !== 'complete') {
    const id = stageMap[event.stage];

    if (event.status === 'start') {
      activateStage(id);
    }

    if (event.status === 'round') {
      // Update hub label to show current round + live score
      const stageEl = document.getElementById('stageHub');
      stageEl.querySelector('.stage-desc').textContent =
        `Round ${event.round} — score ${event.score}/10`;
    }

    if (event.status === 'done') {
      document.getElementById(id).className = 'stage done';
    }
  }

  if (event.stage === 'complete') {
    markAllDone();
    renderResults(event.result);
  }
}

// ── Render all results ──
function renderResults(data) {
  document.getElementById('scoreValue').textContent  = data.final_score.toFixed(1);
  document.getElementById('roundsLabel').textContent = `${data.total_rounds} round${data.total_rounds !== 1 ? 's' : ''}`;

  const badge = document.getElementById('badgePassed');
  badge.textContent = data.passed ? 'PASSED' : 'MAX ROUNDS';
  badge.className   = 'badge' + (data.passed ? '' : ' failed');

  renderChart(data.score_history);
  renderScorecard(data.scorecard);

  document.getElementById('finalPrompt').textContent    = data.final_prompt;
  document.getElementById('executorOutput').textContent = data.executor_output || '—';

  renderIterations(data.iterations);

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
        data:                 scoreHistory,
        borderColor:          '#a3e635',
        backgroundColor:      'rgba(163,230,53,0.08)',
        pointBackgroundColor: '#a3e635',
        pointRadius:          5,
        pointHoverRadius:     7,
        borderWidth:          2,
        fill:                 true,
        tension:              0.4,
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
          callbacks: { label: ctx => ` Score: ${ctx.parsed.y}/10` },
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

// ── Stage helpers ──
function activateStage(id) {
  document.getElementById(id).className = 'stage active';
}

function resetStages() {
  ['stageAnalyst','stageHub','stageExecutor','stageScorer'].forEach(id => {
    document.getElementById(id).className = 'stage';
    if (id === 'stageHub') {
      document.getElementById(id).querySelector('.stage-desc').textContent = 'Iterative refinement';
    }
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

// ── Onboarding Guide Logic ──
const guides = {
  raw: {
    title: "01 / The Raw Requirement",
    text: "Enter your prompt idea in plain English. For example: 'A travel agent that suggests hidden gems in Europe.' The Analyst agent will structure this into a professional prompt for you."
  },
  sample: {
    title: "02 / The Sample Message",
    text: "Provide an example of what a user would say to your AI. This is used to test the final optimized prompt so you can see the 'Executor' output immediately."
  }
};

function toggleGuide(type) {
  const overlay = document.getElementById('guideOverlay');
  const title = document.getElementById('guideTitle');
  const text = document.getElementById('guideText');

  if (type && guides[type]) {
    title.textContent = guides[type].title;
    text.textContent = guides[type].text;
    overlay.style.display = 'flex';
  } else {
    overlay.style.display = 'none';
  }
}

// Show guide on first visit
window.addEventListener('DOMContentLoaded', () => {
  if (!localStorage.getItem('apo_onboarded')) {
    setTimeout(() => toggleGuide('raw'), 1000); // 1 second delay for effect
    localStorage.setItem('apo_onboarded', 'true');
  }
});