/* Страница /models: рейтинг моделей по количеству запросов. */

let allModels = [];

function renderModels(filter) {
  const rows = allModels.filter((row) => !filter || row.model.toLowerCase().includes(filter));
  const body = document.getElementById('models-body');
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="8" class="empty">Ничего не найдено</td></tr>';
    return;
  }
  const maxRequests = Math.max(...rows.map((row) => Number(row.requests)));
  body.innerHTML = rows.map((row, index) => `
    <tr>
      <td class="rank right">${index + 1}</td>
      <td>
        ${row.model === NO_MODEL
          ? '<span class="subtle">без модели <span class="small">(баланс, каталоги, статусы задач)</span></span>'
          : `<a class="model-link" href="/monitor?model=${encodeURIComponent(row.model)}">${esc(row.model)}</a>`}
        <div class="bar" style="width:${Math.max(2, (Number(row.requests) / maxRequests) * 220)}px;opacity:.35;margin-top:4px"></div>
      </td>
      <td class="right num"><b>${fmtNum(row.requests)}</b></td>
      <td class="right num">${Number(row.errors) ? `<span class="tag err">${fmtNum(row.errors)}</span>` : '<span class="subtle">0</span>'}</td>
      <td class="right num small">${fmtNum(row.prompt_tokens)} / ${fmtNum(row.completion_tokens)}</td>
      <td class="right num">${fmtMoney(row.cost)}</td>
      <td class="right num small subtle">${fmtMs(row.avg_duration_ms)}</td>
      <td class="right small subtle nowrap">${esc(row.last_used || '—')}</td>
    </tr>`).join('');
}

document.addEventListener('DOMContentLoaded', async () => {
  allModels = await api('/_api/models');
  const totalRequests = allModels.reduce((sum, row) => sum + Number(row.requests), 0);
  const totalCost = allModels.reduce((sum, row) => sum + Number(row.cost), 0);
  document.getElementById('m-summary').textContent =
    `${allModels.length} моделей · ${fmtNum(totalRequests)} запросов · ${fmtMoney(totalCost)}`;
  renderModels('');
  document.getElementById('m-search').addEventListener('input', (event) => {
    renderModels(event.target.value.trim().toLowerCase());
  });
});
