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
let allRows = [];
let watchRows = [];
let selectedDetailKey = null;

async function load(){
  const [summary, latest, recent, all, watch] = await Promise.all([
    fetch('./data/summary.json').then(r=>r.json()),
    fetch('./data/latest_candidates.json').then(r=>r.json()),
    fetch('./data/recent_candidates.json').then(r=>r.json()),
    fetch('./data/all_candidates.json').then(r=>r.ok ? r.json() : []),
    fetch('./data/watch_states.json').then(r=>r.ok ? r.json() : [])
  ]);
  summaryData = summary;
  latestRows = latest;
  recentRows = recent;
  allRows = all && all.length ? all : [...latest, ...recent];
  watchRows = watch || [];
  document.getElementById('status').textContent = `目前 ${new Date().toLocaleString('zh-TW')}｜最新資料 ${summary.data_through}`;
  renderCards(summary);
  renderCandidateSummary(summary);
  setupFilters();
  renderVolgapSummary();
  renderMainAList();
  renderWatchState();
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

const subtypeFilters = {
  '正常': 'volgapNormal',
  '可救斷層': 'volgapRescue',
  '大量斷層觀察': 'volgapWatch',
  '危險斷層': 'volgapDanger',
  '待補': 'volgapMissing'
};
const subtypeOrder = ['正常', '可救斷層', '大量斷層觀察', '危險斷層', '待補'];
function countSubtype(rows, subtype){ return rows.filter(r => String(r.volgap_subtype_zh || '待補') === subtype).length; }
function subtypeTone(subtype){
  if(subtype === '正常') return 'ok';
  if(subtype === '可救斷層') return 'rescue';
  if(subtype === '危險斷層') return 'danger';
  if(subtype === '待補') return 'missing';
  return 'watch';
}
function renderVolgapSummary(){
  const target = document.getElementById('volgapSummary');
  if(!target) return;
  target.innerHTML = subtypeOrder.map(subtype => {
    const all = countSubtype(allRows, subtype);
    const recent = countSubtype(recentRows, subtype);
    const latest = countSubtype(latestRows, subtype);
    const mainA = allRows.filter(r => r.candidate === 'A_repo50_c4_40_fixed20' && String(r.volgap_subtype_zh || '待補') === subtype).length;
    return `<button class="subtype-card ${subtypeTone(subtype)}" data-risk="${subtypeFilters[subtype]}">
      <div class="subtype-head"><span>${subtype}</span><strong>${all}</strong></div>
      <div class="subtype-metrics"><span>近期 ${recent}</span><span>最新 ${latest}</span><span>A ${mainA}</span></div>
    </button>`;
  }).join('');
  document.querySelectorAll('.subtype-card').forEach(btn => btn.addEventListener('click', () => {
    document.getElementById('rangeFilter').value = 'all';
    document.getElementById('riskFilter').value = btn.dataset.risk;
    renderStockCards();
    document.getElementById('stockCards').scrollIntoView({behavior:'smooth', block:'start'});
  }));
}

function setupFilters(){
  const sel = document.getElementById('candidateFilter');
  [...new Set([...latestRows, ...recentRows, ...allRows].map(r=>r.candidate))].sort().forEach(c=>{
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
function activeRows(){
  const range = document.getElementById('rangeFilter').value;
  if(range === 'all') return allRows;
  return range === 'recent' ? recentRows : latestRows;
}
function isTrue(v){ return v === true || v === 'True' || v === 'true' || v === 1 || v === '1'; }
function isChase(r){ return isTrue(r.risk_signal_day_gt9) || Number(r.next_open_gap) >= .05; }
function isLowLiquidity(r){ return isTrue(r.risk_liquidity_lt100m); }
function isWeakMomentum(r){ return isTrue(r.is_weak_momentum) || (r.candidate === 'A_repo50_c4_40_fixed20' && Number(r.ret_20d) < .15); }
function isFloor15(r){ return isTrue(r.is_floor15_observation) || (r.candidate === 'A_repo50_c4_40_fixed20' && Number(r.ret_20d) >= .15 && Number(r.ret_20d) < .40); }
function isRet60Hot(r){ return Number(r.ret_60d_signal) > 1.5; }
function isVolumeGapWatch(r){ return String(r.volume_gap_risk_zh || '').includes('大量斷層') || ['可救斷層','危險斷層','大量斷層觀察'].includes(String(r.volgap_subtype_zh || '')); }
function isVolgapRescue(r){ return String(r.volgap_subtype_zh || '') === '可救斷層'; }
function isVolgapDanger(r){ return String(r.volgap_subtype_zh || '') === '危險斷層'; }
function isLongMaBear(r){ return isTrue(r.risk_any_long_ma_bear) || Number(r.risk_long_ma_score || 0) < 0; }
function round19TagsText(r){ return String(r.risk_badge_zh || '').split(';').filter(Boolean).join(' / '); }
function classify(r){
  if(r.candidate !== 'A_repo50_c4_40_fixed20') return '非主規格觀察';
  if(isWeakMomentum(r)) return '弱動能觀察';
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
  score += Number(r.volgap_score_impact || 0);
  return Math.round(score);
}
function priorityLabel(r){
  if(r.research_priority_zh) return r.research_priority_zh;
  const s = priorityScore(r);
  if(s >= 82) return '優先研究';
  if(s >= 62) return '次級觀察';
  return '風險觀察';
}
function matchRisk(r, risk){
  if(risk === 'all') return true;
  if(risk === 'clean') return !isChase(r) && !isLowLiquidity(r) && !isWeakMomentum(r) && r.candidate === 'A_repo50_c4_40_fixed20';
  if(risk === 'weak') return isWeakMomentum(r);
  if(risk === 'floor15') return isFloor15(r);
  if(risk === 'chase') return isChase(r);
  if(risk === 'liquidity') return isLowLiquidity(r);
  if(risk === 'ret60hot') return isRet60Hot(r);
  if(risk === 'volgapNormal') return String(r.volgap_subtype_zh || '') === '正常';
  if(risk === 'volgapRescue') return isVolgapRescue(r);
  if(risk === 'volgapWatch') return String(r.volgap_subtype_zh || '') === '大量斷層觀察';
  if(risk === 'volgapDanger') return isVolgapDanger(r);
  if(risk === 'volgapMissing') return String(r.volgap_subtype_zh || '待補') === '待補';
  if(risk === 'volgap') return isVolumeGapWatch(r);
  if(risk === 'longma') return isLongMaBear(r);
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
  if(isWeakMomentum(r)) tags.push('<span class="pill weak">弱動能</span>');
  if(isFloor15(r)) tags.push('<span class="pill floor">floor15觀察</span>');
  if(isChase(r)) tags.push('<span class="pill risk">追高</span>');
  if(Number(r.next_open_gap) >= .05) tags.push('<span class="pill risk">高開>5%</span>');
  else if(Number(r.next_open_gap) >= .03) tags.push('<span class="pill">高開>3%</span>');
  if(isLowLiquidity(r)) tags.push('<span class="pill bad">低流動</span>');
  if(isRet60Hot(r)) tags.push('<span class="pill research">60日>150%</span>');
  if(isVolgapDanger(r)) tags.push('<span class="pill bad">危險斷層</span>');
  else if(isVolgapRescue(r)) tags.push('<span class="pill research">可救斷層</span>');
  else if(isVolumeGapWatch(r)) tags.push(`<span class="pill research">${r.volgap_subtype_zh || r.volume_gap_risk_zh}</span>`);
  if(isLongMaBear(r)) tags.push('<span class="pill bad">長均空頭</span>');
  if(r.risk_badge_zh) tags.push('<span class="pill muted">研究中</span>');
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

function stateClass(state){
  if(String(state).includes('降溫')) return 'cool';
  if(String(state).includes('回測')) return 'retest';
  if(String(state).includes('突破')) return 'breakout';
  if(String(state).includes('降級')) return 'down';
  return 'neutral';
}
function watchStateHtml(r){
  return `<div class="watch-card ${stateClass(r.rearm_state)}">
    <div class="watch-head"><strong>${r.stock_id} ${r.stock_name || ''}</strong><span>${r.rearm_state || '未分類'}</span></div>
    <div class="watch-theme">${r.theme_bucket || '—'}</div>
    <div class="watch-metrics">
      <div><label>訊號後</label><b>${fmtPct(r.post_signal_ret)}</b></div>
      <div><label>距高點</label><b>${fmtPct(r.pullback_from_post_signal_high)}</b></div>
      <div><label>MA20</label><b>${fmtPct(r.ma20_gap)}</b></div>
      <div><label>RSI</label><b>${fmtNum(r.rsi14,1)}</b></div>
    </div>
    <p>${r.rule_reason || ''}</p>
    <em>${r.suggested_action || '觀察'}</em>
  </div>`;
}
function renderWatchState(){
  const target = document.getElementById('watchStateList');
  if(!target) return;
  const rows = (watchRows || []).slice().sort((a,b)=>{
    const order = {'回測觀察區':0,'再啟動突破候選':1,'中性等待':2,'等待降溫':3,'降級-跌破結構':4};
    return (order[a.rearm_state] ?? 9) - (order[b.rearm_state] ?? 9) || Number(b.post_signal_ret||0)-Number(a.post_signal_ret||0);
  });
  document.getElementById('watchStateHint').textContent = summaryData?.watch_state ? `共 ${summaryData.watch_state.rows} 檔｜${summaryData.watch_state.decision}` : 'B類候選生命週期狀態';
  target.innerHTML = rows.length ? rows.map(watchStateHtml).join('') : '<div class="empty">尚無 Watch State 資料。</div>';
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
      <div><label>動能</label><b>${r.momentum_bucket_zh || '—'}</b></div>
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
    ['動能桶', r.momentum_bucket_zh], ['策略角色', r.strategy_role_zh], ['研究優先', r.research_priority_zh || priorityLabel(r)], ['研究標籤', r.research_tags],
    ['資料來源', r.source_type || '—'], ['60日漲幅', fmtPct(r.ret_60d_signal)], ['60日上限', isRet60Hot(r) ? '超過150%' : (r.ret_60d_signal == null ? '待補' : '通過')], ['Round19標籤', round19TagsText(r) || '—'],
    ['top1/top3量', fmtNum(r.top1_to_top3_volume_ratio,2)], ['top1/top5量', fmtNum(r.top1_to_top5_volume_ratio,2)], ['top1/top10量', fmtNum(r.top1_to_top10_volume_ratio,2)], ['量能斷層', r.volume_gap_risk_zh || '—'],
    ['斷層分類', r.volgap_subtype_zh || '—'], ['斷層分數影響', r.volgap_score_impact ?? '—'],
    ['日長均空頭', isTrue(r.risk_daily_long_ma_bear) ? '是' : '否'], ['周長均空頭', isTrue(r.risk_weekly_long_ma_bear) ? '是' : '否'], ['長均分數', r.risk_long_ma_score ?? '—'],
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
