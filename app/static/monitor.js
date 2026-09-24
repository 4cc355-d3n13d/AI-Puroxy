/* Страница /monitor: график, фильтры, лог запросов с раскрытием тела. */

const state = {
  page: 1, pageSize: 50, openId: null, timer: null,
  refreshing: false, renderingId: null, seenTotal: null,
};

const el = (id) => document.getElementById(id);

function readUrlFilters() {
  const params = new URLSearchParams(location.search);
  if (params.get('model')) el('f-model').dataset.pending = params.get('model');
  if (params.get('endpoint')) el('f-endpoint').dataset.pending = params.get('endpoint');
  if (params.get('upstream')) el('f-upstream').dataset.pending = params.get('upstream');
  if (params.get('day')) { el('f-from').value = params.get('day'); el('f-to').value = params.get('day'); }
  if (params.get('q')) el('f-q').value = params.get('q');
  if (params.get('status')) el('f-status').value = params.get('status');
  if (params.get('kind')) el('f-kind').value = params.get('kind');
  // прямая ссылка на конкретный запрос: /monitor?request=123
  if (params.get('request')) state.openId = params.get('request');
}

function currentFilters() {
  return {
    model: el('f-model').value,
    endpoint: el('f-endpoint').value,
    upstream: el('f-upstream').value,
    status: el('f-status').value,
    kind: el('f-kind').value,
    q: el('f-q').value.trim(),
    date_from: el('f-from').value,
    date_to: el('f-to').value,
  };
}

function syncUrl() {
  const filters = currentFilters();
  const params = new URLSearchParams();
  if (filters.model) params.set('model', filters.model);
  if (filters.endpoint) params.set('endpoint', filters.endpoint);
  if (filters.upstream) params.set('upstream', filters.upstream);
  if (filters.status) params.set('status', filters.status);
  if (filters.kind) params.set('kind', filters.kind);
  if (filters.q) params.set('q', filters.q);
  if (filters.date_from) params.set('day', filters.date_from);
  if (state.openId) params.set('request', state.openId);
  const query = params.toString();
  history.replaceState(null, '', query ? `/monitor?${query}` : '/monitor');
}

async function loadFilters() {
  const data = await api('/_api/filters');
  const fill = (select, rows, key, label = modelLabel) => {
    const pending = select.dataset.pending || select.value;
    select.innerHTML = `<option value="">${select.dataset.all}</option>` + rows
      .map((row) => `<option value="${esc(row[key])}">${esc(label(row[key]))} (${row.n})</option>`).join('');
    if (pending) select.value = pending;
    delete select.dataset.pending;
  };
  el('f-model').dataset.all = 'Все модели';
  el('f-endpoint').dataset.all = 'Все эндпоинты';
  el('f-upstream').dataset.all = 'Все источники';
  fill(el('f-model'), data.models, 'model');
  fill(el('f-endpoint'), data.endpoints, 'endpoint');
  fill(el('f-upstream'), data.upstreams, 'upstream', sourceName);
  // фильтр по источнику нужен, только когда их больше одного
  el('f-upstream').hidden = data.upstreams.length < 2 && !el('f-upstream').value;
}

async function loadStats() {
  const data = await api('/_api/overview');
  el('stats').innerHTML = `
    <div class="stat"><div class="stat-label">Запросов всего</div>
      <div class="stat-value">${fmtNum(data.requests)}</div>
      <div class="stat-sub">сегодня ${fmtNum(data.today_requests)}</div></div>
    <div class="stat"><div class="stat-label">Потрачено</div>
      <div class="stat-value">${fmtMoney(data.cost)}</div>
      <div class="stat-sub">сегодня ${fmtMoney(data.today_cost)}</div></div>
    <div class="stat"><div class="stat-label">Токенов</div>
      <div class="stat-value">${fmtNum(data.tokens)}</div>
      <div class="stat-sub">${fmtNum(data.models)} моделей</div></div>
    <div class="stat"><div class="stat-label">Ошибок</div>
      <div class="stat-value">${fmtNum(data.errors)}</div>
      <div class="stat-sub">${data.requests ? ((data.errors / data.requests) * 100).toFixed(1) : '0.0'}% запросов</div></div>
    <div class="stat"><div class="stat-label">Баланс</div>
      <div class="stat-value">${data.balance === null ? '—' : fmtMoney(data.balance)}</div>
      <div class="stat-sub">${data.balance_checked_at ? 'на ' + data.balance_checked_at : 'нет данных'}</div></div>`;
}

async function loadChart() {
  const days = Number(el('chart-days').value);
  const data = await api(`/_api/chart?days=${days}`);
  const total = data.series.reduce((sum, day) => sum + day.total, 0);
  el('chart-summary').textContent = `${fmtNum(total)} запр. за ${days} дн.`;
  renderDailyChart(el('chart'), data, {
    onModelClick: (model) => {
      if (model === NO_MODEL || model === 'прочие') return;
      el('f-model').value = model;
      reload(true);
    },
    onDayClick: (day) => { el('f-from').value = day.day; el('f-to').value = day.day; reload(true); },
  });
}

const statusTag = (row) => {
  if (row.error && !row.status_code) return '<span class="tag err">ошибка</span>';
  if (row.status_code === null) return '<span class="tag">—</span>';
  const cls = row.status_code >= 400 ? 'err' : 'ok';
  return `<span class="tag ${cls}">${row.status_code}</span>`;
};

/* Значки, по которым сразу видно характер запроса. */
const badgesOf = (row) => {
  const badges = [];
  if (row.tools_called) {
    const names = row.tools_called.split(',');
    badges.push(`<span class="badge tools" title="вызваны инструменты">🔧 ${names.map(esc).join(', ')}</span>`);
  } else if (row.tools_offered) {
    badges.push(`<span class="badge dim" title="инструменты предложены, но не вызваны">🔧 ${row.tools_offered} доступно</span>`);
  }
  if (row.reasoning_tokens) {
    badges.push(`<span class="badge think" title="модель рассуждала">💭 ${fmtNum(row.reasoning_tokens)}</span>`);
  }
  if (row.images) badges.push(`<span class="badge" title="изображения в запросе">🖼 ${row.images}</span>`);
  if (row.media_out) badges.push(`<span class="badge media-badge" title="медиа в ответе">🖼 → ${row.media_out}</span>`);
  if (row.cached_tokens) {
    badges.push(`<span class="badge dim" title="токены из кэша — дешевле">⚡ кэш ${fmtNum(row.cached_tokens)}</span>`);
  }
  if (row.stream) badges.push('<span class="badge dim" title="потоковый ответ">stream</span>');
  if (row.finish_reason && row.finish_reason !== 'stop' && row.finish_reason !== 'end_turn') {
    badges.push(`<span class="badge warn-badge" title="причина завершения">${esc(row.finish_reason)}</span>`);
  }
  return badges.join('');
};

const previewOf = (row) => {
  const badges = badgesOf(row);
  if (row.error) {
    return `<div class="log-line err-line">${esc(row.error).slice(0, 200)}</div>${badges}`;
  }
  const ask = row.prompt_preview;
  const answer = row.answer_preview;
  if (!ask && !answer) {
    // служебные вызовы без диалога: баланс, каталоги, статусы задач
    return `<div class="log-line subtle">${esc(row.endpoint || row.path)} · ${fmtBytes(row.response_size || 0)}</div>${badges}`;
  }
  const think = row.reasoning_preview;
  return `
    ${ask ? `<div class="log-line"><span class="who">→</span><span class="txt">${esc(ask)}</span></div>` : ''}
    ${think ? `<div class="log-line think-line"><span class="who">💭</span><span class="txt">${esc(think)}</span></div>` : ''}
    ${answer ? `<div class="log-line answer"><span class="who">←</span><span class="txt">${esc(answer)}</span></div>` : ''}
    ${badges}`;
};

const costTitle = (row) => {
  const parts = [row.cost_source === 'estimated' ? 'оценка по прайсу модели' : 'из ответа API'];
  if (row.cost_api !== null && row.cost_api !== undefined) parts.push(`API: ${fmtMoney(row.cost_api)}`);
  if (row.cost_estimated !== null && row.cost_estimated !== undefined) parts.push(`прайс: ${fmtMoney(row.cost_estimated)}`);
  return esc(parts.join(' · '));
};

function rowHtml(row) {
  return `
      <tr class="log-row" data-id="${row.id}">
        <td class="mono small nowrap">${esc(row.ts).slice(5)}</td>
        <td class="cell-model" title="${esc(row.model || '')}${row.path ? ' · ' + esc(row.path) : ''}">
          ${row.model ? esc(row.model) : `<span class="subtle">${esc(row.endpoint || row.path || '—')}</span>`}
        </td>
        <td class="right">${statusTag(row)}</td>
        <td class="right num small">${fmtMs(row.duration_ms)}</td>
        <td class="right num small">${row.total_tokens
          ? `<span title="${fmtNum(row.prompt_tokens)} в запросе → ${fmtNum(row.completion_tokens)} в ответе">${fmtNum(row.total_tokens)}</span>`
          : '<span class="subtle">—</span>'}</td>
        <td class="right num small">${row.cost !== null && row.cost !== undefined
          ? `<span title="${row.cost_source === 'estimated' ? 'оценка по прайсу модели' : 'из ответа API'}">${fmtMoney(row.cost)}${row.cost_source === 'estimated' ? '*' : ''}</span>`
          : '<span class="subtle">—</span>'}</td>
        <td class="cell-what">${previewOf(row)}</td>
      </tr>`;
}

const rowNode = (row) => {
  const template = document.createElement('template');
  template.innerHTML = rowHtml(row).trim();
  const node = template.content.firstElementChild;
  node.addEventListener('click', () => toggleDetail(node));
  return node;
};

/* Строка, по которой держим экран при вставке новых записей сверху:
   открытая карточка, иначе первая видимая строка. */
function scrollAnchor(body) {
  const open = body.querySelector('.log-row.is-open');
  if (open) return open;
  const top = 52 + 40; // шапка страницы и шапка таблицы
  return [...body.querySelectorAll('.log-row')].find((row) => row.getBoundingClientRect().bottom > top) || null;
}

/**
 * Автообновление без перерисовки: строки сопоставляются по id, существующие узлы
 * (и раскрытая карточка под своей строкой) не пересоздаются, новые вставляются
 * на свои места. Раньше таблица перерисовывалась целиком — карточка закрывалась
 * и открывалась заново, сбрасывая прокрутку, выделение и развёрнутые блоки.
 */
function patchLog(body, items) {
  const existing = new Map([...body.querySelectorAll('.log-row')].map((node) => [node.dataset.id, node]));
  const anchor = scrollAnchor(body);
  const anchorTop = anchor ? anchor.getBoundingClientRect().top : 0;
  const tableTop = body.getBoundingClientRect().top + window.scrollY;

  const wanted = new Set(items.map((row) => String(row.id)));
  existing.forEach((node, id) => {
    if (wanted.has(id)) return;
    const next = node.nextElementSibling;
    if (next && next.classList.contains('detail-row')) next.remove();
    node.remove();
  });
  body.querySelectorAll('tr:not(.log-row):not(.detail-row)').forEach((node) => node.remove());

  let cursor = null; // последний размещённый узел (строка или её карточка)
  items.forEach((row) => {
    let node = existing.get(String(row.id));
    if (!node) {
      node = rowNode(row);
      node.classList.add('is-new');
      setTimeout(() => node.classList.remove('is-new'), 2500);
    }
    const detail = node.nextElementSibling && node.nextElementSibling.classList.contains('detail-row')
      ? node.nextElementSibling : null;
    const place = cursor ? cursor.nextElementSibling : body.firstElementChild;
    if (place !== node) body.insertBefore(node, place);
    if (detail && node.nextElementSibling !== detail) node.after(detail);
    cursor = detail || node;
  });

  // пользователь прокрутил к таблице — держим на месте то, что он читает;
  // если он наверху страницы, новые строки просто появляются сверху
  if (anchor && anchor.isConnected && window.scrollY > tableTop - 60) {
    const shift = anchor.getBoundingClientRect().top - anchorTop;
    if (shift) window.scrollBy(0, shift);
  }
}

async function loadLog(options = {}) {
  const filters = currentFilters();
  const params = new URLSearchParams({ ...filters, page: state.page, page_size: state.pageSize });
  const data = await api(`/_api/requests?${params}`);
  const body = el('log-body');
  const openId = state.openId;
  const openVisible = !openId || data.items.some((row) => String(row.id) === String(openId));

  if (options.live && openId && !openVisible) {
    // открытая запись уехала со страницы — таблицу не трогаем, только сообщаем о новых
    const fresh = data.total - (state.seenTotal ?? data.total);
    if (fresh > 0) {
      el('pending-new').textContent = `+${fmtNum(fresh)} новых`;
      el('pending-new').hidden = false;
    }
    return;
  }

  if (!data.items.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty">Запросов нет — отправьте первый запрос через прокси</td></tr>';
  } else if (options.live) {
    patchLog(body, data.items);
  } else {
    body.innerHTML = '';
    data.items.forEach((row) => body.appendChild(rowNode(row)));
  }
  state.seenTotal = data.total;
  el('pending-new').hidden = true;
  el('page-info').textContent = `${data.total ? (data.page - 1) * data.page_size + 1 : 0}–${Math.min(data.page * data.page_size, data.total)} из ${fmtNum(data.total)}`;
  el('prev').disabled = data.page <= 1;
  el('next').disabled = data.page >= data.pages;
  if (state.openId) {
    const row = body.querySelector(`.log-row[data-id="${state.openId}"]`);
    if (row && !row.classList.contains('is-open')) openDetail(row, true);
  }
}

function toggleDetail(row) {
  const next = row.nextElementSibling;
  if (next && next.classList.contains('detail-row')) {
    next.remove();
    row.classList.remove('is-open');
    state.openId = null;
    syncUrl();
    return;
  }
  document.querySelectorAll('.detail-row').forEach((node) => node.remove());
  document.querySelectorAll('.log-row.is-open').forEach((node) => node.classList.remove('is-open'));
  openDetail(row, false);
}

function pretty(raw) {
  if (!raw) return '(пусто)';
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.stream && typeof parsed.text === 'string') {
      return `— собранный текст (${parsed.events} SSE-событий) —\n\n${parsed.text}\n\n— сырые события —\n\n${parsed.raw}`;
    }
    return JSON.stringify(parsed, null, 2);
  } catch (error) {
    return raw;
  }
}

const ROLE_LABEL = {
  system: 'Система', user: 'Пользователь', assistant: 'Ассистент',
  tool: 'Результат инструмента', developer: 'Разработчик',
};

const asText = (value) => (typeof value === 'string' ? value : JSON.stringify(value, null, 2));

/* Блок вызова инструмента: имя и аргументы в читаемом виде. */
function toolCallBlock(call) {
  const args = call.arguments === null || call.arguments === undefined ? '' : asText(call.arguments);
  return `
    <div class="tool-call">
      <div class="tool-name">🔧 ${esc(call.name || 'без имени')}</div>
      ${args ? `<pre class="tool-args">${esc(args)}</pre>` : ''}
    </div>`;
}

const LONG_TEXT = 500;

/* Длинные промпты сворачиваем: иначе системная инструкция на несколько экранов
   оттесняет вниз то, ради чего сюда и заходят — рассуждения и ответ. */
function collapsibleText(text, label) {
  if (!text) return '';
  if (text.length <= LONG_TEXT) return `<div class="msg-text">${esc(text)}</div>`;
  return `
    <details class="long-text">
      <summary>${esc(label)} · ${fmtNum(text.length)} символов — развернуть</summary>
      <div class="msg-text">${esc(text)}</div>
    </details>
    <div class="msg-text preview">${esc(text.slice(0, 200))}…</div>`;
}

/* Превью картинок сообщения; группа — чтобы листать их в просмотре стрелками. */
const mediaStrip = (sources, group, caption) => (sources && sources.length
  ? `<div class="media-strip">${sources.map((src) => mediaThumb(src, { group, caption })).join('')}</div>`
  : '');

function messageBlock(message) {
  const extras = (message.extras || []).map((extra) => {
    if (extra.kind === 'tool_call') return toolCallBlock(extra);
    if (extra.kind === 'thinking') return `<div class="think-block">💭 ${esc(extra.text)}</div>`;
    if (extra.kind === 'tool_result') return `<pre class="tool-args">${esc(extra.text || '')}</pre>`;
    return '';
  }).join('');
  const role = ROLE_LABEL[message.role] || message.role;
  const shown = (message.media || []).length;
  const lost = (message.images || 0) - shown;
  return `
    <div class="msg msg-${esc(message.role)}">
      <div class="msg-role">${esc(role)}${message.images ? ` · 🖼 ${message.images}` : ''}${lost > 0
        ? ` <span class="subtle" title="картинка не сохранилась: тело запроса было обрезано до появления галереи">(${lost} не сохранилось)</span>` : ''}</div>
      ${collapsibleText(message.text, role)}
      ${mediaStrip(message.media, `req-${state.renderingId}`, (message.text || '').slice(0, 300))}
      ${extras}
    </div>`;
}

/* Человекочитаемая карточка: о чём просили, что модель думала и сделала. */
function dialogView(data) {
  const summary = data.summary || {};
  const request = summary.request || {};
  const response = summary.response || {};
  const tokens = summary.tokens || {};

  const params = Object.entries(request.params || {})
    .map(([key, value]) => `<span class="param">${esc(key)}: <b>${esc(asText(value))}</b></span>`).join('');

  const offered = (request.tools_offered || []).length
    ? `<div class="tools-offered">
         <span class="section-label">Доступные инструменты (${request.tools_offered.length})</span>
         ${request.tools_offered.map((tool) => `<span class="badge dim" title="${esc(tool.description || '')}">${esc(tool.name)}</span>`).join('')}
       </div>`
    : '';

  // в длинной переписке показываем последние сообщения, остальные прячем под кат
  const all = request.messages || [];
  const TAIL = 2;
  const head = all.length > TAIL + 1 ? all.slice(0, all.length - TAIL) : [];
  const tail = head.length ? all.slice(-TAIL) : all;
  const messages = (head.length
    ? `<details class="earlier"><summary>Ранее в диалоге · ${head.length} сообщ.</summary>
         ${head.map(messageBlock).join('')}</details>`
    : '') + tail.map(messageBlock).join('');

  const system = request.system
    ? messageBlock({ role: 'system', text: request.system, images: 0, extras: [] })
    : '';

  const reasoningTokens = tokens.reasoning_tokens ? ` · ${fmtNum(tokens.reasoning_tokens)} токенов` : '';
  const reasoning = response.reasoning
    ? `<details class="think" open>
         <summary>💭 Рассуждения модели${reasoningTokens}</summary>
         <div class="think-block">${esc(response.reasoning)}</div>
       </details>`
    : '';

  const calls = (response.tool_calls || []).map(toolCallBlock).join('');

  const lastPrompt = ((request.messages || []).slice(-1)[0] || {}).text || '';
  const media = response.media
    ? `<div class="msg msg-answer">
         <div class="msg-role">Медиа-задача · ${esc(response.media.state || '—')}</div>
         ${response.media.task_id ? `<div class="msg-text mono small">${esc(response.media.task_id)}</div>` : ''}
         ${mediaStrip(response.media.urls, `res-${state.renderingId}`, lastPrompt.slice(0, 300))}
       </div>`
    : '';
  const images = (response.images || []).length
    ? `<div class="msg msg-answer"><div class="msg-role">Сгенерировано · 🖼 ${response.images.length}</div>
         ${mediaStrip(response.images, `res-${state.renderingId}`, lastPrompt.slice(0, 300))}</div>`
    : '';

  const answer = response.text
    ? `<div class="msg msg-answer"><div class="msg-role">Ответ${response.finish_reason ? ` · ${esc(response.finish_reason)}` : ''}</div>
         <div class="msg-text">${esc(response.text)}</div></div>`
    : '';

  const error = response.error || data.error
    ? `<div class="msg msg-error"><div class="msg-role">Ошибка</div>
         <div class="msg-text">${esc(response.error || data.error)}</div></div>`
    : '';

  const nothing = !system && !messages && !answer && !reasoning && !calls && !media && !images && !error;
  if (nothing) {
    return `<div class="subtle small">Диалога нет — это служебный вызов. Смотрите вкладку «Сырой JSON».</div>`;
  }

  return `
    ${params || offered ? `<div class="params-row">${params}${offered}</div>` : ''}
    <div class="dialog">
      ${system}${messages}
      ${reasoning ? `<div class="msg msg-think">${reasoning}</div>` : ''}
      ${calls ? `<div class="msg msg-assistant"><div class="msg-role">Вызовы инструментов</div>${calls}</div>` : ''}
      ${answer}${images}${media}${error}
    </div>`;
}

async function openDetail(row, silent) {
  const id = row.dataset.id;
  state.openId = id;
  syncUrl();
  row.classList.add('is-open');
  const detail = document.createElement('tr');
  detail.className = 'detail-row';
  detail.innerHTML = '<td colspan="7"><div class="detail"><div class="subtle">Загрузка…</div></div></td>';
  row.after(detail);
  try {
    const data = await api(`/_api/requests/${id}`);
    state.renderingId = id;
    const tokens = (data.summary && data.summary.tokens) || {};
    detail.innerHTML = `<td colspan="7"><div class="detail">
      <div class="detail-meta">
        <span class="tag accent">${esc(data.method)} ${esc(data.path)}</span>
        ${data.model ? `<span class="tag">${esc(data.model)}</span>` : ''}
        ${data.upstream && Object.keys(window.SOURCE_NAMES || {}).length > 1 ? `<span class="tag" title="источник">⇄ ${esc(sourceName(data.upstream))}</span>` : ''}
        ${data.stream ? '<span class="tag warn">stream</span>' : ''}
        <span class="tag">${esc(data.ts)}</span>
        <span class="tag">${fmtMs(data.duration_ms)}</span>
        ${data.total_tokens ? `<span class="tag">${fmtNum(data.prompt_tokens)} → ${fmtNum(data.completion_tokens)} токенов</span>` : ''}
        ${tokens.reasoning_tokens ? `<span class="tag think-tag">💭 ${fmtNum(tokens.reasoning_tokens)}</span>` : ''}
        ${tokens.cached_tokens ? `<span class="tag">⚡ кэш ${fmtNum(tokens.cached_tokens)}</span>` : ''}
        ${data.cost !== null ? `<span class="tag ok" title="${costTitle(data)}">${fmtMoney(data.cost)}${data.cost_source === 'estimated' ? ' (оценка)' : ''}</span>` : ''}
        ${data.upstream_id ? `<span class="tag mono">${esc(data.upstream_id)}</span>` : ''}
        ${statusTag(data)}
      </div>
      <div class="detail-tabs">
        <button class="tab is-active" data-tab="dialog">Диалог</button>
        <button class="tab" data-tab="raw">Сырой JSON</button>
      </div>
      <div class="tab-body" data-pane="dialog">${dialogView(data)}</div>
      <div class="tab-body is-hidden" data-pane="raw">
        <div class="raw-grid">
          <div><h3>Запрос</h3><pre>${esc(pretty(data.request_body))}</pre></div>
          <div><h3>Ответ</h3><pre>${esc(pretty(data.response_body))}</pre></div>
        </div>
      </div>
    </div></td>`;
    detail.querySelectorAll('.tab').forEach((tab) => {
      tab.addEventListener('click', (event) => {
        event.stopPropagation();
        detail.querySelectorAll('.tab').forEach((t) => t.classList.toggle('is-active', t === tab));
        detail.querySelectorAll('.tab-body').forEach((pane) => {
          pane.classList.toggle('is-hidden', pane.dataset.pane !== tab.dataset.tab);
        });
      });
    });
    detail.addEventListener('click', (event) => event.stopPropagation());
  } catch (error) {
    detail.innerHTML = `<td colspan="7"><div class="detail"><div class="subtle">Не удалось загрузить: ${esc(error.message)}</div></div></td>`;
  }
  if (!silent) detail.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

async function reload(resetPage) {
  if (resetPage) state.page = 1;
  syncUrl();
  await Promise.all([loadLog(), loadStats(), loadChart()]);
}

async function autoRefresh() {
  if (document.hidden || state.refreshing) return;
  state.refreshing = true;
  try {
    await Promise.all([loadLog({ live: true }), loadStats()]);
  } catch (error) {
    // сеть моргнула — попробуем в следующий раз
  } finally {
    state.refreshing = false;
  }
}

function scheduleAutoRefresh() {
  clearInterval(state.timer);
  el('pending-new').hidden = true;
  if (el('auto-refresh').checked) state.timer = setInterval(autoRefresh, 5000);
}

document.addEventListener('DOMContentLoaded', async () => {
  readUrlFilters();
  await loadFilters();
  await reload(true);
  scheduleAutoRefresh();

  ['f-model', 'f-endpoint', 'f-upstream', 'f-status', 'f-kind', 'f-from', 'f-to'].forEach((id) => {
    el(id).addEventListener('change', () => reload(true));
  });
  el('f-size').addEventListener('change', () => { state.pageSize = Number(el('f-size').value); reload(true); });
  let debounce;
  el('f-q').addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(() => reload(true), 350); });
  el('f-reset').addEventListener('click', () => {
    ['f-q', 'f-from', 'f-to'].forEach((id) => { el(id).value = ''; });
    ['f-model', 'f-endpoint', 'f-upstream', 'f-status', 'f-kind'].forEach((id) => { el(id).value = ''; });
    reload(true);
  });
  el('prev').addEventListener('click', () => { state.page = Math.max(1, state.page - 1); loadLog(); });
  el('next').addEventListener('click', () => { state.page += 1; loadLog(); });
  el('chart-days').addEventListener('change', loadChart);
  el('auto-refresh').addEventListener('change', scheduleAutoRefresh);
  el('pending-new').addEventListener('click', () => {
    document.querySelectorAll('.detail-row').forEach((node) => node.remove());
    state.openId = null;
    state.page = 1;
    el('pending-new').hidden = true;
    loadLog().then(() => el('log-body').closest('.card').scrollIntoView({ behavior: 'smooth' }));
  });
  el('chart-toggle').addEventListener('click', () => {
    const card = el('chart-card');
    const collapsed = card.classList.toggle('is-collapsed');
    el('chart-toggle').textContent = collapsed ? 'Развернуть' : 'Свернуть';
    localStorage.setItem('chart-collapsed', collapsed ? '1' : '');
    if (!collapsed) loadChart();
  });
  if (localStorage.getItem('chart-collapsed')) el('chart-toggle').click();
  window.addEventListener('resize', () => { clearTimeout(window._chartResize); window._chartResize = setTimeout(loadChart, 250); });
});
