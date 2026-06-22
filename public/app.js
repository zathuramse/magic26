const fmtPct = v => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : `${(Number(v)*100).toFixed(1)}%`;
const fmtMoney = v => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : `${(Number(v)/1e8).toFixed(1)}億`;
const fmtNum = (v, d=2) => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(d);
const labelMap = {
  A_repo50_c4_40_fixed20: 'A 主觀察',
  B_magic_c4_40_fixed20: 'B 寬基準',
  C_c4_25_fixed20: 'C 高濃度'
};
const specTone = { A_repo50_c4_40_fixed20: 'main', B_magic_c4_40_fixed20: 'base', C_c4_25_fixed20: 'tight' };
let summaryData = null;
let latestRows = [];
let recentRows = [];
let selectedDetailKey = null;

async function load(){
  const [summary, latest, recent] = await Promise.all([
    fetch('./data/summary.json').then(r=>r.json()),
    fetch('./data/latest_candidates.json').then(r=>r.json()),
    fetch('./data/recent_candidates.json').then(r=>r.json())
  ]);
  summaryData = summary;
  latestRows = latest;
  recentRows = recent;
  document.getElementById('status').textContent = `目前 ${new Date().toLocaleString('zh-TW')}｜最新資料 ${summary.data_through}`;
  renderCards(summary);
  renderCandidateSummary(summary);
  setupFilters();
  renderMainAList();
  renderStockCards();
}

function renderCards(s){
  const main = (s.candidates || []).find(c=>c.candidate === s.main_spec) || {};
  const cards = [
    ['最新訊號日', s.latest_signal_date || '—', '最新候選日期'],
    ['最新候選數', s.latest_candidate_rows, '同日 raw/adjusted 規格列數'],
    ['主規格筆數', main.rows ?? '—', 'Candidate A 歷史候選列'],
    ['A 20D excess', fmtPct(main.median_t1_open_excess_20d), `勝率 ${fmtPct(main.win_t1_open_excess_20d)}`]
  ];
  document.getElementById('cards').innerHTML = cards.map(c=>`<div class="card"><div class="label">${c[0]}</div><div class="value">${c[1]}</div><div class="hint">${c[2]}</div></div>`).join('');
}

function renderCandidateSummary(s){
  document.getElementById('candidateSummary').innerHTML = (s.candidates || []).map(c => `
    <button class="spec-card ${specTone[c.candidate] || ''}" data-candidate="${c.candidate}">
      <div class="spec-top"><span>${labelMap[c.candidate] || c.candidate}</span><strong>${c.rows}</strong></div>
      <div class="spec-metrics">
        <span>最新 ${c.latest_date}</span>
        <span>raw ${c.raw_rows} / adj ${c.adjusted_rows}</span>
        <span>20D excess ${fmtPct(c.median_t1_open_excess_20d)}</span>
        <span>勝率 ${fmtPct(c.win_t1_open_excess_20d)}</span>
      </div>
    </button>
  `).join('');
  document.querySelectorAll('.spec-card').forEach(btn => btn.addEventListener('click', () => setCandidate(btn.dataset.candidate)));
}

function setupFilters(){
  const sel = document.getElementById('candidateFilter');
  [...new Set([...latestRows, ...recentRows].map(r=>r.candidate))].sort().forEach(c=>{
    const opt=document.createElement('option'); opt.value=c; opt.textContent=labelMap[c] || c; sel.appendChild(opt);
  });
  ['candidateFilter','rangeFilter','riskFilter','sortFilter'].forEach(id=>document.getElementById(id).addEventListener('change', renderStockCards));
  document.getElementById('search').addEventListener('input', renderStockCards);
  document.getElementById('clearDetail').addEventListener('click', clearDetail);
  document.getElementById('jumpMainA').addEventListener('click', () => { document.getElementById('rangeFilter').value='recent'; setCandidate('A_repo50_c4_40_fixed20'); });
  document.querySelectorAll('#quickFilters button').forEach(btn => btn.addEventListener('click', () => setCandidate(btn.dataset.candidate)));
}

function setCandidate(value){
  document.getElementById('candidateFilter').value = value;
  document.querySelectorAll('#quickFilters button').forEach(btn => btn.classList.toggle('active', btn.dataset.candidate === value));
  renderStockCards();
}
function activeRows(){ return document.getElementById('rangeFilter').value === 'recent' ? recentRows : latestRows; }
function isTrue(v){ return v === true || v === 'True' || v === 'true' || v === 1 || v === '1'; }
function isChase(r){ return isTrue(r.risk_signal_day_gt9) || Number(r.next_open_gap) >= .05; }
function isLowLiquidity(r){ return isTrue(r.risk_liquidity_lt100m); }
function classify(r){
  if(r.candidate !== 'A_repo50_c4_40_fixed20') return '非主規格觀察';
  if(isLowLiquidity(r)) return '流動性不足';
  if(isChase(r)) return '追高風險';
  return '可研究';
}
function priorityScore(r){
  let score = 0;
  if(r.candidate === 'A_repo50_c4_40_fixed20') score += 45;
  if(!isChase(r)) score += 18;
  if(!isLowLiquidity(r)) score += 15;
  score += Math.min(14, Math.max(0, Number(r.top5_volume_ratio_120 || 0) * 14));
  score += Math.min(8, Math.max(0, Number(r.avg_amount_20d || 0) / 1_000_000_000 * 2));
  return Math.round(score);
}
function priorityLabel(r){
  const s = priorityScore(r);
  if(s >= 82) return '優先研究';
  if(s >= 62) return '次級觀察';
  return '風險觀察';
}
function matchRisk(r, risk){
  if(risk === 'all') return true;
  if(risk === 'clean') return !isChase(r) && !isLowLiquidity(r) && r.candidate === 'A_repo50_c4_40_fixed20';
  if(risk === 'chase') return isChase(r);
  if(risk === 'liquidity') return isLowLiquidity(r);
  if(risk === 'nonmain') return r.candidate !== 'A_repo50_c4_40_fixed20';
  return true;
}
function compareRows(sort){
  return (a,b) => {
    if(sort === 'date') return String(b.date).localeCompare(String(a.date)) || priorityScore(b)-priorityScore(a);
    if(sort === 'repo') return Number(b.top5_volume_ratio_120||0) - Number(a.top5_volume_ratio_120||0);
    if(sort === 'amount') return Number(b.avg_amount_20d||0) - Number(a.avg_amount_20d||0);
    return priorityScore(b)-priorityScore(a) || String(b.date).localeCompare(String(a.date)) || String(a.stock_id).localeCompare(String(b.stock_id));
  };
}
function riskTags(r){
  const tags=[];
  if(isChase(r)) tags.push('<span class="pill risk">追高</span>');
  if(Number(r.next_open_gap) >= .05) tags.push('<span class="pill risk">高開>5%</span>');
  else if(Number(r.next_open_gap) >= .03) tags.push('<span class="pill">高開>3%</span>');
  if(isLowLiquidity(r)) tags.push('<span class="pill bad">低流動</span>');
  if(r.candidate !== 'A_repo50_c4_40_fixed20') tags.push('<span class="pill muted">非主規格</span>');
  if(!tags.length) tags.push('<span class="pill good-bg">可研究</span>');
  return tags.join(' ');
}
function rowKey(r){ return `${r.date}|${r.stock_id}|${r.price_mode}|${r.candidate}`; }
function externalLinksHtml(r){
  const id = String(r.stock_id).replace(/\.0$/, '');
  return `<div class="external-links">
    <a target="_blank" rel="noopener" href="https://tw.stock.yahoo.com/quote/${id}.TW">Yahoo TW</a>
    <a target="_blank" rel="noopener" href="https://tw.stock.yahoo.com/quote/${id}.TWO">Yahoo TWO</a>
    <a target="_blank" rel="noopener" href="https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID=${id}">Goodinfo</a>
    <a target="_blank" rel="noopener" href="https://www.tradingview.com/chart/?symbol=TWSE%3A${id}">TradingView</a>
    <a target="_blank" rel="noopener" href="https://www.wantgoo.com/stock/${id}">Wantgoo</a>
  </div>`;
}

function renderMainAList(){
  const rows = recentRows.filter(r => r.candidate === 'A_repo50_c4_40_fixed20').sort(compareRows('priority')).slice(0, 6);
  document.getElementById('mainAList').innerHTML = rows.map(r => stockCardHtml(r, true)).join('') || '<div class="empty">近期沒有主規格 A 候選。</div>';
  document.querySelectorAll('#mainAList .stock-card').forEach(card => card.addEventListener('click', () => showDetail(rows.find(r => rowKey(r) === card.dataset.key))));
}

function renderStockCards(){
  const cand = document.getElementById('candidateFilter').value;
  const risk = document.getElementById('riskFilter').value;
  const sort = document.getElementById('sortFilter').value;
  const q = document.getElementById('search').value.trim().toLowerCase();
  let rows = activeRows().filter(r => cand === 'all' || r.candidate === cand).filter(r => matchRisk(r, risk));
  if(q) rows = rows.filter(r => `${r.stock_id} ${r.stock_name} ${r.industry_category}`.toLowerCase().includes(q));
  rows = rows.slice().sort(compareRows(sort));
  document.getElementById('viewHint').textContent = `${document.getElementById('rangeFilter').selectedOptions[0].textContent}｜顯示 ${rows.length} 筆`;
  document.getElementById('stockCards').innerHTML = rows.length ? rows.map(r => stockCardHtml(r)).join('') : '<div class="empty">沒有符合條件的候選。</div>';
  document.querySelectorAll('#stockCards .stock-card').forEach(card => card.addEventListener('click', () => showDetail(rows.find(r => rowKey(r) === card.dataset.key))));
}
function stockCardHtml(r, compact=false){
  const key = rowKey(r);
  return `<button class="stock-card ${compact ? 'compact-card' : ''} ${selectedDetailKey === key ? 'selected' : ''}" data-key="${key}">
    <div class="stock-head">
      <div><strong>${r.stock_id}</strong><span>${r.stock_name || ''}</span></div>
      <em>${priorityLabel(r)} ${priorityScore(r)}</em>
    </div>
    <div class="stock-sub"><span>${r.date}</span><span>${labelMap[r.candidate] || r.candidate}</span><span>${r.industry_category || '—'}</span><span>${r.price_mode}</span></div>
    <div class="metric-row">
      <div><label>20D</label><b>${fmtPct(r.ret_20d)}</b></div>
      <div><label>repo量</label><b>${fmtPct(r.top5_volume_ratio_120)}</b></div>
      <div><label>金額</label><b>${fmtMoney(r.avg_amount_20d)}</b></div>
    </div>
    <div class="stock-tags">${riskTags(r)}</div>
  </button>`;
}
function showDetail(r){
  if(!r) return;
  selectedDetailKey = rowKey(r);
  document.getElementById('detailTitle').textContent = `${r.stock_id} ${r.stock_name || ''}`;
  document.getElementById('detailSubtitle').textContent = `${labelMap[r.candidate] || r.candidate}｜${r.date}｜${classify(r)}｜${priorityLabel(r)} ${priorityScore(r)}`;
  const items = [
    ['產業', r.industry_category], ['價格模式', r.price_mode], ['收盤價', fmtNum(r.close,2)], ['20D金額', fmtMoney(r.avg_amount_20d)],
    ['區間位置', fmtPct(r.range_pos)], ['gap1', fmtPct(r.gap1)], ['gap2', fmtPct(r.gap2)], ['20D漲幅', fmtPct(r.ret_20d)],
    ['最大量距今', `${fmtNum(r.days_since_max_volume,0)}日`], ['repo量比', fmtPct(r.top5_volume_ratio_120)],
    ['訊號日漲幅', fmtPct(r.signal_day_ret_1d)], ['隔日開盤', fmtPct(r.next_open_gap)],
    ['20D excess', fmtPct(r.t1_open_excess_20d)], ['60D excess', fmtPct(r.t1_open_excess_60d)], ['研究分數', priorityScore(r)], ['分類', classify(r)],
  ];
  document.getElementById('detailBody').innerHTML = `<div class="detail-grid">${items.map(([k,v]) => `<div><label>${k}</label><strong>${v ?? '—'}</strong></div>`).join('')}</div><div class="detail-tags">${riskTags(r)}</div>${externalLinksHtml(r)}`;
  renderStockCards();
  renderMainAList();
  document.getElementById('detailPanel').scrollIntoView({behavior:'smooth', block:'nearest'});
}
function clearDetail(){
  selectedDetailKey = null;
  document.getElementById('detailTitle').textContent = '候選細節';
  document.getElementById('detailSubtitle').textContent = '點選卡片後顯示完整欄位。';
  document.getElementById('detailBody').innerHTML = '<div class="detail-empty">尚未選取候選。</div>';
  renderStockCards();
  renderMainAList();
}
load().catch(err=>{document.getElementById('status').textContent='載入失敗'; console.error(err);});
