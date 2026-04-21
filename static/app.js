'use strict';

const CHARTS = {};

// ------------------------------------------------------------------ //
// Helpers
// ------------------------------------------------------------------ //

function fmt(n, decimals = 0) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}
function fmtCurrency(n) {
  if (n == null) return '—';
  return '$' + fmt(n, 2);
}
function fmtPct(n) {
  if (n == null) return '—';
  return fmt(n, 1) + '%';
}

async function api(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json();
}

function chartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: true,
    plugins: { legend: { labels: { color: '#8892a4', font: { size: 12 } } } },
    scales: {
      x: { ticks: { color: '#8892a4' }, grid: { color: '#2a2d3e' } },
      y: { ticks: { color: '#8892a4' }, grid: { color: '#2a2d3e' } },
    },
  };
}

// ------------------------------------------------------------------ //
// KPIs + Cost Savings
// ------------------------------------------------------------------ //

async function loadKPIs() {
  const [summary, savings] = await Promise.all([
    api('/analysis/summary'),
    api('/analysis/cost-savings'),
  ]);
  document.getElementById('v-revenue').textContent  = fmtCurrency(savings.net_revenue);
  document.getElementById('v-discount').textContent = fmtCurrency(savings.total_discounts_given);
  document.getElementById('v-rate').textContent     = fmtPct(savings.discount_rate_pct);
  document.getElementById('v-invoices').textContent = fmt(savings.total_invoices);
  document.getElementById('v-guests').textContent   = fmt(summary.dim_guests);

  // Cost savings bar chart
  const canvas = document.getElementById('savings-chart');
  if (CHARTS['savings']) CHARTS['savings'].destroy();
  CHARTS['savings'] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: ['Gross Revenue', 'Net Revenue', 'Discounts Given', 'Tax Collected'],
      datasets: [{
        label: 'Amount ($)',
        data: [savings.gross_revenue, savings.net_revenue, savings.total_discounts_given, savings.total_tax_collected],
        backgroundColor: ['#6c63ff', '#00c9a7', '#f56565', '#ed8936'],
        borderRadius: 6,
      }],
    },
    options: {
      ...chartDefaults(),
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
    },
  });
}

// ------------------------------------------------------------------ //
// Revenue chart
// ------------------------------------------------------------------ //

async function loadRevenue() {
  const period = document.getElementById('period-select').value;
  const data = await api(`/analysis/revenue?period=${period}`);
  const canvas = document.getElementById('revenue-chart');
  if (CHARTS['revenue']) CHARTS['revenue'].destroy();
  CHARTS['revenue'] = new Chart(canvas, {
    type: 'line',
    data: {
      labels: data.map(r => r.period),
      datasets: [
        {
          label: 'Net Revenue',
          data: data.map(r => r.total_revenue),
          borderColor: '#6c63ff',
          backgroundColor: 'rgba(108,99,255,0.12)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
        {
          label: 'Discounts',
          data: data.map(r => r.total_discount),
          borderColor: '#f56565',
          backgroundColor: 'rgba(245,101,101,0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
      ],
    },
    options: chartDefaults(),
  });
}

// ------------------------------------------------------------------ //
// Booking trends
// ------------------------------------------------------------------ //

async function loadBookingTrends() {
  const data = await api('/analysis/booking-trends');
  const canvas = document.getElementById('booking-chart');
  if (CHARTS['booking']) CHARTS['booking'].destroy();
  CHARTS['booking'] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.map(r => r.day_of_week),
      datasets: [
        { label: 'Completed', data: data.map(r => r.completed), backgroundColor: '#00c9a7', borderRadius: 4 },
        { label: 'Cancelled', data: data.map(r => r.cancelled), backgroundColor: '#f56565', borderRadius: 4 },
      ],
    },
    options: { ...chartDefaults(), scales: { x: { stacked: true, ticks: { color: '#8892a4' }, grid: { color: '#2a2d3e' } }, y: { stacked: true, ticks: { color: '#8892a4' }, grid: { color: '#2a2d3e' } } } },
  });
}

// ------------------------------------------------------------------ //
// Top services table
// ------------------------------------------------------------------ //

async function loadTopServices() {
  const data = await api('/analysis/services/top?limit=10');
  const el = document.getElementById('services-table');
  if (!data.length) { el.innerHTML = '<p class="empty">No service data yet. Run a sync first.</p>'; return; }
  el.innerHTML = `
    <table>
      <thead><tr>
        <th>#</th><th>Service</th><th>Category</th><th>Bookings</th><th>Revenue</th><th>Avg Price</th>
      </tr></thead>
      <tbody>
        ${data.map((r, i) => `<tr>
          <td>${i + 1}</td>
          <td>${r.service_name}</td>
          <td>${r.category_name || '—'}</td>
          <td>${fmt(r.bookings)}</td>
          <td>${fmtCurrency(r.total_revenue)}</td>
          <td>${fmtCurrency(r.avg_price)}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

// ------------------------------------------------------------------ //
// Employee utilization table
// ------------------------------------------------------------------ //

async function loadEmployeeUtil() {
  const data = await api('/analysis/employees/utilization');
  const el = document.getElementById('employee-table');
  if (!data.length) { el.innerHTML = '<p class="empty">No employee data yet.</p>'; return; }
  el.innerHTML = `
    <table>
      <thead><tr>
        <th>Therapist</th><th>Designation</th><th>Completed</th><th>No-shows</th><th>Cancelled</th><th>Revenue</th>
      </tr></thead>
      <tbody>
        ${data.map(r => `<tr>
          <td>${r.therapist_name}</td>
          <td>${r.designation || '—'}</td>
          <td>${fmt(r.completed)}</td>
          <td>${fmt(r.no_shows)}</td>
          <td>${fmt(r.cancelled)}</td>
          <td>${fmtCurrency(r.total_revenue)}</td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

// ------------------------------------------------------------------ //
// Guest retention
// ------------------------------------------------------------------ //

async function loadRetention() {
  const data = await api('/analysis/guests/retention');
  const canvas = document.getElementById('retention-chart');
  if (CHARTS['retention']) CHARTS['retention'].destroy();

  const newG = data.new_guests || 0;
  const retG = data.returning_guests || 0;
  CHARTS['retention'] = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['New Guests', 'Returning Guests'],
      datasets: [{ data: [newG, retG], backgroundColor: ['#6c63ff', '#00c9a7'], borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { labels: { color: '#8892a4' } } },
    },
  });

  document.getElementById('retention-stats').innerHTML = `
    <div class="retention-stat"><div class="rs-val">${fmt(newG)}</div><div class="rs-lbl">New Guests</div></div>
    <div class="retention-stat"><div class="rs-val">${fmt(retG)}</div><div class="rs-lbl">Returning</div></div>
    <div class="retention-stat"><div class="rs-val">${fmt(data.avg_visits_per_guest, 1)}</div><div class="rs-lbl">Avg Visits</div></div>
  `;
}

// ------------------------------------------------------------------ //
// Sync log
// ------------------------------------------------------------------ //

async function loadSyncLog() {
  const data = await api('/sync/status');
  const el = document.getElementById('sync-log');
  if (!data.length) { el.innerHTML = '<p class="empty">No syncs yet. Click "Sync Data" to start.</p>'; return; }
  el.innerHTML = `
    <table>
      <thead><tr>
        <th>Entity</th><th>Center</th><th>Date Range</th><th>Records</th><th>Status</th><th>Started</th><th>Duration</th>
      </tr></thead>
      <tbody>
        ${data.map(r => {
          const started = r.started_at ? new Date(r.started_at).toLocaleString() : '—';
          let dur = '—';
          if (r.started_at && r.finished_at) {
            const ms = new Date(r.finished_at) - new Date(r.started_at);
            dur = ms < 1000 ? ms + 'ms' : (ms / 1000).toFixed(1) + 's';
          }
          const tagClass = { success: 'tag-success', error: 'tag-error', running: 'tag-running' }[r.status] || '';
          return `<tr>
            <td>${r.entity}</td>
            <td>${r.center_id || '—'}</td>
            <td>${r.start_date || ''}${r.end_date ? ' → ' + r.end_date : ''}</td>
            <td>${fmt(r.records_synced)}</td>
            <td><span class="tag ${tagClass}">${r.status}</span>${r.error_message ? `<br/><small style="color:#f56565">${r.error_message.slice(0, 80)}</small>` : ''}</td>
            <td>${started}</td>
            <td>${dur}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

// ------------------------------------------------------------------ //
// Sync trigger
// ------------------------------------------------------------------ //

let pollTimer = null;

async function triggerSync() {
  const btn = document.getElementById('sync-btn');
  const badge = document.getElementById('sync-badge');
  const sd = document.getElementById('start-date').value;
  const ed = document.getElementById('end-date').value;

  let url = '/sync/';
  const params = new URLSearchParams();
  if (sd) params.set('start_date', sd);
  if (ed) params.set('end_date', ed);
  if (params.toString()) url += '?' + params.toString();

  try {
    const r = await fetch(url, { method: 'POST' });
    if (r.status === 409) { alert('A sync is already running.'); return; }
    if (!r.ok) throw new Error(await r.text());
    btn.disabled = true;
    badge.textContent = 'Running…';
    badge.className = 'badge running';
    badge.classList.remove('hidden');
    pollSyncStatus();
  } catch (e) {
    alert('Failed to start sync: ' + e.message);
  }
}

function pollSyncStatus() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const { running } = await api('/sync/running');
      if (!running) {
        clearInterval(pollTimer);
        document.getElementById('sync-btn').disabled = false;
        const badge = document.getElementById('sync-badge');
        badge.textContent = 'Done';
        badge.className = 'badge success';
        setTimeout(() => badge.classList.add('hidden'), 4000);
        await loadAll();
      }
    } catch (_) {}
  }, 2500);
}

// ------------------------------------------------------------------ //
// Boot
// ------------------------------------------------------------------ //

async function loadAll() {
  await Promise.allSettled([
    loadKPIs(),
    loadRevenue(),
    loadBookingTrends(),
    loadTopServices(),
    loadEmployeeUtil(),
    loadRetention(),
    loadSyncLog(),
  ]);
}

// Set default date range: last 90 days
(function initDates() {
  const today = new Date();
  const past  = new Date(today);
  past.setDate(today.getDate() - 90);
  document.getElementById('end-date').value   = today.toISOString().slice(0, 10);
  document.getElementById('start-date').value = past.toISOString().slice(0, 10);
})();

loadAll();
