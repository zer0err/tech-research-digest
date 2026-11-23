import {dailyReceiptPlan, slotStatus} from './slot-status.mjs?v=2';
import {dateInZone, executionZone, plannedInstant} from './time-display.mjs';

(() => {
  const archive = document.querySelector('#latest');
  if (!archive) return;

  const picker = archive.querySelector('#date-picker');
  const search = archive.querySelector('#timeline-search');
  const empty = archive.querySelector('#archive-no-results');
  const results = [...archive.querySelectorAll('.archive-result')];

  function update() {
    if (!picker || !search || !empty) return;
    const query = search.value.trim().toLowerCase();
    results.forEach(result => {
      result.hidden = result.dataset.date !== picker.value || !result.textContent.toLowerCase().includes(query);
    });
    empty.hidden = results.some(result => !result.hidden);
    empty.textContent = picker.value ? '所选日期没有匹配结果。' : '该日期没有已发布日报。';
  }

  if (picker && search) {
    picker.addEventListener('change', update);
    search.addEventListener('input', update);
    const requested = new URLSearchParams(location.search).get('date');
    if (requested && /^\d{4}-\d{2}-\d{2}$/.test(requested)) {
      picker.value = requested;
      archive.open = true;
    }
    update();
  }

  function openHashTarget() {
    if (location.hash === '#latest') archive.open = true;
  }
  openHashTarget();
  window.addEventListener('hashchange', openHashTarget);
  // A repeated click should reopen the disclosure even if the hash has not changed.
  document.querySelector('.site-header a[href="index.html#latest"]')?.addEventListener('click', () => {
    archive.open = true;
  });

  async function refreshReceipt() {
    const line = document.querySelector('[data-status-date]');
    if (!line) return;
    const now = new Date();
    const day = dateInZone(now, executionZone);
    line.hidden = Boolean(line.dataset.lastPublishedDate && line.dataset.lastPublishedDate >= day);
    if (line.hidden) return;
    const planned = dailyReceiptPlan(line.dataset, day);
    if (!planned) return;
    try {
      const response = await fetch('slot-status.json', {cache: 'no-store'});
      if (!response.ok) return;
      const receipts = await response.json();
      const record = receipts[day + ':daily_report'];
      line.textContent = slotStatus(record, plannedInstant(day, planned), now);
    } catch { /* Leave the static status in place if the receipt cannot be read. */ }
  }
  refreshReceipt();
})();
