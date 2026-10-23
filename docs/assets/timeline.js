(() => {
  const picker = document.querySelector('#date-picker');
  if (!picker) return;
  const buttons = [...document.querySelectorAll('[data-filter]')];
  let category = '全部';
  const search = document.querySelector('#timeline-search');
  function update() {
    document.querySelectorAll('.magazine-lead').forEach(section => {
      section.hidden = section.dataset.date !== picker.value;
    });
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
  const menu = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('#main-nav');
  if (menu && navigation) {
    const close = () => {menu.setAttribute('aria-expanded', 'false'); navigation.classList.remove('menu-open');};
    menu.addEventListener('click', () => {
      const open = menu.getAttribute('aria-expanded') !== 'true';
      menu.setAttribute('aria-expanded', String(open));
      navigation.classList.toggle('menu-open', open);
    });
    navigation.addEventListener('click', event => {if (event.target.closest('a')) close();});
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {close(); menu.focus();}
    });
  }
  const progress = document.querySelector('.reading-progress');
  if (progress) {
    let scheduled = false;
    const paint = () => {
      const total = document.documentElement.scrollHeight - innerHeight;
      progress.style.width = (total > 0 ? Math.min(100, Math.max(0, scrollY / total * 100)) : 0) + '%';
      scheduled = false;
    };
    addEventListener('scroll', () => {
      if (!scheduled) {scheduled = true; requestAnimationFrame(paint);}
    }, {passive: true});
    addEventListener('resize', paint);
    paint();
  }
})();
