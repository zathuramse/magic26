const fmtPct = v => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : `${(Number(v)*100).toFixed(1)}%`;
const fmtMoney = v => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : `${(Number(v)/1e8).toFixed(1)}億`;
const labelMap = {
  A_repo50_c4_40_fixed20: 'A 主觀察',
  B_magic_c4_40_fixed20: 'B 寬基準',
  C_c4_25_fixed20: 'C 高濃度'
};
let allRows = [];
async function load(){
  const [summary, latest] = await Promise.all([
    fetch('./data/summary.json').then(r=>r.json()),
    fetch('./data/latest_candidates.json').then(r=>r.json())
  ]);
  allRows = latest;
  document.getElementById('status').textContent = `目前 ${new Date().toLocaleString('zh-TW')}｜最新資料 ${summary.data_through}`;
  renderCards(summary);
  setupFilters();
  renderTable();
}
function renderCards(s){
  const cards = [
    ['最新訊號日', s.latest_signal_date || '—', '最新候選日期'],
    ['最新候選數', s.latest_candidate_rows, '同日 raw/adjusted 規格列數'],
    ['2026 候選列', s.recent_2026_rows, '2026-01-01 之後'],
    ['主規格', 'A', 'repo50 + C4 40 + C5 >5']
  ];
  document.getElementById('cards').innerHTML = cards.map(c=>`<div class="card"><div class="label">${c[0]}</div><div class="value">${c[1]}</div><div class="hint">${c[2]}</div></div>`).join('');
}
function setupFilters(){
  const sel = document.getElementById('candidateFilter');
  [...new Set(allRows.map(r=>r.candidate))].sort().forEach(c=>{
    const opt=document.createElement('option'); opt.value=c; opt.textContent=labelMap[c] || c; sel.appendChild(opt);
  });
  sel.addEventListener('change', renderTable);
  document.getElementById('search').addEventListener('input', renderTable);
}
function riskTags(r){
  const tags=[];
  if(r.risk_signal_day_gt9 === true || r.risk_signal_day_gt9 === 'True') tags.push('<span class="pill risk">近漲停</span>');
  if(Number(r.next_open_gap) >= .05) tags.push('<span class="pill risk">高開>5%</span>');
  else if(Number(r.next_open_gap) >= .03) tags.push('<span class="pill">高開>3%</span>');
  if(r.risk_liquidity_lt100m === true || r.risk_liquidity_lt100m === 'True') tags.push('<span class="pill bad">流動性<1億</span>');
  return tags.join(' ');
}
function renderTable(){
  const cand = document.getElementById('candidateFilter').value;
  const q = document.getElementById('search').value.trim().toLowerCase();
  let rows = allRows.filter(r => cand === 'all' || r.candidate === cand);
  if(q) rows = rows.filter(r => `${r.stock_id} ${r.stock_name} ${r.industry_category}`.toLowerCase().includes(q));
  const html = `<table><thead><tr>
    <th>日期</th><th>規格</th><th>代號</th><th>名稱</th><th>產業</th><th>價格模式</th>
    <th>20D漲幅</th><th>repo量比</th><th>最大量距今</th><th>訊號日</th><th>隔日開盤</th><th>20D excess</th><th>金額</th><th>風險</th>
  </tr></thead><tbody>${rows.map(r=>`<tr>
    <td>${r.date}</td><td><span class="pill">${labelMap[r.candidate] || r.candidate}</span></td><td>${r.stock_id}</td><td>${r.stock_name||''}</td><td>${r.industry_category||''}</td><td>${r.price_mode}</td>
    <td>${fmtPct(r.ret_20d)}</td><td>${fmtPct(r.top5_volume_ratio_120)}</td><td>${Number(r.days_since_max_volume).toFixed(0)}日</td><td>${fmtPct(r.signal_day_ret_1d)}</td><td>${fmtPct(r.next_open_gap)}</td><td class="${Number(r.t1_open_excess_20d)>=0?'good':'bad'}">${fmtPct(r.t1_open_excess_20d)}</td><td>${fmtMoney(r.avg_amount_20d)}</td><td>${riskTags(r)}</td>
  </tr>`).join('')}</tbody></table>`;
  document.getElementById('tableWrap').innerHTML = html;
}
load().catch(err=>{document.getElementById('status').textContent='載入失敗'; console.error(err);});
