// Article reading enhancements are progressively applied only to canonical issue sections.
const headingSelector = 'h2,h3,h4,h5,h6';
const referenceLabel = /^\s*\[([1-9]\d*)\]\s+/;

export function strictHttps(url) {
  if (typeof url !== 'string' || /\s/.test(url)) return false;
  try {
    const value = new URL(url);
    return value.protocol === 'https:' && !value.username && !value.password;
  } catch {
    return false;
  }
}

export function legacyReferenceCount(rows, numbered) {
  if (!rows.length) return 0;
  return rows.every((row, index) => {
    const printed = row.text.match(referenceLabel);
    return row.urls.length === 1 && strictHttps(row.urls[0]) &&
      (numbered ? !printed || Number(printed[1]) === index + 1 : Number(printed?.[1]) === index + 1);
  }) && new Set(rows.map(row => row.urls[0])).size === rows.length ? rows.length : 0;
}

function idAvailable(id) {
  return !document.getElementById(id);
}

export function addStableHeadingIds(headings) {
  headings.forEach((heading, index) => {
    const legacyId = 'section-' + index;
    if (!heading.id && idAvailable(legacyId)) {
      heading.id = legacyId;
    } else if (heading.id !== legacyId && idAvailable(legacyId)) {
      const anchor = document.createElement('span');
      anchor.id = legacyId;
      anchor.className = 'article-anchor-alias';
      anchor.setAttribute('aria-hidden', 'true');
      heading.before(anchor);
    }
  });
}

function safeLegacyTargets(section, heading, refs) {
  let rows, elements;
  const numbered = refs.tagName === 'OL' && !refs.hasAttribute('reversed') &&
    (!refs.hasAttribute('start') || refs.getAttribute('start') === '1') &&
    Array.from(refs.children).every(li => li.tagName === 'LI' && !li.hasAttribute('value') && !li.querySelector('ol,ul'));
  if (numbered) {
    elements = Array.from(refs.children);
    rows = elements.map(li => ({
      text: li.textContent,
      urls: [...li.querySelectorAll('a[href]')].map(a => a.getAttribute('href')),
    }));
  } else if (refs.tagName === 'P' && !refs.querySelector(':scope > :not(a):not(br)')) {
    rows = [{text: '', urls: []}];
    elements = [];
    for (const node of refs.childNodes) {
      if (node.nodeType === 3) rows.at(-1).text += node.textContent;
      else if (node.tagName === 'BR') rows.push({text: '', urls: []});
      else if (node.tagName === 'A') {
        rows.at(-1).urls.push(node.getAttribute('href'));
        elements.push(node);
      }
    }
    if (rows.length !== elements.length) return [];
  } else return [];

  // No heuristic against an incomplete notes block; it must be the last section block.
  if (refs.nextElementSibling || !legacyReferenceCount(rows, numbered)) return [];
  const ids = elements.map((target, index) => target.id || section.id + '-source-' + (index + 1));
  if (new Set(ids).size !== ids.length ||
      ids.some((id, index) => document.getElementById(id) && document.getElementById(id) !== elements[index])) return [];
  elements.forEach((target, index) => { target.id = ids[index]; });
  refs.classList.add('article-reference-list');
  heading.classList.add('article-reference-heading');
  return ids;
}

function explicitTargets(section, refs) {
  const ids = [...refs.children].map((target, index) => {
    const link = target.querySelector('a[href]');
    const expected = section.id + '-source-' + (index + 1);
    return target.tagName === 'LI' && target.id === expected && document.getElementById(expected) === target &&
      strictHttps(link?.getAttribute('href')) ? expected : '';
  });
  return ids.length && ids.every(Boolean) ? ids : [];
}

function scopedCitations(section) {
  const headings = [...section.querySelectorAll(':scope > :is(h2,h3,h4,h5,h6)')];
  const found = headings.filter(heading => heading.textContent.trim() === '参考资料');
  // Multiple/unknown reference blocks are deliberately left as plain text.
  if (found.length !== 1) return;
  const heading = found[0];
  const refs = heading.nextElementSibling;
  if (!refs) return;
  const ids = refs.classList.contains('article-reference-list') ? explicitTargets(section, refs) :
    safeLegacyTargets(section, heading, refs);
  if (!ids.length) return;

  // Link only text nodes in prose before the references, never links or code.
  const walker = document.createTreeWalker(section, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const parent = node.parentElement;
    if (!parent || parent.closest('a,code,pre,script,style') ||
        !(node.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING) || heading.contains(node)) continue;
    const matches = [...node.data.matchAll(/\[([1-9]\d*)\]/g)].filter(match => ids[Number(match[1]) - 1]);
    if (!matches.length) continue;
    const replacement = document.createDocumentFragment();
    let end = 0;
    for (const match of matches) {
      replacement.append(node.data.slice(end, match.index));
      const link = document.createElement('a');
      link.className = 'article-citation';
      link.href = '#' + ids[Number(match[1]) - 1];
      link.textContent = match[0];
      link.setAttribute('aria-label', '本节来源 ' + match[1]);
      replacement.append(link);
      end = match.index + match[0].length;
    }
    replacement.append(node.data.slice(end));
    node.replaceWith(replacement);
  }
}

function stackEvidence(table) {
  if (table.caption || table.tFoot || table.querySelector('table,[colspan],[rowspan],colgroup') ||
      table.tHead?.rows.length !== 1 || table.tBodies.length !== 1) return;
  const columns = [...table.tHead.rows[0].cells];
  const rows = [...table.tBodies[0].rows];
  if (columns.length < 2 || !columns.every(col => col.tagName === 'TH' && col.textContent.trim()) ||
      !rows.length || rows.some(row => row.cells.length !== columns.length)) return;
  // Keep the original cell nodes' descendants, preserving text, links and IDs.
  const group = document.createElement('div');
  group.className = 'article-evidence';
  if (table.hasAttribute('id')) group.id = table.id;
  for (const row of rows) {
    const card = document.createElement('section');
    card.className = 'article-evidence-row';
    const cells = [...row.cells];
    const title = document.createElement('p');
    title.className = 'article-evidence-title';
    title.append(...cells[0].childNodes);
    if (cells[0].id) title.id = cells[0].id;
    if (row.id) card.id = row.id;
    const list = document.createElement('dl');
    for (let index = 1; index < columns.length; index++) {
      const term = document.createElement('dt');
      term.textContent = columns[index].textContent.trim();
      const value = document.createElement('dd');
      value.append(...cells[index].childNodes);
      if (cells[index].id) value.id = cells[index].id;
      list.append(term, value);
    }
    card.append(title, list);
    group.append(card);
  }
  table.replaceWith(group);
}

function addDirectory(articleBody, sections) {
  const toc = document.createElement('details');
  toc.className = 'article-directory article-issue-directory';
  const summary = document.createElement('summary');
  summary.textContent = '本期目录';
  const count = document.createElement('span');
  count.textContent = sections.length + ' 节';
  summary.append(count);
  const nav = document.createElement('nav');
  nav.setAttribute('aria-label', '本期目录');
  const list = document.createElement('ol');
  for (const section of sections) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = '#' + section.id;
    link.textContent = section.querySelector(headingSelector)?.textContent.trim() || section.id;
    item.append(link);
    list.append(item);
  }
  nav.append(list);
  toc.append(summary, nav);
  articleBody.before(toc);
}

export function enhanceReading(article, stylesheet) {
  const body = article.querySelector('.article-body');
  const sections = body && [...body.querySelectorAll(':scope > section[id^="edition-"]')];
  if (!sections?.length || sections.some(section => !/^edition-[1-9]\d*$/.test(section.id))) return false;
  addStableHeadingIds([...body.querySelectorAll('h2')]);
  const styles = document.createElement('link');
  styles.rel = 'stylesheet';
  styles.href = stylesheet;
  document.head.append(styles);
  article.closest('.article-layout').classList.add('article-reading');
  const title = article.querySelector('h1');
  const meta = article.parentElement.querySelector('.article-meta');
  const back = meta?.querySelector('.back-link');
  if (back) {
    const href = new URL(back.getAttribute('href'), document.baseURI);
    href.hash = 'latest';
    back.href = href.href;
    back.textContent = '← 返回日报归档';
    article.prepend(back);
    const bottom = document.createElement('p');
    bottom.className = 'article-bottom-return';
    bottom.append(back.cloneNode(true));
    body.after(bottom);
  }
  addDirectory(body, sections);
  const first = sections[0];
  const lead = [...first.children].find(child =>
    child.matches(headingSelector) && /^(本期结论|本期要点|本时段要点|核心判断)$/.test(child.textContent.trim()));
  const leadingList = lead?.nextElementSibling?.matches('ol,ul') ? lead.nextElementSibling : null;
  const takeaway = leadingList?.firstElementChild;
  for (const section of sections) {
    scopedCitations(section);
    section.querySelectorAll('table').forEach(stackEvidence);
  }
  if (takeaway?.tagName === 'LI' && takeaway.textContent.trim() && takeaway.textContent.length < 280) {
    takeaway.classList.add('article-primary-takeaway');
    // Move a cited, bounded takeaway, not a guessed or duplicate summary.
    if (title && leadingList.children.length > 1 && takeaway.querySelector('.article-citation')) {
      const summary = document.createElement('div');
      summary.className = 'article-primary-summary';
      const label = document.createElement('p');
      label.className = 'article-primary-label';
      label.textContent = '本期要点';
      summary.append(label, ...takeaway.childNodes);
      if (takeaway.id) summary.id = takeaway.id;
      takeaway.remove();
      if (leadingList.tagName === 'OL') leadingList.start = leadingList.start + 1;
      title.after(summary);
    }
  }
  if (title && meta) title.after(meta);
  // Native deep links may resolve before the enhanced citation/legacy aliases exist.
  if (/^#(?:section-\d+|edition-\d+-source-\d+)$/.test(location.hash)) {
    document.getElementById(location.hash.slice(1))?.scrollIntoView({block: 'start'});
  }
  return true;
}
