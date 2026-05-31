"""
Run this script once to produce dashboard.html.
Usage: python3 generate_dashboard.py

Requires dashboard.css and dashboard.js to be in the same directory.
"""

import json
import os
import pandas as pd
from scipy.stats import mannwhitneyu

CSV_FILE = "cell-count.csv"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

POP_LABELS = {
    "b_cell": "B Cell",
    "cd8_t_cell": "CD8 T Cell",
    "cd4_t_cell": "CD4 T Cell",
    "nk_cell": "NK Cell",
    "monocyte": "Monocyte",
}

# ── Load & enrich data ────────────────────────────────────────────────────────

df = pd.read_csv(CSV_FILE)

df["total_cells"] = df[POPULATIONS].sum(axis=1)
for pop in POPULATIONS:
    df[f"{pop}_freq"] = (df[pop] / df["total_cells"]).round(6)

# ── Pre-compute statistical results (Part 3) ─────────────────────────────────

stat_subset = df[
    (df["condition"] == "melanoma")
    & (df["treatment"] == "miraclib")
    & (df["sample_type"] == "PBMC")
].copy()

stat_results = {}
for pop in POPULATIONS:
    resp   = stat_subset[stat_subset["response"] == "yes"][f"{pop}_freq"]
    nonresp = stat_subset[stat_subset["response"] == "no"][f"{pop}_freq"]
    _, pval = mannwhitneyu(resp, nonresp, alternative="two-sided")
    stat_results[pop] = {
        "label":           POP_LABELS[pop],
        "resp_mean":       round(float(resp.mean()), 4),
        "nonresp_mean":    round(float(nonresp.mean()), 4),
        "pvalue":          round(float(pval), 6),
        "significant":     bool(pval < 0.05),
        "resp_values":     resp.round(6).tolist(),
        "nonresp_values":  nonresp.round(6).tolist(),
        "time_values":     stat_subset["time_from_treatment_start"].tolist(),
        "freq_values":     stat_subset[f"{pop}_freq"].tolist(),
        "response_values": stat_subset["response"].tolist(),
    }

# ── Serialize raw data ────────────────────────────────────────────────────────

keep_cols = [
    "sample", "project", "subject", "condition", "sex",
    "treatment", "response", "sample_type", "time_from_treatment_start",
    "total_cells",
] + POPULATIONS + [f"{p}_freq" for p in POPULATIONS]

records = df[keep_cols].to_dict(orient="records")

data_json      = json.dumps(records)
stat_json      = json.dumps(stat_results)
pop_list_json  = json.dumps(POPULATIONS)
pop_label_json = json.dumps(POP_LABELS)

# ── HTML template ─────────────────────────────────────────────────────────────

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Cell Count Dashboard</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"/>
<link rel="stylesheet" href="dashboard.css"/>
<script src="https://cdn.plot.ly/plotly-2.34.0.min.js"></script>
</head>
<body>

<div class="dashboard-header mb-3">
  <div class="header-eyebrow">Immunology Research</div>
  <h1>Cell Count Dashboard</h1>
  <p>Interactive exploration of immune cell populations across clinical samples</p>
</div>

<div class="container-fluid px-4">

  <!-- TAB NAV -->
  <ul class="nav nav-tabs" id="mainTabs">
    <li class="nav-item"><a class="nav-link active" href="#" data-tab="overview">Data Overview</a></li>
    <li class="nav-item"><a class="nav-link"        href="#" data-tab="stats"   >Statistical Analysis</a></li>
    <li class="nav-item"><a class="nav-link"        href="#" data-tab="subset"  >Subset Analysis</a></li>
  </ul>

  <!-- TAB 1 — DATA OVERVIEW -->
  <div id="tab-overview" class="tab-content">

    <div class="row g-3 mb-3">
      <div class="col-md-4">
        <label class="form-label fw-semibold">Condition</label>
        <select id="f-condition" class="form-select form-select-sm" multiple size="3"></select>
        <small class="text-muted">Hold Ctrl/⌘ to multi-select</small>
      </div>
      <div class="col-md-4">
        <label class="form-label fw-semibold">Treatment</label>
        <select id="f-treatment" class="form-select form-select-sm" multiple size="3"></select>
      </div>
      <div class="col-md-4">
        <label class="form-label fw-semibold">Sample Type</label>
        <select id="f-sampletype" class="form-select form-select-sm" multiple size="3"></select>
      </div>
    </div>
    <div class="row mb-3">
      <div class="col-auto">
        <button class="btn btn-sm btn-outline-secondary" id="btn-clear">Clear filters</button>
      </div>
      <div class="col-auto align-self-center text-muted small" id="filter-count"></div>
    </div>

    <div class="chart-card">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="fw-semibold mb-0">Relative Cell Population Frequencies</h6>
        <small class="text-muted">sample &nbsp;·&nbsp; total_count &nbsp;·&nbsp; population &nbsp;·&nbsp; count &nbsp;·&nbsp; percentage</small>
      </div>
      <div class="freq-table-wrapper">
        <table class="table table-sm table-hover freq-table mb-0">
          <thead>
            <tr>
              <th>Sample</th>
              <th>Total Count</th>
              <th>Population</th>
              <th>Count</th>
              <th>Percentage (%)</th>
            </tr>
          </thead>
          <tbody id="freq-tbody"></tbody>
        </table>
      </div>
      <div class="pagination-bar">
        <button class="btn btn-sm btn-outline-secondary" id="page-prev">&#8592; Prev</button>
        <small class="text-muted" id="page-info"></small>
        <button class="btn btn-sm btn-outline-secondary" id="page-next">Next &#8594;</button>
      </div>
    </div>

  </div>

  <!-- TAB 2 — STATISTICAL ANALYSIS -->
  <div id="tab-stats" class="tab-content tab-hidden">

    <h6 class="fw-semibold mb-1">Mann-Whitney U Test</h6>
    <p>Comparing relative frequencies of responders vs non-responders in the melanoma + miraclib + PBMC subset. Significant populations (p&nbsp;&lt;&nbsp;0.05) are highlighted in green.</p>
    <div class="row g-2 mt-3" id="stat-kpis"></div>

    <div class="row mt-4 mb-3">
      <div class="col-md-4">
        <label class="form-label fw-semibold">Select Population to Visualize</label>
        <select id="stat-pop" class="form-select form-select-sm"></select>
      </div>
    </div>

    <div class="row g-3 mb-4">
      <div class="col-md-6"><div class="chart-card"><div id="chart-boxplot"></div></div></div>
      <div class="col-md-6"><div class="chart-card"><div id="chart-scatter"></div></div></div>
    </div>

    <div class="chart-card mb-3">
      <h6 class="fw-semibold mb-2">Relative Frequency Summary: Responders vs Non-Responders</h6>
      <table class="table table-sm table-bordered stat-table mb-0">
        <thead>
          <tr>
            <th>Population</th>
            <th>Responder Mean Freq</th>
            <th>Non-responder Mean Freq</th>
            <th>p-value</th>
            <th>Significant</th>
          </tr>
        </thead>
        <tbody id="stat-tbody"></tbody>
      </table>
    </div>

  </div>

  <!-- TAB 3 — SUBSET ANALYSIS -->
  <div id="tab-subset" class="tab-content tab-hidden">

    <p class="text-muted mb-3">Melanoma + miraclib + PBMC + time from treatment start = 0.</p>

    <div class="row g-2 mb-3" id="subset-kpis"></div>

    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="chart-card"><div id="chart-project-bar"></div></div></div>
      <div class="col-md-4"><div class="chart-card"><div id="chart-pie-response"></div></div></div>
      <div class="col-md-4"><div class="chart-card"><div id="chart-pie-sex"></div></div></div>
    </div>

  </div>

</div>

<!-- Inject data as globals, then load app logic -->
<script>
const ALL_DATA    = {data_json};
const STAT        = {stat_json};
const POPULATIONS = {pop_list_json};
const POP_LABELS  = {pop_label_json};
</script>
<script src="dashboard.js"></script>

</body>
</html>
"""

output_path = "dashboard.html"
with open(output_path, "w") as f:
    f.write(HTML)

print(f"Generated: {output_path}")
print(f"Open in your browser: file://{os.path.abspath(output_path)}")
