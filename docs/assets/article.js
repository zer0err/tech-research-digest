import {executionZone, timestampInZone} from './time-display.mjs';
(() => {
  const article = document.querySelector('.article-layout > article');
  if (!article) return;
  const headings = [...article.querySelectorAll('.article-body h2')];
  if (headings.length) {
    const details = document.createElement('details');
    details.className = 'article-directory';
    const summary = document.createElement('summary');
    summary.textContent = '本文目录';
    details.append(summary);
    const list = document.createElement('ul');
    headings.forEach((heading, index) => {
      heading.id = 'section-' + index;
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = '#' + heading.id;
      link.textContent = heading.textContent;
      item.append(link);
      list.append(item);
    });
    details.append(list);
    article.querySelector('.article-body').before(details);
  }
  fetch('../posts.json').then(r => {if (!r.ok) throw new Error('index unavailable'); return r.json();}).then(entries => {
    const current = entries.findIndex(e => new URL('../' + e.url, location.href).pathname === location.pathname);
    if (current < 0) return;
    const entry = entries[current];
    const dateNode = document.querySelector('.article-meta dd');
    if (dateNode) {
      dateNode.textContent = timestampInZone(entry.date, executionZone);
      dateNode.dataset.publishedAt = entry.date;
      dateNode.previousElementSibling.textContent = '发布时间';
    }
    const heading = article.querySelector('h1');
    heading.textContent = entry.title;
    document.title = heading.textContent;
    const note = document.createElement('p');
    note.className = 'disclosure';
    note.textContent = `发布时间按 ${executionZone}（UTC+8）计，不随阅读设备时区改日。`;
    heading.after(note);
    const nav = document.createElement('nav');
    nav.className = 'article-neighbors';
    [[current + 1, '上一篇'], [current - 1, '下一篇']].forEach(([index, label]) => {
      const entry = entries[index];
      if (!entry) return;
      const link = document.createElement('a');
      link.href = '../' + entry.url;
      link.textContent = label + ' · ' + entry.title;
      nav.append(link);
    });
    article.append(nav);
  }).catch(() => {});
})();
