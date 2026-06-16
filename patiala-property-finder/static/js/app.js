'use strict';
let currentPage = 1;
let debounceTimer = null;
let filterDebounceTimer = null;
const PER_PAGE = 24;

document.addEventListener('DOMContentLoaded', () => {
  loadFilters();
  loadStats();
  loadProperties();
});

// ── Search ───────────────────────────────────────────────────────────────────

function debounceSearch() {
  const v = document.getElementById('searchInput').value;
  document.getElementById('clearSearch').style.display = v ? 'block' : 'none';
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => { currentPage = 1; loadProperties(); }, 380);
}

function debounceFilters() {
  clearTimeout(filterDebounceTimer);
  filterDebounceTimer = setTimeout(() => { currentPage = 1; loadProperties(); }, 500);
}

function clearSearch() {
  document.getElementById('searchInput').value = '';
  document.getElementById('clearSearch').style.display = 'none';
  currentPage = 1; loadProperties();
}

function applyFilters() { currentPage = 1; loadProperties(); }

function clearFilters() {
  ['searchInput','fType','fPropType','fSource','fLocation'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['minPrice','maxPrice','minArea','maxArea'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('clearSearch').style.display = 'none';
  currentPage = 1; loadProperties();
}

// ── Filters / Stats ──────────────────────────────────────────────────────────

async function loadFilters() {
  try {
    const res  = await fetch('/api/filters');
    const data = await res.json();

    populate('fPropType', data.property_types, 'Property Type');
    populate('fSource',   data.sources,         'All Sources');
    populate('fLocation', data.locations,        'All Localities');
  } catch(e) { console.warn('loadFilters:', e); }
}

function populate(id, items, placeholder) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const cur = sel.value;
  sel.innerHTML = `<option value="">${escH(placeholder)}</option>`;
  items.forEach(item => {
    const o = document.createElement('option');
    o.value = item; o.textContent = item;
    sel.appendChild(o);
  });
  if (cur) sel.value = cur;
}

async function loadStats() {
  try {
    const res  = await fetch('/api/stats');
    const data = await res.json();
    const chip = document.getElementById('statTotal');
    if (chip) chip.textContent = `${data.total} listings`;
  } catch(e) {}
}

// ── Load Properties ──────────────────────────────────────────────────────────

async function loadProperties() {
  const params = new URLSearchParams({
    page: currentPage,
    per_page: PER_PAGE,
  });

  const searchVal = document.getElementById('searchInput')?.value.trim();
  if (searchVal)   params.set('search',        searchVal);

  const fType = document.getElementById('fType')?.value;
  if (fType)       params.set('listing_type',  fType);

  const fProp = document.getElementById('fPropType')?.value;
  if (fProp)       params.set('property_type', fProp);

  const fSrc = document.getElementById('fSource')?.value;
  if (fSrc)        params.set('source',        fSrc);

  const fLoc = document.getElementById('fLocation')?.value;
  if (fLoc)        params.set('location',      fLoc);

  const minP = document.getElementById('minPrice')?.value;
  if (minP)        params.set('min_price',     minP);
  const maxP = document.getElementById('maxPrice')?.value;
  if (maxP)        params.set('max_price',     maxP);

  const minA = document.getElementById('minArea')?.value;
  if (minA)        params.set('min_area',      minA);
  const maxA = document.getElementById('maxArea')?.value;
  if (maxA)        params.set('max_area',      maxA);

  showLoading(true);
  try {
    const res  = await fetch(`/api/properties?${params}`);
    const data = await res.json();
    renderProperties(data);
    renderPagination(data);
    updateMeta(data);
  } catch(e) {
    showToast('Failed to load listings', 'error');
  } finally {
    showLoading(false);
  }
}

// ── Render Cards ─────────────────────────────────────────────────────────────

function renderProperties(data) {
  const grid  = document.getElementById('propertyGrid');
  const empty = document.getElementById('emptyState');
  grid.innerHTML = '';
  if (!data.properties?.length) { empty.style.display = 'block'; return; }
  empty.style.display = 'none';
  data.properties.forEach((p, i) => grid.appendChild(createCard(p, i)));
}

function createCard(p, i) {
  const el = document.createElement('article');
  el.className = 'property-card';
  el.style.animationDelay = `${i * 25}ms`;

  const ltClass  = p.listing_type === 'Rent' ? 'badge-rent' : 'badge-buy';
  const ltBadge  = p.listing_type ? `<span class="badge ${ltClass}">${escH(p.listing_type)}</span>` : '';
  const typeBadge= p.property_type ? `<span class="badge badge-type">${escH(p.property_type)}</span>` : '';
  const srcBadge = p.source_name   ? `<span class="badge badge-source">${escH(p.source_name)}</span>` : '';

  const meta = [];
  if (p.location) meta.push(`<span class="card-meta-item"><span>📍</span>${escH(p.location)}${p.location !== 'Patiala' ? ', Patiala' : ''}</span>`);
  if (p.area)     meta.push(`<span class="card-meta-item"><span>📐</span>${escH(p.area)}</span>`);

  const priceHtml = p.price
    ? `<div class="card-price">${escH(p.price)}</div>`
    : `<div class="card-price no-price">Price not listed</div>`;

  const hasUrl = p.source_url && p.source_url.startsWith('http');
  const linkHtml = hasUrl
    ? `<a href="${escH(p.source_url)}" target="_blank" rel="noopener noreferrer" class="btn-listing">
         View listing
         <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
           <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
           <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
         </svg>
       </a>`
    : `<span class="btn-listing btn-listing--unavailable">Link not available</span>`;

  const dateStr = p.added_at
    ? new Date(p.added_at).toLocaleDateString('en-IN',{day:'numeric',month:'short'})
    : '';

  el.innerHTML = `
    <div class="card-top">
      <div class="card-badges">${ltBadge}${typeBadge}${srcBadge}</div>
      <button class="card-delete" title="Remove" onclick="deleteListing(${p.id},this)">✕</button>
    </div>
    <h2 class="card-title">${escH(p.title)}</h2>
    ${priceHtml}
    ${meta.length ? `<div class="card-meta">${meta.join('')}</div>` : ''}
    ${p.summary ? `<p class="card-summary">${escH(p.summary)}</p>` : ''}
    <div class="card-footer">
      <span class="card-source-info">${dateStr ? dateStr : ''}</span>
      ${linkHtml}
    </div>`;
  return el;
}

// ── Pagination ────────────────────────────────────────────────────────────────

function renderPagination(data) {
  const c = document.getElementById('pagination');
  c.innerHTML = '';
  if (data.pages <= 1) return;

  const add = (label, pg, disabled, active) => {
    const b = document.createElement('button');
    b.className = 'page-btn' + (active ? ' active' : '');
    b.textContent = label;
    b.disabled = disabled;
    b.onclick = () => { currentPage = pg; loadProperties(); window.scrollTo({top:0,behavior:'smooth'}); };
    c.appendChild(b);
  };

  add('← Prev', currentPage-1, currentPage===1, false);
  const s = Math.max(1, currentPage-2);
  const e = Math.min(data.pages, currentPage+2);
  for (let pg=s; pg<=e; pg++) add(pg, pg, false, pg===currentPage);
  add('Next →', currentPage+1, currentPage===data.pages, false);
}

function updateMeta(data) {
  const meta = document.getElementById('resultsMeta');
  const cnt  = document.getElementById('resultsCount');
  if (!data.total) { meta.style.display='none'; return; }
  meta.style.display = 'block';
  const from = (data.page-1)*data.per_page+1;
  const to   = Math.min(data.page*data.per_page, data.total);
  cnt.textContent = `Showing ${from}–${to} of ${data.total} listing${data.total!==1?'s':''}`;
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteListing(id, btn) {
  if (!confirm('Remove this listing from your local database?')) return;
  try {
    await fetch(`/api/property/${id}`, {method:'DELETE'});
    const card = btn.closest('.property-card');
    card.style.transition = 'opacity .3s,transform .3s';
    card.style.opacity = '0'; card.style.transform = 'scale(.95)';
    setTimeout(() => { card.remove(); loadStats(); }, 300);
    showToast('Listing removed');
  } catch(e) { showToast('Could not remove listing','error'); }
}

// ── Refresh ───────────────────────────────────────────────────────────────────

const SOURCE_ORDER = ['MagicBricks','99acres','Housing.com','CommonFloor','NoBroker','Google Search'];

async function startRefresh() {
  const modal = document.getElementById('refreshModal');
  const btn   = document.getElementById('refreshBtn');
  const prog  = document.getElementById('progressBar');
  const result= document.getElementById('modalResult');

  // Reset modal UI
  result.style.display = 'none';
  prog.style.width = '0%';
  SOURCE_ORDER.forEach(name => setSourceStatus(name, 'pending', '', ''));
  modal.classList.add('visible');
  btn.classList.add('loading');

  // Animate progress bar while waiting
  let pct = 0;
  const progInterval = setInterval(() => {
    pct = Math.min(pct + 1.5, 85);
    prog.style.width = pct + '%';
  }, 800);

  // Mark all as fetching sequentially (visual only — actual fetch is synchronous)
  SOURCE_ORDER.forEach(name => setSourceStatus(name, 'fetching', '', ''));

  try {
    const res  = await fetch('/api/refresh', {method:'POST'});
    const data = await res.json();

    clearInterval(progInterval);
    prog.style.width = '100%';

    // Update source status from response
    const sources = data.sources || {};
    SOURCE_ORDER.forEach(name => {
      const s = sources[name];
      if (s) {
        setSourceStatus(name, s.status, s.message, s.count > 0 ? `${s.count} fetched` : '');
      } else {
        setSourceStatus(name, 'failed', 'No response', '');
      }
    });

    result.style.display = 'block';
    result.innerHTML = data.added > 0
      ? `<strong>✓ ${data.added}</strong> new listing${data.added!==1?'s':''} added · ${data.dupes||0} duplicates removed`
      : `No new listings found this time`;

    loadStats();
    loadFilters();
    loadProperties();

    setTimeout(() => {
      modal.classList.remove('visible');
      btn.classList.remove('loading');
      prog.style.width = '0%';
      showToast(data.added > 0 ? `✓ ${data.added} new listings added` : 'No new listings', data.added > 0 ? 'success' : '');
    }, 3500);

  } catch(e) {
    clearInterval(progInterval);
    modal.classList.remove('visible');
    btn.classList.remove('loading');
    showToast('Refresh failed. Please try again.', 'error');
  }
}

function setSourceStatus(name, status, message, countText) {
  const row = document.querySelector(`.source-row[data-source="${name}"]`);
  if (!row) return;
  const badge = row.querySelector('.src-badge');
  const count = row.querySelector('.src-count');
  const labels = {pending:'Pending',fetching:'Fetching…',completed:'Done',blocked:'Blocked',failed:'Failed'};
  if (badge) {
    badge.className = `src-badge badge-${status}`;
    badge.textContent = labels[status] || status;
  }
  if (count) count.textContent = countText || message || '';
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function showLoading(v) {
  document.getElementById('loadingState').style.display = v ? 'block' : 'none';
  if (v) document.getElementById('propertyGrid').innerHTML = '';
}

function showToast(msg, type='') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (type ? ' '+type : '');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.className = 'toast'; }, 3400);
}

function escH(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
