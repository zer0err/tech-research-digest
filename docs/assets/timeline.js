import {visitorZone, dateInZone, timeInZone, timestampInZone, plannedInstant, localizedTitle, executionZone} from './time-display.mjs';
import {slotStatus} from './slot-status.mjs';
(() => {
  const picker = document.querySelector('#date-picker');
  if (!picker) return;
  const zone = visitorZone();
  const buttons = [...document.querySelectorAll('[data-filter]')];
  const search = document.querySelector('#timeline-search');
  const template = document.querySelector('.day-section').cloneNode(true);
  const rowTemplates = [...template.querySelectorAll('.timeline-row')];
  const sourceRows = new Map();
  document.querySelectorAll('.day-section .timeline-row').forEach(row => {
    row.dataset.originalTitle = row.querySelector('h2').textContent;
    sourceRows.set(row.dataset.executionDate + ':' + row.dataset.slot, row);
  });
  let category = '全部';
  let today = '';
  let previousToday = '';
  let receipts = {};

  function renderDates(initial = false) {
    const clock = new Date();
    today = dateInZone(clock, zone);
    const executionDay = dateInZone(clock, executionZone);
    const selected = picker.value;
    // A stale static index must still show the current execution day's plans without inventing articles.
    rowTemplates.forEach(original => {
      const key = executionDay + ':' + original.dataset.slot;
      if (sourceRows.has(key)) return;
      const row = original.cloneNode(true);
      row.className = 'timeline-row pending';
      row.dataset.executionDate = executionDay;
      row.dataset.plannedAt = plannedInstant(executionDay, row.dataset.executionTime);
      row.dataset.publishedAt = '';
      row.dataset.originalTitle = row.dataset.label;
      row.querySelector('h2').textContent = row.dataset.label;
      row.querySelector('.timeline-card > p').textContent = '有效内容通过检查后更新。';
      row.querySelectorAll('.read-link, .publication-time').forEach(element => element.remove());
      sourceRows.set(key, row);
    });
    const groups = new Map([[today, []]]);
    sourceRows.forEach(row => {
      const planned = row.dataset.plannedAt;
      const day = dateInZone(planned, zone);
      const time = row.querySelector('.time-rail time');
      time.dateTime = planned;
      time.textContent = timeInZone(planned, zone);
      time.title = '东八区执行计划：' + row.dataset.executionDate + ' ' + row.dataset.executionTime;
      row.dataset.time = time.textContent;
      if (row.dataset.publishedAt) {
        row.querySelector('h2').textContent = localizedTitle(row.dataset.originalTitle, row.dataset.publishedAt, zone);
        row.querySelector('.publication-time').textContent = '实际发布：' + timestampInZone(row.dataset.publishedAt, zone);
      } else {
        const record = receipts[row.dataset.executionDate + ':' + row.dataset.slot];
        row.querySelector('.status').textContent = slotStatus(record, planned, clock, row.dataset.executionDate < executionDay);
        row.querySelector('.timeline-card > p').textContent = record?.updated_at
          ? '任务最近检查：' + timestampInZone(record.updated_at, zone) + '。未生成文章，不代表任务仍在等待。'
          : '仅展示已通过检查的内容；没有任务记录时不推断已执行或无新增。';
      }
      if (!groups.has(day)) groups.set(day, []);
      groups.get(day).push(row);
    });
    document.querySelectorAll('.day-section').forEach(section => section.remove());
    picker.replaceChildren();
    [...groups.keys()].sort().reverse().forEach(day => {
      const rows = groups.get(day).sort((a, b) => new Date(a.dataset.plannedAt) - new Date(b.dataset.plannedAt));
      const section = template.cloneNode(true);
      section.dataset.date = day;
      section.querySelector('.day-heading h2').textContent = day;
      const completed = rows.filter(row => row.dataset.publishedAt).length;
      section.querySelector('.day-heading span').textContent = '已更新 ' + completed + ' / ' + rows.length + ' 个时段 · ' + zone;
      section.querySelector('.progress-track span').style.width = (rows.length ? completed / rows.length * 100 : 0) + '%';
      section.querySelector('.timeline').replaceChildren(...rows);
      const closed = rows.filter(row => !row.dataset.publishedAt && row.dataset.executionDate < executionDay);
      if (closed.length) {
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = '查看 ' + closed.length + ' 个未发布时段及原因';
        const list = document.createElement('ol');
        list.className = 'timeline';
        list.append(...closed);
        details.append(summary, list);
        section.append(details);
      }
      document.querySelector('#latest').append(section);
      const option = document.createElement('option');
      option.value = day;
      option.textContent = day + (day === today ? ' · 今天' : '');
      picker.append(option);
    });
    picker.value = initial || (previousToday !== today && selected === previousToday) ? today : selected;
    if (![...picker.options].some(option => option.value === picker.value)) picker.value = today;
    previousToday = today;
  }
  function update() {
    document.querySelector('#timeline-heading').textContent = picker.value === today
      ? '今日技术时间线' : picker.value + ' · 历史时间线';
    document.querySelector('#timezone-note').textContent = '显示时区：' + zone
      + '；按本地计划日期分组，实际发布时间单独标注。任务始终按东八区（UTC+8）执行。';
    document.querySelectorAll('.day-section').forEach(section => {
      section.hidden = section.dataset.date !== picker.value;
      section.querySelectorAll('.timeline-row').forEach(row => {
        row.hidden = (category !== '全部' && row.dataset.category !== category)
          || !row.textContent.toLowerCase().includes(search.value.trim().toLowerCase());
      });
    });
  }
  picker.addEventListener('change', update);
  search.addEventListener('input', update);
  buttons.forEach(button => button.addEventListener('click', () => {
    category = button.dataset.filter;
    buttons.forEach(other => other.setAttribute('aria-pressed', String(other === button)));
    update();
  }));
  renderDates(true);
  const requested = new URLSearchParams(location.search).get('date');
  if ([...picker.options].some(option => option.value === requested)) picker.value = requested;
  update();
  async function refreshReceipts() {
    try {
      const response = await fetch('slot-status.json', {cache: 'no-store'});
      if (response.ok) receipts = await response.json();
    } catch { /* Keep explicit unknown status when the network is unavailable. */ }
    renderDates(); update();
  }
  refreshReceipts();
  setInterval(refreshReceipts, 60000);
})();
