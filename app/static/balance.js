/* Страница /balance: календарь трат по дням + детализация по моделям за выбранный день. */

const bstate = { month: null, day: todayISO(), data: null };
const bel = (id) => document.getElementById(id);

const monthTitle = (month) => {
  const [year, mon] = month.split('-').map(Number);
  return new Date(year, mon - 1, 1).toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
};

async function loadCalendar(month) {
  const data = await api(`/_api/balance/calendar${month ? `?month=${month}` : ''}`);
  bstate.month = data.month;
  bstate.data = data;

  bel('cal-month').textContent = monthTitle(data.month);
  bel('cal-total').textContent = `${fmtMoney(data.total_cost)} · ${fmtNum(data.total_requests)} запр. за месяц`;

  const maxCost = Math.max(...data.days.map((day) => day.cost), 0);
  const today = todayISO();
  const blanks = Array.from({ length: data.weekday_offset }, () => '<div class="cal-cell is-blank"></div>').join('');
  bel('cal-grid').innerHTML = blanks + data.days.map((day) => {
    const intensity = maxCost > 0 ? Math.min(1, day.cost / maxCost) : 0;
    const empty = day.requests === 0;
    return `<button class="cal-cell${empty ? ' is-empty' : ''}${day.day === today ? ' is-today' : ''}${day.day === bstate.day ? ' is-selected' : ''}"
              data-day="${day.day}" ${day.balance_end !== null ? `title="баланс на конец дня: ${fmtMoney(day.balance_end)}"` : ''}>
        <span class="cal-day">${Number(day.day.slice(-2))}</span>
        <span class="cal-cost${empty ? ' zero' : ''}">${day.cost > 0 ? fmtMoney(day.cost) : '—'}</span>
        <span class="cal-req">${day.requests ? day.requests + ' запр.' : ''}</span>
        ${day.cost > 0 ? `<i class="cal-bar" style="opacity:${(0.18 + intensity * 0.82).toFixed(2)}"></i>` : ''}
      </button>`;
  }).join('');

  bel('cal-grid').querySelectorAll('.cal-cell[data-day]').forEach((cell) => {
    cell.addEventListener('click', () => selectDay(cell.dataset.day));
  });

  const overview = await api('/_api/overview');
  const spentThisMonth = data.total_cost;
  bel('balance-stats').innerHTML = `
    <div class="stat"><div class="stat-label">Текущий баланс</div>
      <div class="stat-value" style="${overview.low_balance ? 'color:var(--err)' : ''}">${overview.balance === null ? '—' : fmtMoney(overview.balance)}</div>
      <div class="stat-sub">${data.balance_checked_at ? 'проверен ' + data.balance_checked_at : 'нет данных'}</div></div>
    <div class="stat"><div class="stat-label">Потрачено за месяц</div>
      <div class="stat-value">${fmtMoney(spentThisMonth)}</div>
      <div class="stat-sub">${fmtNum(data.total_requests)} запросов</div></div>
    <div class="stat"><div class="stat-label">В среднем за день</div>
      <div class="stat-value">${fmtMoney(spentThisMonth / Math.max(1, data.days.filter((d) => d.requests > 0).length))}</div>
      <div class="stat-sub">по дням с активностью</div></div>
    <div class="stat"><div class="stat-label">Порог предупреждения</div>
      <div class="stat-value">${overview.balance_threshold ? fmtMoney(overview.balance_threshold) : 'выкл.'}</div>
      <div class="stat-sub">${overview.low_balance ? 'баланс ниже порога' : 'настраивается в /settings'}</div></div>`;
}

async function selectDay(day) {
  bstate.day = day;
  document.querySelectorAll('.cal-cell').forEach((cell) => {
    cell.classList.toggle('is-selected', cell.dataset.day === day);
  });
  bel('day-title').textContent = `Детализация за ${new Date(day + 'T00:00:00').toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}`;
  bel('day-log-link').href = `/monitor?day=${day}`;
  const data = await api(`/_api/balance/day/${day}`);
  if (!data.models.length) {
    bel('day-detail').innerHTML = '<div class="empty">За этот день запросов не было</div>';
    return;
  }
  const maxCost = Math.max(...data.models.map((row) => Number(row.cost)), 0);
  bel('day-detail').innerHTML = `
    <table>
      <thead><tr><th>Модель</th><th class="right">Запр.</th><th class="right">Токены</th><th class="right">Траты</th></tr></thead>
      <tbody>
        ${data.models.map((row) => `
          <tr>
            <td>${row.model === NO_MODEL
              ? '<span class="subtle">без модели</span>'
              : `<a class="model-link" href="/monitor?model=${encodeURIComponent(row.model)}&day=${day}">${esc(row.model)}</a>`}
              ${Number(row.estimated) ? '<span class="tag small" title="часть стоимости оценена по прайсу">оценка</span>' : ''}</td>
            <td class="right num">${fmtNum(row.requests)}</td>
            <td class="right num small subtle">${fmtNum(Number(row.prompt_tokens) + Number(row.completion_tokens))}</td>
            <td class="right num">
              <div class="bar-cell" style="justify-content:flex-end">
                <span class="bar" style="width:${maxCost ? Math.max(2, (Number(row.cost) / maxCost) * 60) : 2}px"></span>
                ${fmtMoney(row.cost)}
              </div></td>
          </tr>`).join('')}
      </tbody>
      <tfoot><tr>
        <th>Итого</th><th class="right num">${fmtNum(data.total_requests)}</th><th></th>
        <th class="right num">${fmtMoney(data.total_cost)}</th>
      </tr></tfoot>
    </table>
    <div class="card-body small subtle">
      ${data.balance_delta === null ? '' : `<div style="margin-bottom:6px">
        Фактическое изменение баланса за день: <b>${fmtMoney(data.balance_delta)}</b>
        (${fmtMoney(data.balance_start)} → ${fmtMoney(data.balance_end)}).
        Разница с суммой по логу — это траты, которые API не возвращает в ответе, например медиа-задачи.
      </div>`}
      По эндпоинтам: ${data.endpoints.map((row) => `${esc(row.endpoint)} — ${row.requests}`).join(', ') || '—'}
    </div>`;
}

document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(location.search);
  if (params.get('day')) bstate.day = params.get('day');
  await loadCalendar(params.get('month') || bstate.day.slice(0, 7));
  await selectDay(bstate.day);

  bel('prev-month').addEventListener('click', () => loadCalendar(bstate.data.prev_month));
  bel('next-month').addEventListener('click', () => loadCalendar(bstate.data.next_month));
  bel('this-month').addEventListener('click', () => loadCalendar(todayISO().slice(0, 7)));
  bel('refresh-balance').addEventListener('click', async (event) => {
    event.target.disabled = true;
    event.target.textContent = 'Обновляем…';
    await fetch('/_api/balance/refresh', { method: 'POST' });
    await refreshBalanceChip();
    await loadCalendar(bstate.month);
    await selectDay(bstate.day);
    event.target.disabled = false;
    event.target.textContent = 'Обновить баланс';
  });
});
