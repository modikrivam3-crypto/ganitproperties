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
  if (p.contact_number && p.contact_number !== 'null' && p.contact_number !== 'None') meta.push(`<span class="card-meta-item"><span>📞</span>${escH(p.contact_number)}</span>`);

  const priceHtml = p.price
    ? `<div class="card-price">${escH(p.price)}</div>`
    : `<div class="card-price no-price">Price not listed</div>`;

  const hasUrl = p.source_url && p.source_url.startsWith('http');

  // Determine best phone number to use: phone field > contact_number
  const phoneNum = (p.phone && p.phone !== 'null' && p.phone !== 'None') ? p.phone : '';
  const contactName = (p.contact_name && p.contact_name !== 'null' && p.contact_name !== 'None') ? p.contact_name : '';
  const contactNum = (p.contact_number && p.contact_number !== 'null' && p.contact_number !== 'None') ? p.contact_number : '';

  // Contact name line
  const contactNameHtml = contactName
    ? `<div class="card-contact-name"><span>👤</span> ${escH(contactName)}</div>`
    : '';

  // Contact display: show number if available, otherwise "Not publicly available"
  let contactDisplayHtml = '';
  if (phoneNum) {
    contactDisplayHtml = `<div class="card-contact-info"><span>📞</span> Contact: ${escH(phoneNum)}</div>`;
  } else if (contactNum && !phoneNum) {
    contactDisplayHtml = `<div class="card-contact-info"><span>📞</span> Contact: ${escH(contactNum)}</div>`;
  } else {
    contactDisplayHtml = `<div class="card-contact-info card-contact-info--na"><span>📞</span> Contact: Not publicly available</div>`;
  }

  // Contact buttons: if phone exists, show Call & WhatsApp
  let contactButtonsHtml = '';
  if (phoneNum) {
    const cleanNum = phoneNum.replace(/[\s\-\(\)\+]/g, '');
    const isIndian = /^(\+?91[-\s]?)?[6-9]\d{9}$/.test(cleanNum) || /^[6-9]\d{9}$/.test(cleanNum);
    const dialNum = isIndian ? cleanNum.replace(/^0+/, '') : cleanNum;
    const fullTel = dialNum.startsWith('+') ? dialNum : `+91${dialNum}`;
    const waNum = isIndian ? `91${dialNum.replace(/^91/, '')}` : dialNum;

    contactButtonsHtml = `<div class="card-contact-buttons">
      <a href="tel:${fullTel}" class="btn-contact btn-call">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
        </svg>
        Call
      </a>
      ${isIndian ? `<a href="https://wa.me/${waNum}" target="_blank" rel="noopener noreferrer" class="btn-contact btn-whatsapp">
        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
          <path d="M12 0C5.373 0 0 5.373 0 12c0 2.545.792 4.904 2.148 6.825L1.46 23.08l4.328-1.36A11.94 11.94 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.952 0-3.79-.572-5.32-1.548l-.381-.227-2.685.843.84-2.79-.204-.404A9.96 9.96 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/>
        </svg>
        WhatsApp
      </a>` : ''}
    </div>`;
  }

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
    ${contactNameHtml}
    ${contactDisplayHtml}
    ${contactButtonsHtml}
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

const SOURCE_ORDER = ['MagicBricks','99acres','Housing.com','CommonFloor','NoBroker','Google Search','Google API','Bing API','SerpAPI'];

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

// ── Import Modal ──────────────────────────────────────────────────────────────

function showImportModal() {
  document.getElementById('importModal').classList.add('visible');
}

function hideImportModal() {
  document.getElementById('importModal').classList.remove('visible');
  document.getElementById('importResult').style.display = 'none';
}

function switchImportTab(tab) {
  document.querySelectorAll('.import-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.import-panel').forEach(p => p.classList.remove('active'));
  document.querySelector(`.import-tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`panel-${tab}`).classList.add('active');
  document.getElementById('importResult').style.display = 'none';
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  const nameEl = document.getElementById('selectedFileName');
  if (file) {
    nameEl.textContent = file.name;
    nameEl.style.display = 'inline';
  } else {
    nameEl.textContent = '';
    nameEl.style.display = 'none';
  }
}

async function uploadCSV() {
  const fileInput = document.getElementById('csvFileInput');
  const file = fileInput.files[0];
  if (!file) {
    showToast('Please select a CSV file first', 'error');
    return;
  }

  const btn = document.getElementById('csvUploadBtn');
  btn.disabled = true;
  btn.textContent = 'Importing…';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/import/csv', { method: 'POST', body: formData });
    const data = await res.json();
    const resultDiv = document.getElementById('importResult');
    resultDiv.style.display = 'block';
    if (data.error) {
      resultDiv.innerHTML = `<span class="import-error">❌ ${escH(data.error)}</span>`;
    } else {
      resultDiv.innerHTML = `<span class="import-success">✓ ${data.added} added, ${data.dupes} duplicates skipped, ${data.skipped} skipped</span>`;
      loadStats();
      loadProperties();
      fileInput.value = '';
      document.getElementById('selectedFileName').textContent = '';
    }
  } catch(e) {
    showToast('Import failed', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Import CSV';
  }
}

async function pasteCSV() {
  const textarea = document.getElementById('csvPasteInput');
  const csvText = textarea.value.trim();
  if (!csvText) {
    showToast('Please paste CSV data first', 'error');
    return;
  }

  const btn = document.getElementById('csvPasteBtn');
  btn.disabled = true;
  btn.textContent = 'Importing…';

  try {
    const res = await fetch('/api/import/paste', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csv_text: csvText }),
    });
    const data = await res.json();
    const resultDiv = document.getElementById('importResult');
    resultDiv.style.display = 'block';
    if (data.error) {
      resultDiv.innerHTML = `<span class="import-error">❌ ${escH(data.error)}</span>`;
    } else {
      resultDiv.innerHTML = `<span class="import-success">✓ ${data.added} added, ${data.dupes} duplicates skipped, ${data.skipped} skipped</span>`;
      loadStats();
      loadProperties();
    }
  } catch(e) {
    showToast('Import failed', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Import Pasted Data';
  }
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
  return String(s).replace(/&/g,'&').replace(/</g,'<').replace(/>/g,'>').replace(/"/g,'"');
}