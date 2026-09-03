/* Общие помощники интерфейса: форматирование, запросы, график запросов по дням. */

const api = async (url, options) => {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
};

const fmtMoney = (value, digits = 2) => {
  if (value === null || value === undefined) return '—';
  const number = Number(value);
  if (!isFinite(number)) return '—';
  const decimals = number !== 0 && Math.abs(number) < 0.01 ? 4 : digits;
  return number.toLocaleString('ru-RU', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + ' ₽';
};

const fmtNum = (value) => (value === null || value === undefined ? '—' : Number(value).toLocaleString('ru-RU'));

const fmtMs = (value) => {
  if (value === null || value === undefined) return '—';
  const ms = Number(value);
  return ms >= 10000 ? (ms / 1000).toFixed(1) + ' с' : Math.round(ms) + ' мс';
};

const fmtBytes = (value) => {
  const units = ['Б', 'КБ', 'МБ', 'ГБ'];
  let number = Number(value) || 0;
  let index = 0;
  while (number >= 1024 && index < units.length - 1) { number /= 1024; index += 1; }
  return `${number.toFixed(index ? 1 : 0)} ${units[index]}`;
};

const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]
));

const shortDate = (iso) => {
  const date = new Date(iso + (iso.length === 10 ? 'T00:00:00' : ''));
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' });
};

const todayISO = () => new Date().toLocaleDateString('sv-SE');

/* Запросы без модели (баланс, список моделей и т.п.) складываем в одну служебную категорию. */
const NO_MODEL = '—';
const modelLabel = (name) => (name === NO_MODEL ? 'без модели' : name);

/* Палитра назначается по позиции в легенде: моделей на графике не больше девяти,
   поэтому цвета гарантированно не совпадают (хэш имени давал коллизии). */
const PALETTE = [
  '#3f5bd9', '#e0803a', '#2f9e6f', '#b8478e', '#7a5cd0',
  '#2b93b6', '#c2544a', '#8a8f2a', '#5a6b8c', '#a0703a',
];
const GREY = '#9aa1ad';
const colorFor = (name, index = 0) => (
  name === 'прочие' || name === NO_MODEL ? GREY : PALETTE[index % PALETTE.length]
);

/* --------------------------------------------------------- баланс в шапке */

async function refreshBalanceChip() {
  const value = document.getElementById('balance-chip-value');
  if (!value) return null;
  try {
    const data = await api('/_api/overview');
    value.textContent = data.balance === null || data.balance === undefined ? '—' : fmtMoney(data.balance);
    document.getElementById('balance-chip').classList.toggle('is-low', !!data.low_balance);
    return data;
  } catch (error) {
    value.textContent = '—';
    return null;
  }
}

/* --------------------------------------------------------- график по дням */

/** Округление верхней границы шкалы до «круглого» значения. */
const niceMax = (value) => {
  const pow = 10 ** Math.floor(Math.log10(value));
  const normalized = value / pow;
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10;
  return step * pow;
};

/**
 * Линейный график «запросы по дням в разрезе моделей»: по линии на модель.
 * Инлайновый SVG — без внешних зависимостей и без лишнего внимания к себе.
 */
function renderDailyChart(container, data, options = {}) {
  const series = data.series || [];
  const models = data.models || [];
  const width = Math.max(container.clientWidth || 900, 320);
  const height = options.height || 132;
  const padLeft = 34;
  const padRight = 8;
  const padTop = 8;
  const padBottom = 18;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const colors = new Map(models.map((model, index) => [model, colorFor(model, index)]));
  const colorOf = (model) => colors.get(model) || GREY;

  const peak = Math.max(1, ...series.flatMap((day) => models.map((model) => day.models[model] || 0)));
  const max = niceMax(peak);
  const xAt = (index) => padLeft + (series.length <= 1 ? plotWidth / 2 : (index * plotWidth) / (series.length - 1));
  const yAt = (value) => padTop + plotHeight - (value / max) * plotHeight;

  const grid = [0, max / 2, max].map((value) => `
    <line x1="${padLeft}" y1="${yAt(value).toFixed(1)}" x2="${width - padRight}" y2="${yAt(value).toFixed(1)}"
          stroke="currentColor" opacity="${value === 0 ? '.18' : '.08'}"></line>
    <text x="${padLeft - 6}" y="${(yAt(value) + 3).toFixed(1)}" text-anchor="end"
          font-size="9.5" fill="currentColor" opacity=".45">${value % 1 ? value.toFixed(1) : value}</text>`).join('');

  const showDots = series.length <= 45;
  const lines = models.map((model) => {
    const points = series.map((day, index) => `${xAt(index).toFixed(1)},${yAt(day.models[model] || 0).toFixed(1)}`);
    const dots = showDots
      ? series.map((day, index) => (day.models[model]
        ? `<circle cx="${xAt(index).toFixed(1)}" cy="${yAt(day.models[model]).toFixed(1)}" r="2.4"
                   fill="${colorOf(model)}"></circle>`
        : '')).join('')
      : '';
    return `<g data-model="${esc(model)}">
      <polyline points="${points.join(' ')}" fill="none" stroke="${colorOf(model)}"
                stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"></polyline>
      ${dots}</g>`;
  }).join('');

  const labelStep = Math.ceil(series.length / 12);
  const labels = series.map((day, index) => (index % labelStep === 0
    ? `<text x="${xAt(index).toFixed(1)}" y="${height - 4}" text-anchor="middle"
             font-size="9.5" fill="currentColor" opacity=".45">${shortDate(day.day)}</text>`
    : '')).join('');

  const columnWidth = series.length <= 1 ? plotWidth : plotWidth / (series.length - 1);
  const hotspots = series.map((day, index) => `
    <rect class="chart-hit" data-index="${index}" x="${(xAt(index) - columnWidth / 2).toFixed(1)}" y="${padTop}"
          width="${columnWidth.toFixed(1)}" height="${plotHeight}" fill="transparent"></rect>`).join('');

  container.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img"
         aria-label="Запросы по дням">
      ${grid}
      <line class="chart-guide" x1="0" y1="${padTop}" x2="0" y2="${padTop + plotHeight}"
            stroke="currentColor" opacity="0" stroke-width="1" stroke-dasharray="3 3"></line>
      ${lines}
      <g class="chart-focus"></g>
      ${labels}
      ${hotspots}
    </svg>
    <div class="chart-legend">
      ${models.map((model) => `<span class="item" data-model="${esc(model)}">
          <i class="swatch" style="background:${colorOf(model)}"></i>${esc(modelLabel(model))}</span>`).join('')}
      ${models.length ? '' : '<span class="subtle">нет данных за период</span>'}
    </div>`;

  const tip = ensureTip();
  const guide = container.querySelector('.chart-guide');
  const focus = container.querySelector('.chart-focus');

  const clearFocus = () => {
    tip.style.display = 'none';
    guide.setAttribute('opacity', '0');
    focus.innerHTML = '';
  };

  container.querySelectorAll('.chart-hit').forEach((hit) => {
    hit.addEventListener('mousemove', (event) => {
      const index = Number(hit.dataset.index);
      const day = series[index];
      const rows = Object.entries(day.models).sort((a, b) => b[1] - a[1]);

      guide.setAttribute('x1', xAt(index).toFixed(1));
      guide.setAttribute('x2', xAt(index).toFixed(1));
      guide.setAttribute('opacity', '.35');
      focus.innerHTML = models.map((model) => (day.models[model]
        ? `<circle cx="${xAt(index).toFixed(1)}" cy="${yAt(day.models[model]).toFixed(1)}" r="4"
                   fill="${colorOf(model)}" stroke="var(--surface)" stroke-width="1.5"></circle>`
        : '')).join('');

      tip.innerHTML = `<div class="day">${shortDate(day.day)} — ${day.total} запр.</div>` + (rows.length
        ? rows.map(([model, count]) => `<div class="row"><span><i class="swatch" style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${colorOf(model)}"></i> ${esc(modelLabel(model))}</span><b>${count}</b></div>`).join('')
        : '<div class="subtle">нет запросов</div>');
      tip.style.display = 'block';
      tip.style.left = Math.min(event.clientX + 14, window.innerWidth - 300) + 'px';
      tip.style.top = event.clientY + 16 + 'px';
    });
    hit.addEventListener('mouseleave', clearFocus);
    if (options.onDayClick) {
      hit.style.cursor = 'pointer';
      hit.addEventListener('click', () => options.onDayClick(series[Number(hit.dataset.index)]));
    }
  });
  container.querySelector('.chart-svg').addEventListener('mouseleave', clearFocus);

  if (options.onModelClick) {
    container.querySelectorAll('.chart-legend .item').forEach((item) => {
      item.addEventListener('click', () => options.onModelClick(item.dataset.model));
    });
  }
}

function ensureTip() {
  let tip = document.querySelector('.chart-tip');
  if (!tip) {
    tip = document.createElement('div');
    tip.className = 'chart-tip';
    document.body.appendChild(tip);
  }
  return tip;
}

document.addEventListener('DOMContentLoaded', () => {
  refreshBalanceChip();
  setInterval(refreshBalanceChip, 60000);
});
