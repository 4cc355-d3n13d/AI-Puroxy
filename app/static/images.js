/* Страница /images: галерея картинок и видео из запросов и ответов. */

const gallery = { page: 1, direction: '', loaded: false };
const $ = (id) => document.getElementById(id);

function readUrl() {
  const params = new URLSearchParams(location.search);
  gallery.direction = params.get('direction') || '';
  $('g-kind').value = params.get('kind') || '';
  $('g-q').value = params.get('q') || '';
  if (params.get('model')) $('g-model').dataset.pending = params.get('model');
  gallery.page = Number(params.get('page')) || 1;
}

function syncUrl() {
  const params = new URLSearchParams();
  if (gallery.direction) params.set('direction', gallery.direction);
  if ($('g-kind').value) params.set('kind', $('g-kind').value);
  if ($('g-model').value) params.set('model', $('g-model').value);
  if ($('g-q').value.trim()) params.set('q', $('g-q').value.trim());
  if (gallery.page > 1) params.set('page', gallery.page);
  const query = params.toString();
  history.replaceState(null, '', query ? `/images?${query}` : '/images');
}

const DIRECTION_LABEL = { input: 'вход', output: 'результат' };

function card(item) {
  const caption = item.prompt || '';
  const when = esc(String(item.ts).slice(0, 16));
  return `
    <figure class="g-item ${item.direction === 'input' ? 'is-input' : ''}">
      ${mediaThumb(item.src, { kind: item.kind, group: 'gallery', caption, request: item.request_id, size: 'thumb-fill' })}
      <figcaption>
        <div class="g-meta">
          <span class="tag ${item.direction === 'output' ? 'ok' : ''}">${DIRECTION_LABEL[item.direction] || esc(item.direction)}</span>
          <span class="g-model" title="${esc(item.model || '')}">${esc(item.model || '—')}</span>
        </div>
        ${caption ? `<div class="g-prompt" title="${esc(caption)}">${esc(caption)}</div>` : ''}
        <div class="g-foot small subtle">
          <a href="/monitor?request=${item.request_id}" title="открыть запрос">${when}</a>
          ${item.uses > 1 ? `<span title="встречалась в ${item.uses} запросах">×${item.uses}</span>` : ''}
          ${item.bytes ? `<span>${fmtBytes(item.bytes)}</span>` : (item.file ? '' : '<span title="внешняя ссылка апстрима, может истечь">ссылка</span>')}
        </div>
      </figcaption>
    </figure>`;
}

async function load() {
  syncUrl();
  const params = new URLSearchParams({
    direction: gallery.direction, kind: $('g-kind').value, model: $('g-model').value,
    q: $('g-q').value.trim(), page: gallery.page, page_size: 60,
  });
  const data = await api(`/_api/media?${params}`);

  if (!gallery.loaded) {
    const pending = $('g-model').dataset.pending;
    $('g-model').innerHTML = '<option value="">Все модели</option>' + data.models
      .map((row) => `<option value="${esc(row.model)}">${esc(row.model)} (${row.n})</option>`).join('');
    if (pending) $('g-model').value = pending;
    gallery.loaded = true;
  }
  document.querySelectorAll('#g-direction button').forEach((button) => {
    button.classList.toggle('is-active', button.dataset.value === gallery.direction);
  });

  const counts = data.counts || {};
  $('g-summary').textContent = `результатов ${fmtNum(counts.output || 0)} · входящих ${fmtNum(counts.input || 0)}`;
  $('gallery').innerHTML = data.items.length
    ? data.items.map(card).join('')
    : `<div class="empty">${(counts.output || counts.input)
      ? 'Ничего не найдено — попробуйте сбросить фильтры'
      : 'Картинок пока нет. Здесь появятся изображения из запросов (vision) и результаты медиа-задач.'}</div>`;
  $('g-page').textContent = data.total
    ? `${(data.page - 1) * data.page_size + 1}–${Math.min(data.page * data.page_size, data.total)} из ${fmtNum(data.total)}`
    : '';
  $('g-prev').disabled = data.page <= 1;
  $('g-next').disabled = data.page >= data.pages;
  $('g-pager').hidden = data.pages <= 1;
}

document.addEventListener('DOMContentLoaded', () => {
  readUrl();
  load();
  document.querySelectorAll('#g-direction button').forEach((button) => {
    button.addEventListener('click', () => { gallery.direction = button.dataset.value; gallery.page = 1; load(); });
  });
  ['g-kind', 'g-model'].forEach((id) => $(id).addEventListener('change', () => { gallery.page = 1; load(); }));
  let debounce;
  $('g-q').addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(() => { gallery.page = 1; load(); }, 350); });
  $('g-prev').addEventListener('click', () => { gallery.page = Math.max(1, gallery.page - 1); load(); window.scrollTo(0, 0); });
  $('g-next').addEventListener('click', () => { gallery.page += 1; load(); window.scrollTo(0, 0); });
});
