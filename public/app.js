const fmtPct = v => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : `${(Number(v)*100).toFixed(1)}%`;
const fmtMoney = v => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : `${(Number(v)/1e8).toFixed(1)}億`;
const fmtNum = (v, d=2) => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(d);
const labelMap = {
  A_repo50_c4_40_fixed20: 'A 組：先看這組',
  B_magic_c4_40_fixed20: 'B 組：條件放寬',
  C_c4_25_fixed20: 'C 組：條件較嚴'
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
  renderFreshness(summary);
  renderCards(summary);
  renderCandidateSummary(summary);
  setupFilters();
  renderVolgapSummary();
  renderMainAList();
  renderWatchState();
  renderStockCards();
}

function daysBetween(a,b){
  if(!a || !b) return null;
  const da = new Date(`${a}T00:00:00`);
  const db = new Date(`${b}T00:00:00`);
  if(Number.isNaN(da.getTime()) || Number.isNaN(db.getTime())) return null;
  return Math.round((db - da) / 86400000);
}
function todayIso(){ return new Date().toISOString().slice(0,10); }
function renderFreshness(s){
  const today = todayIso();
  const lag = daysBetween(s.data_through, today);
  const lagText = lag !== null && lag > 0 ? `（落後 ${lag} 天）` : '';
  document.getElementById('status').textContent = `目前 ${new Date().toLocaleString('zh-TW')}｜資料只算到 ${s.data_through || '—'}${lagText}`;
  const box = document.getElementById('freshnessNotice');
  if(!box) return;
  if(lag !== null && lag > 2){
    box.className = 'freshness warning';
    box.innerHTML = `<strong>資料沒有更新到今天。</strong><span>這包資料只算到 ${s.data_through}；最近一次找到候選是 ${s.latest_signal_date || '—'}。兩個日期意思不同：一個是資料截止日，一個是最近有股票符合條件的日期。</span>`;
  } else {
    box.className = 'freshness ok';
    box.innerHTML = `<strong>資料日期正常。</strong><span>資料算到 ${s.data_through || '—'}；最近一次找到候選是 ${s.latest_signal_date || '—'}。</span>`;
  }
}
function renderCards(s){
  const main = (s.candidates || []).find(c=>c.candidate === s.main_spec) || {};
  const cards = [
    ['最近有候選', s.latest_signal_date || '—', '這不是更新日，是最近一次有股票符合條件'],
    ['那天有幾筆', s.latest_candidate_rows, '同一股票可能有原始價 / 還原價兩筆'],
    ['A 組歷史筆數', main.rows ?? '—', 'A 組是目前主要先看的清單'],
    ['A 組平均勝出大盤', fmtPct(main.median_t1_open_excess_20d), `20 天後勝率 ${fmtPct(main.win_t1_open_excess_20d)}`]
  ];
  document.getElementById('cards').innerHTML = cards.map(c=>`<div class="card"><div class="label">${c[0]}</div><div class="value">${c[1]}</div><div class="hint">${c[2]}</div></div>`).join('');
}

function renderCandidateSummary(s){
  document.getElementById('candidateSummary').innerHTML = (s.candidates || []).map(c => `
    <button class="spec-card ${specTone[c.candidate] || ''}" data-candidate="${c.candidate}">
      <div class="spec-top"><span>${labelMap[c.candidate] || c.candidate}</span><strong>${c.rows}</strong></div>
      <div class="spec-metrics">
        <span>最近出現 ${c.latest_date}</span>
        <span>原始價 ${c.raw_rows} / 還原價 ${c.adjusted_rows}</span>
        <span>20 天平均勝大盤 ${fmtPct(c.median_t1_open_excess_20d)}</span>
        <span>20 天勝率 ${fmtPct(c.win_t1_open_excess_20d)}</span>
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
const subtypeLabels = {
  '正常': '正常',
  '可救斷層': '有落差但可看',
  '大量斷層觀察': '量集中，要小心',
  '危險斷層': '先避開',
  '待補': '資料不夠'
};
const subtypeHints = {
  '正常': '成交量沒有明顯集中在少數幾天',
  '可救斷層': '成交量有落差，但還沒有嚴重到要直接排後面',
  '大量斷層觀察': '成交量集中在少數幾天，容易是假熱度，要小心',
  '危險斷層': '成交量落差很明顯，先當成高風險',
  '待補': '缺少判斷量能落差需要的資料'
};
const subtypeOrder = ['正常', '可救斷層', '大量斷層觀察', '危險斷層', '待補'];
function subtypeLabel(subtype){ return subtypeLabels[subtype] || subtype || '資料不足'; }
function countSubtype(rows, subtype){ return rows.filter(r => String(r.volgap_subtype_zh || '待補') === subtype).length; }
function subtypeTone(subtype){
  if(subtype === '正常') return 'ok';
  if(subtype === '可救斷層') return 'rescue';
  if(subtype === '危險斷層') return 'danger';
  if(subtype === '待補') return 'missing';
  return 'watch';
}
function applyCandidateFilter({range='all', candidate='all', risk='all'}={}){
  document.getElementById('rangeFilter').value = range;
  document.getElementById('candidateFilter').value = candidate;
  document.getElementById('riskFilter').value = risk;
  renderStockCards();
}
function renderVolgapSummary(){
  const target = document.getElementById('volgapSummary');
  if(!target) return;
  target.innerHTML = subtypeOrder.map(subtype => {
    const all = countSubtype(allRows, subtype);
    const recent = countSubtype(recentRows, subtype);
    const latest = countSubtype(latestRows, subtype);
    const mainA = allRows.filter(r => r.candidate === 'A_repo50_c4_40_fixed20' && String(r.volgap_subtype_zh || '待補') === subtype).length;
    return `<button class="subtype-card ${subtypeTone(subtype)}" data-risk="${subtypeFilters[subtype]}" title="${subtypeHints[subtype] || ''}">
      <div class="subtype-head"><span>${subtypeLabel(subtype)}</span><strong>${all}</strong></div>
      <div class="subtype-metrics"><span>今年 ${recent}</span><span>最近日 ${latest}</span><span>A組 ${mainA}</span></div>
    </button>`;
  }).join('');
  document.querySelectorAll('.subtype-card').forEach(btn => btn.addEventListener('click', () => {
    applyCandidateFilter({range:'all', risk:btn.dataset.risk});
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
  if(r.candidate !== 'A_repo50_c4_40_fixed20') return '不是優先清單';
  if(isWeakMomentum(r)) return '漲勢偏弱';
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
function displayPriorityLabel(r){
  return String(priorityLabel(r) || '')
    .replace('優先研究', '先看')
    .replace('中優先-有交易風險', '可看，但先查風險')
    .replace('低優先-需人工確認', '先放後面')
    .replace('規格觀察', '非A組，參考用')
    .replace('次級觀察', '晚點看')
    .replace('風險觀察', '風險高，先確認');
}
function priceModeLabel(mode){
  if(mode === 'raw') return '原始股價';
  if(mode === 'adjusted') return '還原股價';
  return mode || '—';
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
  if(isWeakMomentum(r)) tags.push('<span class="pill weak">漲勢偏弱</span>');
  if(isFloor15(r)) tags.push('<span class="pill floor" title="20日漲幅至少15%，但不是買點">漲幅有過15%</span>');
  if(isChase(r)) tags.push('<span class="pill risk">可能追高</span>');
  if(Number(r.next_open_gap) >= .05) tags.push('<span class="pill risk">開盤高於5%</span>');
  else if(Number(r.next_open_gap) >= .03) tags.push('<span class="pill">開盤高於3%</span>');
  if(isLowLiquidity(r)) tags.push('<span class="pill bad">流動性不足</span>');
  if(isRet60Hot(r)) tags.push('<span class="pill research">前面已漲很多</span>');
  if(isVolgapDanger(r)) tags.push('<span class="pill bad">量太集中，先避開</span>');
  else if(isVolgapRescue(r)) tags.push('<span class="pill research">量有落差但可看</span>');
  else if(isVolumeGapWatch(r)) tags.push(`<span class="pill research">${subtypeLabel(r.volgap_subtype_zh) || '量要小心'}</span>`);
  if(isLongMaBear(r)) tags.push('<span class="pill bad">長期均線偏空</span>');
  if(r.risk_badge_zh) tags.push('<span class="pill muted">還要人工看圖</span>');
  if(r.candidate !== 'A_repo50_c4_40_fixed20') tags.push('<span class="pill muted">不是A組</span>');
  if(!tags.length) tags.push('<span class="pill good-bg">可以先看</span>');
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
  document.getElementById('watchStateHint').textContent = summaryData?.watch_state ? `共 ${summaryData.watch_state.rows} 檔｜這裡只是追蹤名單，不是買進訊號。` : 'B 組追蹤名單';
  target.innerHTML = rows.length ? rows.map(watchStateHtml).join('') : '<div class="empty">尚無 Watch State 資料。</div>';
}

function renderMainAList(){
  const target = document.getElementById('mainAList');
  const rows = recentRows.filter(r => r.candidate === 'A_repo50_c4_40_fixed20').sort(compareRows('priority'));
  if(!rows.length){ target.innerHTML = '<div class="empty">近期沒有主規格 A 候選。</div>'; return; }
  const byKey = new Map(rows.map(r => [rowKey(r), r]));
  target.innerHTML = subtypeOrder.map(subtype => {
    const part = rows.filter(r => String(r.volgap_subtype_zh || '待補') === subtype).slice(0, 3);
    const count = rows.filter(r => String(r.volgap_subtype_zh || '待補') === subtype).length;
    return `<section class="main-a-group ${subtypeTone(subtype)}">
      <button class="main-a-head" data-risk="${subtypeFilters[subtype]}">
        <span>A 組｜${subtypeLabel(subtype)}</span><strong>${count}</strong><em>看此分類</em>
      </button>
      <div class="main-a-cards">${part.length ? part.map(r => stockCardHtml(r, true)).join('') : '<div class="empty mini">近期無候選</div>'}</div>
    </section>`;
  }).join('');
  document.querySelectorAll('#mainAList .stock-card').forEach(card => card.addEventListener('click', () => showDetail(byKey.get(card.dataset.key))));
  document.querySelectorAll('#mainAList .main-a-head').forEach(btn => btn.addEventListener('click', () => {
    applyCandidateFilter({range:'recent', candidate:'A_repo50_c4_40_fixed20', risk:btn.dataset.risk});
    document.getElementById('stockCards').scrollIntoView({behavior:'smooth', block:'start'});
  }));
}

function renderStockCards(){
  const cand = document.getElementById('candidateFilter').value;
  const risk = document.getElementById('riskFilter').value;
  const sort = document.getElementById('sortFilter').value;
  const q = document.getElementById('search').value.trim().toLowerCase();
  let rows = activeRows().filter(r => cand === 'all' || r.candidate === cand).filter(r => matchRisk(r, risk));
  if(q) rows = rows.filter(r => `${r.stock_id} ${r.stock_name} ${r.industry_category}`.toLowerCase().includes(q));
  rows = rows.slice().sort(compareRows(sort));
  document.getElementById('viewHint').textContent = `${document.getElementById('rangeFilter').selectedOptions[0].textContent}｜現在顯示 ${rows.length} 筆`;
  document.getElementById('stockCards').innerHTML = rows.length ? rows.map(r => stockCardHtml(r)).join('') : '<div class="empty">沒有符合條件的候選。</div>';
  document.querySelectorAll('#stockCards .stock-card').forEach(card => card.addEventListener('click', () => showDetail(rows.find(r => rowKey(r) === card.dataset.key))));
}
function stockCardHtml(r, compact=false){
  const key = rowKey(r);
  return `<button class="stock-card ${compact ? 'compact-card' : ''} ${selectedDetailKey === key ? 'selected' : ''}" data-key="${key}">
    <div class="stock-head">
      <div><strong>${r.stock_id}</strong><span>${r.stock_name || ''}</span></div>
      <em>${displayPriorityLabel(r)}｜${priorityScore(r)}分</em>
    </div>
    <div class="stock-sub"><span>${r.date}</span><span>${labelMap[r.candidate] || r.candidate}</span><span>${r.industry_category || '—'}</span><span>${priceModeLabel(r.price_mode)}</span></div>
    <div class="metric-row">
      <div><label>近20天漲幅</label><b>${fmtPct(r.ret_20d)}</b></div>
      <div><label>漲幅區間</label><b>${r.momentum_bucket_zh || '—'}</b></div>
      <div><label>近20天日均成交</label><b>${fmtMoney(r.avg_amount_20d)}</b></div>
    </div>
    <div class="stock-tags">${riskTags(r)}</div>
  </button>`;
}
function detailSectionHtml(title, items){
  return `<section class="detail-section"><h3>${title}</h3><div class="detail-grid">${items.map(([k,v,hint]) => `<div${hint ? ` title="${hint}"` : ''}><label>${k}</label><strong>${v ?? '—'}</strong></div>`).join('')}</div></section>`;
}
function showDetail(r){
  if(!r) return;
  selectedDetailKey = rowKey(r);
  document.getElementById('detailTitle').textContent = `${r.stock_id} ${r.stock_name || ''}`;
  document.getElementById('detailSubtitle').textContent = `${labelMap[r.candidate] || r.candidate}｜${r.date}｜${classify(r)}｜${displayPriorityLabel(r)} ${priorityScore(r)}`;
  const sections = [
    ['基本資料', [
      ['產業', r.industry_category], ['股價版本', priceModeLabel(r.price_mode), `原始值：${r.price_mode || '—'}`], ['收盤價', fmtNum(r.close,2)], ['資料來源', r.source_type || '—']
    ]],
    ['價格與表現', [
      ['近20天日均成交', fmtMoney(r.avg_amount_20d)], ['近20天漲幅', fmtPct(r.ret_20d)], ['當天漲幅', fmtPct(r.signal_day_ret_1d)], ['隔天開盤變化', fmtPct(r.next_open_gap)],
      ['股價在區間偏高處', fmtPct(r.range_pos)], ['短均線強度1', fmtPct(r.gap1), '原欄位：gap1'], ['短均線強度2', fmtPct(r.gap2), '原欄位：gap2'], ['20天後勝大盤', fmtPct(r.t1_open_excess_20d), '原欄位：20D excess'], ['60天後勝大盤', fmtPct(r.t1_open_excess_60d), '原欄位：60D excess']
    ]],
    ['量能集中度', [
      ['最大成交量距今', `${fmtNum(r.days_since_max_volume,0)}日`], ['前5大量占比', fmtPct(r.top5_volume_ratio_120), '越高代表成交量越集中'],
      ['最大量 / 前3大', fmtNum(r.top1_to_top3_volume_ratio,2)], ['最大量 / 前5大', fmtNum(r.top1_to_top5_volume_ratio,2)], ['最大量 / 前10大', fmtNum(r.top1_to_top10_volume_ratio,2)],
      ['成交量是否太集中', r.volume_gap_risk_zh || '—'], ['白話分類', subtypeLabel(r.volgap_subtype_zh), `原研究名：${r.volgap_subtype_zh || '—'}`], ['排序扣分', r.volgap_score_impact ?? '—']
    ]],
    ['風險檢查', [
      ['後來60天漲幅', fmtPct(r.ret_60d_signal)], ['是否已漲太多', isRet60Hot(r) ? '超過150%' : (r.ret_60d_signal == null ? '待補' : '未超過')], ['其他提醒', round19TagsText(r) || '—', '原欄位：Round19標籤'],
      ['日線長均偏空', isTrue(r.risk_daily_long_ma_bear) ? '是' : '否'], ['週線長均偏空', isTrue(r.risk_weekly_long_ma_bear) ? '是' : '否'], ['長均分數', r.risk_long_ma_score ?? '—']
    ]],
    ['研究狀態', [
      ['查看分數', priorityScore(r)], ['目前判斷', classify(r)], ['漲幅區間', r.momentum_bucket_zh], ['原始分組', r.strategy_role_zh], ['查看順序', displayPriorityLabel(r)], ['原始標籤', r.research_tags]
    ]]
  ];
  document.getElementById('detailBody').innerHTML = `<div class="detail-sections">${sections.map(([title, items]) => detailSectionHtml(title, items)).join('')}</div><div class="detail-tags">${riskTags(r)}</div>${externalLinksHtml(r)}`;
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
