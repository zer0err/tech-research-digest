import {slotStatus} from './slot-status.mjs';
import {executionZone, timestampInZone} from './time-display.mjs';

(() => {
  const picker = document.querySelector('#date-picker');
  if (!picker) return;
  const search = document.querySelector('#timeline-search');
  const sections = [...document.querySelectorAll('.day-section')];

  function update() {
    const query = search.value.trim().toLowerCase();
    const today = [...picker.options].some(option => option.value === picker.value)
      ? picker.value
      : sections[0]?.dataset.date;
    document.querySelector('#timeline-heading').textContent = picker.value === today && picker.selectedOptions[0]?.textContent.includes('今天')
      ? '今日日报'
      : picker.value + ' · 日报';
    document.querySelector('#timezone-note').textContent = '发布时刻固定为 ' + executionZone
      + '（UTC+8）当天 09:00。页面不按阅读设备时区改写这一日期。';
    sections.forEach(section => {
      section.hidden = section.dataset.date !== picker.value;
      section.querySelectorAll('.timeline-row').forEach(row => {
        row.hidden = !row.textContent.toLowerCase().includes(query);
      });
    });
  }

  picker.addEventListener('change', update);
  search.addEventListener('input', update);
  const requested = new URLSearchParams(location.search).get('date');
  if ([...picker.options].some(option => option.value === requested)) picker.value = requested;
  update();

  async function refreshReceipts() {
    const pending = document.querySelector('.timeline-row.pending[data-slot="daily_report"]');
    if (!pending) return;
    try {
      const response = await fetch('slot-status.json', {cache: 'no-store'});
      if (!response.ok) return;
      const receipts = await response.json();
      const record = receipts[pending.dataset.date + ':daily_report'];
      const planned = pending.dataset.date + 'T09:00:00+08:00';
      pending.querySelector('.status').textContent = slotStatus(record, planned, new Date(), false);
      if (record?.updated_at) {
        pending.querySelector('.timeline-card > p').textContent = '最近检查：'
          + timestampInZone(record.updated_at, executionZone) + '。没有合格来源时不编造日报。';
      }
    } catch { /* Keep the static status when the receipt cannot be read. */ }
  }
  refreshReceipts();
})();
