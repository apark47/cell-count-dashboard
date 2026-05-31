// ALL_DATA, STAT, POPULATIONS, POP_LABELS are injected as globals by dashboard.html

// ── Colour constants ──────────────────────────────────────────────────────────

const RESP_COLOR  = '#2196F3';
const NRESP_COLOR = '#FF7043';
const COLOR_SEX   = { F: '#E91E8C', M: '#1565C0' };
const PALETTE     = ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B2'];

// ═══════════════════════════════════════════════════════════
// TAB SWITCHING
// ═══════════════════════════════════════════════════════════

document.querySelectorAll('[data-tab]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    document.querySelectorAll('[data-tab]').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('tab-hidden'));
    document.getElementById('tab-' + link.dataset.tab).classList.remove('tab-hidden');
    if (link.dataset.tab === 'stats')  renderStats();
    if (link.dataset.tab === 'subset') renderSubset();
  });
});

// ═══════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════

function unique(arr) { return [...new Set(arr)].sort(); }

function linReg(xs, ys) {
  const n  = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  const num = xs.reduce((s, x, i) => s + (x - mx) * (ys[i] - my), 0);
  const den = xs.reduce((s, x) => s + (x - mx) ** 2, 0);
  const m = den ? num / den : 0;
  const b = my - m * mx;
  return { m, b };
}

function applyFilters(conditions, treatments, sampleTypes) {
  return ALL_DATA.filter(r =>
    (!conditions.length  || conditions.includes(r.condition))   &&
    (!treatments.length  || treatments.includes(r.treatment))   &&
    (!sampleTypes.length || sampleTypes.includes(r.sample_type))
  );
}

// ═══════════════════════════════════════════════════════════
// TAB 1 — DATA OVERVIEW
// ═══════════════════════════════════════════════════════════

(function initOverview() {
  const PAGE_SIZE = 50;
  let tableRows = [];
  let currentPage = 0;

  function populateSelect(id, values) {
    const sel = document.getElementById(id);
    values.forEach(v => {
      const opt = document.createElement('option');
      opt.value = opt.textContent = v;
      sel.appendChild(opt);
    });
  }

  populateSelect('f-condition',  unique(ALL_DATA.map(r => r.condition)));
  populateSelect('f-treatment',  unique(ALL_DATA.map(r => r.treatment)));
  populateSelect('f-sampletype', unique(ALL_DATA.map(r => r.sample_type)));

  function getSelected(id) {
    return [...document.getElementById(id).selectedOptions].map(o => o.value);
  }

  // Melt wide ALL_DATA into long-format relative-frequency rows
  function buildFreqRows(data) {
    const rows = [];
    data.forEach(r => {
      POPULATIONS.forEach(pop => {
        rows.push({
          sample:      r.sample,
          total_count: r.total_cells,
          population:  pop,
          count:       r[pop],
          percentage:  (r[pop + '_freq'] * 100).toFixed(4),
        });
      });
    });
    return rows;
  }

  function renderPage() {
    const start = currentPage * PAGE_SIZE;
    const end   = Math.min(start + PAGE_SIZE, tableRows.length);
    const page  = tableRows.slice(start, end);

    document.getElementById('freq-tbody').innerHTML = page.map(r => `
      <tr>
        <td>${r.sample}</td>
        <td>${r.total_count.toLocaleString()}</td>
        <td>${POP_LABELS[r.population]}</td>
        <td>${r.count.toLocaleString()}</td>
        <td>${r.percentage}</td>
      </tr>
    `).join('');

    document.getElementById('page-info').textContent =
      tableRows.length ? `Rows ${start + 1}–${end} of ${tableRows.length.toLocaleString()}` : 'No results';
    document.getElementById('page-prev').disabled = currentPage === 0;
    document.getElementById('page-next').disabled = end >= tableRows.length;
  }

  function render() {
    const filtered = applyFilters(
      getSelected('f-condition'),
      getSelected('f-treatment'),
      getSelected('f-sampletype')
    );

    document.getElementById('filter-count').textContent =
      `${filtered.length.toLocaleString()} samples · ${(filtered.length * POPULATIONS.length).toLocaleString()} rows`;

    tableRows  = buildFreqRows(filtered);
    currentPage = 0;
    renderPage();
  }

  document.getElementById('page-prev').addEventListener('click', () => {
    if (currentPage > 0) { currentPage--; renderPage(); }
  });
  document.getElementById('page-next').addEventListener('click', () => {
    if ((currentPage + 1) * PAGE_SIZE < tableRows.length) { currentPage++; renderPage(); }
  });

  ['f-condition', 'f-treatment', 'f-sampletype'].forEach(id =>
    document.getElementById(id).addEventListener('change', render)
  );
  document.getElementById('btn-clear').addEventListener('click', () => {
    ['f-condition', 'f-treatment', 'f-sampletype'].forEach(id => {
      [...document.getElementById(id).options].forEach(o => o.selected = false);
    });
    render();
  });

  render();
})();

// ═══════════════════════════════════════════════════════════
// TAB 2 — STATISTICAL ANALYSIS
// ═══════════════════════════════════════════════════════════

let statsRendered = false;

function renderStats() {
  if (!statsRendered) {
    // KPI cards
    const kpiRow = document.getElementById('stat-kpis');
    POPULATIONS.forEach(pop => {
      const s = STAT[pop];
      const col = document.createElement('div');
      col.className = 'col';
      col.innerHTML = `
        <div class="kpi-card">
          <div class="kpi-lbl">${s.label}</div>
          <div class="kpi-val ${s.significant ? 'kpi-success' : ''}">
            ${s.pvalue < 0.001 ? '< 0.001' : s.pvalue.toFixed(4)}
          </div>
          <span class="sig-badge ${s.significant ? 'sig-yes' : 'sig-no'}">
            ${s.significant ? 'Significant ✓' : 'Not significant'}
          </span>
        </div>`;
      kpiRow.appendChild(col);
    });

    // Summary table
    const tbody = document.getElementById('stat-tbody');
    POPULATIONS.forEach(pop => {
      const s = STAT[pop];
      const tr = document.createElement('tr');
      if (s.significant) tr.classList.add('significant');
      tr.innerHTML = `
        <td>${s.label}</td>
        <td>${s.resp_mean.toFixed(4)}</td>
        <td>${s.nonresp_mean.toFixed(4)}</td>
        <td>${s.pvalue < 0.001 ? '< 0.001' : s.pvalue.toFixed(5)}</td>
        <td><span class="sig-badge ${s.significant ? 'sig-yes' : 'sig-no'}">
          ${s.significant ? 'Yes' : 'No'}</span></td>`;
      tbody.appendChild(tr);
    });

    // Population dropdown for charts
    const popSel = document.getElementById('stat-pop');
    POPULATIONS.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p;
      opt.textContent = POP_LABELS[p];
      popSel.appendChild(opt);
    });
    popSel.value = 'cd8_t_cell';
    popSel.addEventListener('change', () => renderStatCharts(popSel.value));

    statsRendered = true;
  }

  renderStatCharts(document.getElementById('stat-pop').value);
}

function renderStatCharts(pop) {
  const s = STAT[pop];
  const pLabel  = s.pvalue < 0.001 ? '< 0.001' : `p = ${s.pvalue.toFixed(4)}`;
  const sigText = s.significant ? `${pLabel} (significant)` : `${pLabel} (not significant)`;

  Plotly.react('chart-boxplot', [
    { y: s.resp_values,    name: 'Responders',     type: 'box',
      marker: { color: RESP_COLOR },  boxpoints: 'all', jitter: 0.3, pointpos: -1.5 },
    { y: s.nonresp_values, name: 'Non-Responders', type: 'box',
      marker: { color: NRESP_COLOR }, boxpoints: 'all', jitter: 0.3, pointpos: -1.5 },
  ], {
    title: `${s.label} Relative Frequency<br><sub>${sigText}</sub>`,
    yaxis: { title: 'Relative Frequency' },
    height: 400, margin: { t: 70 },
    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  }, { responsive: true, displayModeBar: false });

  const respIdx  = s.response_values.map((r, i) => r === 'yes' ? i : -1).filter(i => i >= 0);
  const nrespIdx = s.response_values.map((r, i) => r === 'no'  ? i : -1).filter(i => i >= 0);

  function trend(idxs) {
    const xs = idxs.map(i => s.time_values[i]);
    const ys = idxs.map(i => s.freq_values[i]);
    const { m, b } = linReg(xs, ys);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    return { xs: [minX, maxX], ys: [m * minX + b, m * maxX + b] };
  }

  const tR = trend(respIdx), tN = trend(nrespIdx);

  Plotly.react('chart-scatter', [
    { x: respIdx.map(i  => s.time_values[i]), y: respIdx.map(i  => s.freq_values[i]),
      mode: 'markers', name: 'Responders',     marker: { color: RESP_COLOR,  size: 6 } },
    { x: nrespIdx.map(i => s.time_values[i]), y: nrespIdx.map(i => s.freq_values[i]),
      mode: 'markers', name: 'Non-Responders', marker: { color: NRESP_COLOR, size: 6 } },
    { x: tR.xs, y: tR.ys, mode: 'lines', name: 'Trend (R)',
      line: { color: RESP_COLOR,  dash: 'dash' }, showlegend: false },
    { x: tN.xs, y: tN.ys, mode: 'lines', name: 'Trend (NR)',
      line: { color: NRESP_COLOR, dash: 'dash' }, showlegend: false },
  ], {
    title: `${s.label} Frequency Over Time`,
    xaxis: { title: 'Days from Treatment Start' },
    yaxis: { title: 'Relative Frequency' },
    height: 400, margin: { t: 50 },
    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  }, { responsive: true, displayModeBar: false });
}

// ═══════════════════════════════════════════════════════════
// TAB 3 — SUBSET ANALYSIS
// ═══════════════════════════════════════════════════════════

let subsetRendered = false;

function renderSubset() {
  if (subsetRendered) return;
  subsetRendered = true;

  const sub = ALL_DATA.filter(r =>
    r.condition === 'melanoma' &&
    r.treatment === 'miraclib' &&
    r.sample_type === 'PBMC' &&
    r.time_from_treatment_start === 0
  );

  const subjects  = [...new Set(sub.map(r => r.subject))];
  const respSubs  = [...new Set(sub.filter(r => r.response === 'yes').map(r => r.subject))];
  const nrespSubs = [...new Set(sub.filter(r => r.response === 'no').map(r => r.subject))];

  const kpiData = [
    { label: 'Total Samples',   value: sub.length,       cls: ''            },
    { label: 'Unique Subjects', value: subjects.length,  cls: ''            },
    { label: 'Responders',      value: respSubs.length,  cls: 'kpi-success' },
    { label: 'Non-responders',  value: nrespSubs.length, cls: 'kpi-danger'  },
  ];
  const kpiRow = document.getElementById('subset-kpis');
  kpiData.forEach(k => {
    const col = document.createElement('div');
    col.className = 'col-md-3';
    col.innerHTML = `<div class="kpi-card">
      <div class="kpi-lbl">${k.label}</div>
      <div class="kpi-val ${k.cls}">${k.value}</div>
    </div>`;
    kpiRow.appendChild(col);
  });

  const projCounts = {};
  sub.forEach(r => projCounts[r.project] = (projCounts[r.project] || 0) + 1);
  const projNames = Object.keys(projCounts).sort();

  Plotly.newPlot('chart-project-bar',
    [{ type: 'bar', x: projNames, y: projNames.map(p => projCounts[p]),
       marker: { color: PALETTE } }],
    { title: 'Samples per Project', height: 320,
      yaxis: { title: 'Count' }, xaxis: { title: 'Project' },
      margin: { t: 50, b: 60 }, showlegend: false,
      paper_bgcolor: 'transparent', plot_bgcolor: 'transparent' },
    { responsive: true, displayModeBar: false }
  );

  Plotly.newPlot('chart-pie-response',
    [{ type: 'pie',
       labels: ['Responders', 'Non-Responders'],
       values: [respSubs.length, nrespSubs.length],
       marker: { colors: [RESP_COLOR, NRESP_COLOR] },
       hole: 0.45, textinfo: 'value',
       domain: { x: [0.15, 0.85], y: [0.1, 1] } }],
    { title: 'Subjects by Response', height: 320,
      margin: { t: 50, b: 40, l: 20, r: 20 },
      legend: { orientation: 'h', xanchor: 'center', x: 0.5, y: -0.02 },
      paper_bgcolor: 'transparent' },
    { responsive: true, displayModeBar: false }
  );

  const sexCounts = {};
  [...new Set(sub.map(r => r.subject))].forEach(s => {
    const row = sub.find(r => r.subject === s);
    sexCounts[row.sex] = (sexCounts[row.sex] || 0) + 1;
  });

  Plotly.newPlot('chart-pie-sex',
    [{ type: 'pie',
       labels: Object.keys(sexCounts),
       values: Object.values(sexCounts),
       marker: { colors: Object.keys(sexCounts).map(s => COLOR_SEX[s] || '#888') },
       hole: 0.45, textinfo: 'label+value' }],
    { title: 'Subjects by Sex', height: 320,
      margin: { t: 50, b: 20, l: 20, r: 20 },
      paper_bgcolor: 'transparent' },
    { responsive: true, displayModeBar: false }
  );
}
