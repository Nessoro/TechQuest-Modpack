document.addEventListener("DOMContentLoaded", function(){
/* TechQuest static community hub — no backend, no credentials stored. */
'use strict';
const REPO = 'Nessoro/TechQuest-Modpack';
const GH = `https://github.com/${REPO}`;
const ISSUES = `${GH}/issues`;
const DEFAULT_CATEGORY = 'all';
const LABELS = {bug:'bug', mod:'enhancement'};
const mods = Array.isArray(window.TQ_MODS) ? window.TQ_MODS : [];
let selectedCategory = DEFAULT_CATEGORY;
let query = '';
let expanded = false;

function create(tag, className, textValue) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (textValue != null) node.textContent = textValue;
  return node;
}

function initLinks() {
  document.querySelectorAll('[data-repo-link]').forEach(a=>a.href=GH);
  document.querySelectorAll('[data-issues-link]').forEach(a=>a.href=ISSUES);
  document.querySelector('#mod-counter').textContent = String(mods.length);
  const pack = window.TQ_PACK || {};
  document.querySelectorAll('[data-pack-version]').forEach(node => node.textContent = pack.version || 'alpha');
  document.querySelectorAll('[data-minecraft]').forEach(node => node.textContent = `Java ${pack.minecraft || '1.21.1'}`);
  document.querySelectorAll('[data-neoforge]').forEach(node => node.textContent = `NeoForge ${pack.neoforge || '21.1.264'}`);
}
function filteredMods() {
  return mods.filter(mod=>{
    const categoryMatch = selectedCategory === 'all' ||
      (selectedCategory === 'other' ? !['Технологии','RPG','Мобы','Мир'].includes(mod.group) : mod.group === selectedCategory);
    return categoryMatch && (mod.name + ' ' + mod.group + ' ' + mod.description).toLowerCase().includes(query.toLowerCase());
  });
}
function renderMods() {
  const grid = document.querySelector('#mods-grid');
  grid.replaceChildren();
  const filtered = filteredMods();
  const limited = !expanded && !query && selectedCategory === 'all';
  for (const mod of limited ? filtered.slice(0, 12) : filtered) {
    const card = create('article','mod-card');
    const top = create('div','mod-card-top');
    top.append(create('span','category',mod.group));
    top.append(create('span','required'+(mod.required?'':' optional'),mod.required?'ОСНОВА':'КОМПОНЕНТ / КАНДИДАТ'));
    card.append(top,create('h3','',mod.name),create('p','',mod.description||'Совместимость будет проверена перед включением в релиз.'));
    if(mod.url){const link=create('a','', 'Страница проекта →');link.href=mod.url;link.target='_blank';link.rel='noopener noreferrer';card.append(link)}
    grid.append(card);
  }
  if(!filtered.length) grid.append(create('p','empty','Ничего не найдено. Попробуй другой запрос.'));
  document.querySelector('#mod-counter').textContent = String(filtered.length);
  const more = document.querySelector('#show-all-mods');
  more.classList.toggle('hide', !limited || filtered.length <= 12);
  more.textContent = `Показать все ${mods.length} позиций ↓`;
}
function setupSearch() {
  document.querySelector('#mod-search').addEventListener('input',e=>{query=e.target.value.trim();renderMods()});
  document.querySelectorAll('[data-category]').forEach(button=>button.addEventListener('click',()=>{
    selectedCategory=button.dataset.category;
    document.querySelectorAll('[data-category]').forEach(b=>{
      b.classList.toggle('active',b===button);
      b.setAttribute('aria-pressed',String(b===button));
    });
    renderMods();
  }));
  document.querySelector('#show-all-mods').addEventListener('click',()=>{expanded=true;renderMods()});
}
function safeField(form, name){return String(new FormData(form).get(name)||'').trim()}
function issueDraft(title, body, label){
  const params = new URLSearchParams({title, body, labels:label});
  return `${ISSUES}/new?${params.toString()}`;
}
function setupForms(){
  const bug = document.querySelector('#bug-form');
  const mod = document.querySelector('#mod-form');
  bug.addEventListener('submit',e=>{
    e.preventDefault();
    if(!bug.reportValidity())return;
    const title=safeField(bug,'title');
    const body=[
      '## Описание ошибки',safeField(bug,'details'),'',
      '## Затронутый мод',safeField(bug,'mod')||'Неизвестно','',
      '## Версия / ссылка на лог',safeField(bug,'logs')||'Не указано','',
      '## Окружение','Minecraft 1.21.1 / NeoForge — TechQuest','',
      '> Перед публикацией удалите из логов пароли, токены, IP-адреса и личные данные.'
    ].join('\n');
    window.open(issueDraft(`[Баг] ${title}`,body,LABELS.bug),'_blank','noopener,noreferrer');
  });
  mod.addEventListener('submit',e=>{
    e.preventDefault();
    if(!mod.reportValidity())return;
    const title=safeField(mod,'title');
    const link=safeField(mod,'url');
    const body=['## Название',title,'','## Ссылка на мод',link||'Не указана','','## Почему стоит добавить',safeField(mod,'details'),'','## Совместимость',safeField(mod,'compat')||'Неизвестно','','> Запрос — предложение, добавление мода не гарантируется.'].join('\n');
    window.open(issueDraft(`[Мод] ${title}`,body,LABELS.mod),'_blank','noopener,noreferrer');
  });
}
function relativeDate(iso){
  const d=new Date(iso);
  if(Number.isNaN(d.getTime()))return '';
  return d.toLocaleDateString('ru-RU',{year:'numeric',month:'short',day:'numeric'});
}
async function renderIssues(){
  const feed=document.querySelector('#issues-feed');
  try{
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),8000);
    let response;
    try{response=await fetch(`https://api.github.com/repos/${REPO}/issues?state=open&per_page=15`,{signal:controller.signal,headers:{Accept:'application/vnd.github+json'}})}
    finally{clearTimeout(timeout)}
    if(!response.ok)throw new Error(`GitHub API: ${response.status}`);
    const issues=(await response.json()).filter(issue=>!issue.pull_request).slice(0,7);
    feed.replaceChildren();
    if(!issues.length){feed.append(create('div','issue-placeholder','Пока нет открытых обращений. Можешь создать первое!'));return}
    for(const issue of issues){
      const row=create('div','issue-row');
      const dot=create('div','issue-marker','◉');
      const main=create('div','issue-main');
      const link=create('a','',issue.title||`Обращение #${issue.number}`);
      link.href=issue.html_url;link.target='_blank';link.rel='noopener noreferrer';
      main.append(link,create('div','issue-meta',`#${issue.number} · ${relativeDate(issue.created_at)}`));
      row.append(dot,main);
      if(Array.isArray(issue.labels)&&issue.labels.length){row.append(create('span','issue-label',issue.labels[0].name||'обсуждение'))}
      feed.append(row);
    }
  }catch(err){
    feed.replaceChildren(create('div','issue-placeholder','Обращения пока недоступны. Открой GitHub Issues, чтобы посмотреть их напрямую.'));
  }
}
async function githubJSON(url) {
  const controller = new AbortController();
  const timeout = setTimeout(()=>controller.abort(), 8000);
  try {
    const response = await fetch(url, {signal:controller.signal,headers:{Accept:'application/vnd.github+json'}});
    if(!response.ok) throw new Error(`GitHub API: ${response.status}`);
    return await response.json();
  } finally { clearTimeout(timeout); }
}
async function latestBuild() {
  const status = document.querySelector('#build-status');
  const link = document.querySelector('#download-link');
  // Public GitHub Releases work without authentication and do not expire as
  // Actions artifacts do. The HTML fallback links to the public Releases page.
  try {
    const release = await githubJSON(`https://api.github.com/repos/${REPO}/releases/tags/v0.3.3-micro1-preview`);
    const asset = release.assets?.find(item => item.name === 'TechQuestInstaller.exe' && item.state === 'uploaded');
    const prefix = `${GH}/releases/download/v0.3.3-micro1-preview/`;
    if(!asset || !asset.browser_download_url?.startsWith(prefix))
      throw new Error('Public Windows EXE not yet available');
    link.href = asset.browser_download_url;
    status.textContent = `Публичный тестовый выпуск: ${relativeDate(release.published_at || release.created_at)} · ${asset.name}. Для скачивания регистрация не нужна.`;
  } catch {
    status.textContent = 'Публичный EXE ещё не подтверждён. Открой список релизов: выпуски появляются после проверки безопасности.';
  }
}

initLinks();renderMods();setupSearch();setupForms();renderIssues();latestBuild();


});
