const search = document.querySelector('[data-tool-search]');
const filters = [...document.querySelectorAll('[data-tool-filter]')];
const cards = [...document.querySelectorAll('[data-tool-card]')];
const count = document.querySelector('[data-tool-count]');
const empty = document.querySelector('[data-tool-empty]');
const reset = document.querySelector('[data-tool-reset]');

function normalized(value) {
  return String(value || '').trim().toLocaleLowerCase('zh-CN');
}

function applyFilters() {
  const query = normalized(search?.value);
  const selected = Object.fromEntries(filters.map((control) => [control.dataset.toolFilter, control.value]));
  let visible = 0;
  for (const card of cards) {
    const matchesSearch = !query || normalized(card.dataset.search).includes(query);
    const matchesCategory = !selected.category || card.dataset.category === selected.category;
    const accessModes = String(card.dataset.access || '').split(' ');
    const matchesAccess = !selected.access || accessModes.includes(selected.access);
    const matches = matchesSearch && matchesCategory && matchesAccess;
    card.hidden = !matches;
    if (matches) visible += 1;
  }
  if (count) count.textContent = visible === cards.length ? `显示全部 ${visible} 项` : `找到 ${visible} 项`;
  if (empty) empty.hidden = visible !== 0;
}

function writeUrl() {
  const url = new URL(window.location.href);
  const values = { q: search?.value || '' };
  for (const control of filters) values[control.dataset.toolFilter] = control.value;
  for (const [name, value] of Object.entries(values)) {
    if (value) url.searchParams.set(name, value);
    else url.searchParams.delete(name);
  }
  window.history.replaceState(null, '', url);
}

function update() {
  applyFilters();
  writeUrl();
}

function clearFilters() {
  if (search) search.value = '';
  for (const control of filters) control.value = '';
  update();
  search?.focus();
}

const params = new URLSearchParams(window.location.search);
if (search) search.value = params.get('q') || '';
for (const control of filters) {
  const candidate = params.get(control.dataset.toolFilter) || '';
  control.value = [...control.options].some((option) => option.value === candidate) ? candidate : '';
}

search?.addEventListener('input', update);
for (const control of filters) control.addEventListener('change', update);
reset?.addEventListener('click', clearFilters);
document.querySelector('[data-tool-empty-reset]')?.addEventListener('click', clearFilters);

applyFilters();
