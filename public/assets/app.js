import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

const navigation = document.querySelector('#navigation');
const content = document.querySelector('#content');
const count = document.querySelector('#page-count');
const menuButton = document.querySelector('.menu-button');
const sidebar = document.querySelector('#sidebar');
const themeToggle = document.querySelector('#theme-toggle');

let pages = [];
const defaultTexts = {
  site_title: 'LearningSite | למידה חכמה', brand_prefix: 'Learning', brand_accent: 'Site', brand_home_label: 'דף הבית של LearningSite',
  tagline: 'הנדסת תוכנה וסייבר · לומדים, מתרגלים, מבינים', menu_label: 'תכנים ☰', theme_light_label: '☀ מצב בהיר', theme_dark_label: '🌙 מצב כהה', learning_path_label: 'מסלול הלמידה', navigation_label: 'ניווט בתכני הלמידה', loading_content: 'טוען תכנים…',
  page_count: '{count} עמודים זמינים', empty_title: 'עוד אין תכנים', empty_description: 'צרו את העמוד הראשון דרך תוכנת העורך. היא תעדכן את האינדקס אוטומטית.',
  loading_page: 'טוען את השיעור…', load_error_title: 'לא הצלחנו לטעון את העמוד', load_error_description: 'ודאו שהקובץ {file} קיים, ושהאתר מופעל דרך שרת מקומי.',
  missing_index_title: 'חסר קובץ אינדקס', missing_index_description: 'פתחו את תוכנת העורך ושמרו עמוד כדי ליצור את האינדקס אוטומטית.',
};
let siteTexts = { ...defaultTexts };

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' })[char]);
}

function setTheme(theme) {
  const light = theme === 'light';
  document.body.classList.toggle('light-theme', light);
  themeToggle.setAttribute('aria-pressed', String(light));
  themeToggle.textContent = text(light ? 'theme_dark_label' : 'theme_light_label');
  try { localStorage.setItem('site-theme', light ? 'light' : 'dark'); } catch { /* Storage can be unavailable. */ }
}

function text(key, replacements = {}) {
  return Object.entries(replacements).reduce((value, [name, replacement]) => value.replaceAll(`{${name}}`, replacement), siteTexts[key] ?? defaultTexts[key] ?? '');
}

function applySiteTexts() {
  document.title = text('site_title');
  document.querySelector('#site-title').textContent = text('site_title');
  document.querySelector('#brand-home').setAttribute('aria-label', text('brand_home_label'));
  document.querySelector('#brand-name').innerHTML = `${escapeHtml(text('brand_prefix'))}<span>${escapeHtml(text('brand_accent'))}</span>`;
  document.querySelector('#tagline').textContent = text('tagline');
  menuButton.textContent = text('menu_label');
  themeToggle.textContent = text(document.body.classList.contains('light-theme') ? 'theme_dark_label' : 'theme_light_label');
  document.querySelector('#learning-path-label').textContent = text('learning_path_label');
  navigation.setAttribute('aria-label', text('navigation_label'));
  count.textContent = text('loading_content');
}

async function loadSiteTexts() {
  try {
    const response = await fetch('site-texts.json');
    if (!response.ok) throw new Error();
    siteTexts = { ...defaultTexts, ...await response.json() };
  } catch { siteTexts = { ...defaultTexts }; }
  applySiteTexts();
}

function inline(text) {
  return escapeHtml(text)
    .replace(/!\[([^\]]*)\]\(([^ )]+)\)/g, '<img src="$2" alt="$1" loading="lazy">')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\(([^ )]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

function markdownToHtml(markdown) {
  const lines = markdown.replace(/\r/g, '').split('\n');
  let result = '', list = null, code = false, codeLanguage = '', codeLines = [], direction = null;
  const closeList = () => { if (list) { result += `</${list}>`; list = null; } };
  const closeDirection = () => { if (direction) { result += '</div>'; direction = null; } };
  for (const line of lines) {
    if (line.startsWith('```')) {
      if (code) {
        const source = escapeHtml(codeLines.join('\n'));
        result += codeLanguage === 'mermaid' ? `<pre class="mermaid">${source}</pre>` : `<pre><code>${source}</code></pre>`;
        code = false; codeLanguage = ''; codeLines = [];
      } else { closeList(); code = true; codeLanguage = line.slice(3).trim().toLowerCase(); }
      continue;
    }
    if (code) { codeLines.push(line); continue; }
    const directionStart = line.match(/^:::(rtl|ltr)\s*$/i);
    if (directionStart) { closeList(); closeDirection(); direction = directionStart[1].toLowerCase(); result += `<div class="markdown-direction" dir="${direction}">`; continue; }
    if (line.trim() === ':::') { closeList(); closeDirection(); continue; }
    const heading = line.match(/^(#{1,3})\s+(.+)$/); const unordered = line.match(/^[-*+]\s+(.+)$/); const ordered = line.match(/^\d+\.\s+(.+)$/);
    if (heading) { closeList(); const level = heading[1].length; result += `<h${level}>${inline(heading[2])}</h${level}>`; continue; }
    if (unordered || ordered) { const kind = unordered ? 'ul' : 'ol'; if (list !== kind) { closeList(); result += `<${kind}>`; list = kind; } result += `<li>${inline((unordered || ordered)[1])}</li>`; continue; }
    closeList(); if (!line.trim()) continue;
    if (line.startsWith('> ')) result += `<blockquote>${inline(line.slice(2))}</blockquote>`;
    else if (line === '---') result += '<hr>';
    else result += `<p>${inline(line)}</p>`;
  }
  closeList(); closeDirection(); return result;
}

async function renderMermaid() {
  const diagrams = content.querySelectorAll('.mermaid');
  if (!diagrams.length) return;
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: document.body.classList.contains('light-theme') ? 'default' : 'dark', flowchart: { useMaxWidth: true } });
  try { await mermaid.run({ nodes: diagrams, suppressErrors: true }); }
  catch { diagrams.forEach(diagram => diagram.classList.add('mermaid-error')); }
}

function renderNavigation() {
  const tree = { children: new Map(), pages: [] };
  pages.forEach(page => {
    const folders = page.slug.split('/').slice(0, -1);
    let node = tree;
    folders.forEach(folder => {
      if (!node.children.has(folder)) node.children.set(folder, { children: new Map(), pages: [] });
      node = node.children.get(folder);
    });
    node.pages.push(page);
  });

  const pageLink = page => `<a class="nav-link" href="#/${encodeURIComponent(page.slug)}" data-slug="${escapeHtml(page.slug)}">${escapeHtml(page.title)}</a>`;
  const firstOrder = node => Math.min(
    ...node.pages.map(page => page.order),
    ...[...node.children.values()].map(firstOrder),
    Number.POSITIVE_INFINITY,
  );
  const branch = (node, depth = 0, lineage = []) => {
    const entries = [
      ...[...node.children].map(([name, child]) => ({ type: 'folder', name, child, order: firstOrder(child) })),
      ...node.pages.map(page => ({ type: 'page', page, order: page.order })),
    ].sort((first, second) => first.order - second.order);
    return entries.map(entry => {
      if (entry.type === 'page') return pageLink(entry.page);
      const currentLineage = [...lineage, entry.name];
      const id = `topic-${encodeURIComponent(currentLineage.join('/')).replace(/%/g, '_')}`;
      const inner = branch(entry.child, depth + 1, currentLineage);
      return `<section class="nav-group depth-${depth}"><button class="nav-group-title" type="button" aria-expanded="true" aria-controls="${id}"><span class="topic-chevron">⌄</span>${escapeHtml(entry.name)}</button><div class="nav-group-children" id="${id}">${inner}</div></section>`;
    }).join('');
  };

  navigation.innerHTML = branch(tree);
  navigation.querySelectorAll('.nav-group-title').forEach(button => button.addEventListener('click', () => {
    const expanded = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', String(!expanded));
    document.getElementById(button.getAttribute('aria-controls')).hidden = expanded;
  }));
}

async function renderCurrentPage() {
  const slug = decodeURIComponent(location.hash.replace(/^#\/?/, '')) || pages[0]?.slug;
  const page = pages.find(item => item.slug === slug) || pages[0];
  document.querySelectorAll('.nav-link').forEach(link => link.classList.toggle('active', link.dataset.slug === page?.slug));
  sidebar.classList.remove('open'); menuButton.setAttribute('aria-expanded', 'false');
  if (!page) { content.innerHTML = `<article class="article empty-state"><h1>${escapeHtml(text('empty_title'))}</h1><p>${escapeHtml(text('empty_description'))}</p></article>`; return; }
  content.innerHTML = `<article class="article"><p>${escapeHtml(text('loading_page'))}</p></article>`;
  try { const response = await fetch(page.file); if (!response.ok) throw new Error(); const html = markdownToHtml(await response.text()); const title = html.match(/<h1>(.*?)<\/h1>/)?.[1] || escapeHtml(page.title); content.innerHTML = `<article class="article"><header class="article-header"><h1>${title}</h1></header>${html.replace(/<h1>.*?<\/h1>/, '')}</article>`; await renderMermaid(); content.focus(); }
  catch {
    const description = escapeHtml(text('load_error_description')).replace('{file}', `<code>${escapeHtml(page.file)}</code>`);
    content.innerHTML = `<article class="article empty-state"><h1>${escapeHtml(text('load_error_title'))}</h1><p>${description}</p></article>`;
  }
}

async function init() {
  await loadSiteTexts();
  try {
    const response = await fetch('content-index.json');
    const index = await response.json();
    pages = index
      .map((page, indexPosition) => ({ ...page, order: Number.isFinite(Number(page.order)) ? Number(page.order) : indexPosition + 1, indexPosition }))
      .sort((first, second) => first.order - second.order || first.indexPosition - second.indexPosition);
    count.textContent = text('page_count', { count: pages.length }); renderNavigation(); await renderCurrentPage();
  }
  catch { content.innerHTML = `<article class="article empty-state"><h1>${escapeHtml(text('missing_index_title'))}</h1><p>${escapeHtml(text('missing_index_description'))}</p></article>`; }
}
menuButton.addEventListener('click', () => { const open = sidebar.classList.toggle('open'); menuButton.setAttribute('aria-expanded', String(open)); });
try { setTheme(localStorage.getItem('site-theme') || 'dark'); } catch { setTheme('dark'); }
themeToggle.addEventListener('click', () => { setTheme(document.body.classList.contains('light-theme') ? 'dark' : 'light'); renderCurrentPage(); });
window.addEventListener('hashchange', renderCurrentPage); init();
