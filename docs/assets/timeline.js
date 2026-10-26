(() => {
  const picker = document.querySelector('#date-picker');
  if (!picker) return;
  const buttons = [...document.querySelectorAll('[data-filter]')];
  let category = '全部';
  const search = document.querySelector('#timeline-search');
  const dateFormat = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Shanghai'});
  const timeFormat = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  });
  let today = '';
  let previousToday = '';
  function refreshBeijingDate() {
    const clock = new Date();
    today = dateFormat.format(clock);
    if (![...picker.options].some(option => option.value === today)) {
      const template = document.querySelector('.day-section');
      const section = template.cloneNode(true);
      section.dataset.date = today;
      section.querySelector('.day-heading h2').textContent = today;
      section.querySelector('.day-heading span').textContent = '已更新 0 / 10 个时段 · 北京时间（UTC+8）';
      section.querySelector('.progress-track span').style.width = '0%';
      section.querySelectorAll('.timeline-row').forEach(row => {
        row.className = 'timeline-row pending';
        row.hidden = false;
        row.querySelector('h2').textContent = row.dataset.label;
        row.querySelector('.timeline-card > p').textContent = '按北京时间计划发布，有效内容通过检查后更新。';
        row.querySelectorAll('.read-link, .publication-time').forEach(element => element.remove());
      });
      template.before(section);
      const option = document.createElement('option');
      option.value = today;
      picker.prepend(option);
    }
    [...picker.options].forEach(option => {
      option.textContent = option.value + (option.value === today ? ' · 今天' : '');
    });
    if (!previousToday || (previousToday !== today && picker.value === previousToday)) picker.value = today;
    previousToday = today;
    const time = timeFormat.format(clock);
    document.querySelectorAll('.day-section').forEach(section => {
      section.querySelectorAll('.timeline-row.pending').forEach(row => {
        row.querySelector('.status').textContent = section.dataset.date === today
          ? (time < row.dataset.time ? '未到发布时间' : '等待有效内容') : '本日未发布';
      });
    });
  }
  function update() {
    document.querySelector('#timeline-heading').textContent = picker.value === today
      ? '今日技术时间线' : `${picker.value} · 历史时间线`;
    document.querySelector('#timezone-note').textContent = picker.value === today
      ? '全部时间为北京时间（UTC+8）。左侧为计划时间，实际发布时间见文章卡片。'
      : `正在浏览 ${picker.value} 的历史归档，不是今天提前发布的内容。全部时间为北京时间（UTC+8）。`;
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
  refreshBeijingDate();
  const requested = new URLSearchParams(location.search).get('date');
  if ([...picker.options].some(o => o.value === requested)) picker.value = requested;
  update();
  setInterval(() => { refreshBeijingDate(); update(); }, 60000);
})();
