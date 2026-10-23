(() => {
  const picker = document.querySelector('#date-picker');
  if (!picker) return;
  const buttons = [...document.querySelectorAll('[data-filter]')];
  let category = '全部';
  const search = document.querySelector('#timeline-search');
  function update() {
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
    buttons.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    update();
  }));
  const requested = new URLSearchParams(location.search).get('date');
  if ([...picker.options].some(o => o.value === requested)) picker.value = requested;
  const beijingToday = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Shanghai'}).format(new Date());
  if (![...picker.options].some(o => o.value === beijingToday)) {
    const message = document.createElement('p');
    message.className = 'schedule-note';
    message.textContent = '当前显示最近一次出版记录，今日内容发布后将更新。';
    picker.closest('.timeline-toolbar').after(message);
  }
  update();
})();
