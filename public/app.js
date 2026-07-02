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
let latestGroups = [];
let recentGroups = [];
let allGroups = [];
let watchRows = [];
let selectedDetailKey = null;
let currentKlineKey = null;
let currentKlineRow = null;
let currentKlinePayloadRows = [];
let currentKlineSignalDate = null;
let currentKlineChart = null;
let currentKlineResizeObserver = null;
const defaultKlineOptions = {range:'1Y', ma:true, volume:true, signal:true, scale:'normal', type:'candles', measure:false};
let currentKlineOptions = loadKlineOptions();

function loadKlineOptions(){
  try{
    const saved = JSON.parse(localStorage.getItem('magic26:kline-options') || '{}');
    return {...defaultKlineOptions, ...saved, range: (saved.range === 'ALL' ? 'ALL' : '1Y')};
  }catch(_){
    return {...defaultKlineOptions};
  }
}
function saveKlineOptions(){
  try{ localStorage.setItem('magic26:kline-options', JSON.stringify(currentKlineOptions)); }catch(_){ /* ignore */ }
}
function resetCurrentKlineView(){
  currentKlineChart?.timeScale().fitContent();
  currentKlineChart?.priceScale('right').applyOptions({autoScale:true});
}
function setKlineRange(range){
  currentKlineOptions.range = range;
  saveKlineOptions();
  document.querySelectorAll('[data-kline-range]').forEach(b => b.classList.toggle('active', b.dataset.klineRange === range));
  renderCurrentKlineFromState();
}
function setKlineScale(scale){
  currentKlineOptions.scale = scale;
  saveKlineOptions();
  document.querySelectorAll('[data-kline-scale]').forEach(b => b.classList.toggle('active', b.dataset.klineScale === scale));
  applyKlineScaleMode();
}

function setKlineType(type){
  currentKlineOptions.type = type;
  saveKlineOptions();
  document.querySelectorAll('[data-kline-type]').forEach(b => b.classList.toggle('active', b.dataset.klineType === type));
  renderCurrentKlineFromState();
}


function setKlineMeasure(active){
  currentKlineOptions.measure = !!active;
  saveKlineOptions();
  const panel = document.getElementById('klinePanel');
  panel?.querySelector('[data-kline-action="measure"]')?.classList.toggle('active', currentKlineOptions.measure);
  const info = document.getElementById('klineMeasureInfo');
  if(info){
    info.dataset.active = String(currentKlineOptions.measure);
    info.textContent = currentKlineOptions.measure ? '測量：點第一根作為起點，再點第二根作為終點' : '測量：關閉';
  }
}
function resetKlineMeasure(){
  window.__magic26KlineMeasureStart = null;
  window.__magic26KlineMeasureEnd = null;
  const info = document.getElementById('klineMeasureInfo');
  if(info){
    info.dataset.start = ''; info.dataset.end = ''; info.dataset.days = ''; info.dataset.pct = '';
    info.textContent = currentKlineOptions.measure ? '測量：點第一根作為起點，再點第二根作為終點' : '測量：關閉';
  }
}

function bindGlobalKlineShortcuts(){
  if(window.__magic26KlineShortcutsBound) return;
  window.__magic26KlineShortcutsBound = true;
  document.addEventListener('keydown', ev => {
    const tag = (ev.target?.tagName || '').toLowerCase();
    if(tag === 'input' || tag === 'select' || tag === 'textarea') return;
    if(!document.getElementById('klinePanel')) return;
    const key = ev.key.toLowerCase();
    if(key === 'escape' && document.getElementById('klinePanel')?.classList.contains('fullscreen')){ ev.preventDefault(); toggleKlineFullscreen(false); return; }
    if(key === 'r'){ ev.preventDefault(); resetCurrentKlineView(); return; }
    const rangeMap = {'1':'1Y','2':'ALL'};
    if(rangeMap[key]){ ev.preventDefault(); setKlineRange(rangeMap[key]); }
  });
}

async function load(){
  bindGlobalKlineShortcuts();
  const [summary, latest, recent, all, latestSig, recentSig, allSig, watch] = await Promise.all([
    fetch('./data/summary.json').then(r=>r.json()),
    fetch('./data/latest_candidates.json').then(r=>r.json()),
    fetch('./data/recent_candidates.json').then(r=>r.json()),
    fetch('./data/all_candidates.json').then(r=>r.ok ? r.json() : []),
    fetch('./data/latest_signal_groups.json?v=20260701y').then(r=>r.ok ? r.json() : []),
    fetch('./data/recent_signal_groups.json?v=20260701y').then(r=>r.ok ? r.json() : []),
    fetch('./data/all_signal_groups.json?v=20260701y').then(r=>r.ok ? r.json() : []),
    fetch('./data/watch_states.json').then(r=>r.ok ? r.json() : [])
  ]);
  summaryData = summary;
  latestRows = latest;
  recentRows = recent;
  allRows = all && all.length ? all : [...latest, ...recent];
  latestGroups = latestSig && latestSig.length ? latestSig : groupRows(latestRows);
  recentGroups = recentSig && recentSig.length ? recentSig : groupRows(recentRows);
  allGroups = allSig && allSig.length ? allSig : groupRows(allRows);
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
  const cards = [
    ['資料算到', s.data_through || '—', '這是目前資料截止日'],
    ['最近出訊號', s.latest_signal_date || '—', '這不是更新日，是最近一次有股票符合條件'],
    ['今日主清單', `${s.latest_signal_groups ?? s.latest_candidate_rows ?? '—'} 檔`, '同股同日已合併；原始 / 還原與 A/B 版本收在卡片裡']
  ];
  document.getElementById('cards').innerHTML = cards.map(c=>`<div class="card compact-kpi"><div class="label">${c[0]}</div><div class="value">${c[1]}</div><div class="hint">${c[2]}</div></div>`).join('');
}

function renderCandidateSummary(s){
  document.getElementById('candidateSummary').innerHTML = (s.candidates || []).map(c => `
    <button class="spec-card compact-spec ${specTone[c.candidate] || ''}" data-candidate="${c.candidate}">
      <span>${labelMap[c.candidate] || c.candidate}</span>
      <strong>${c.rows}</strong>
      <em>最近 ${c.latest_date}｜20天勝率 ${fmtPct(c.win_t1_open_excess_20d)}</em>
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
    return `<button class="subtype-card compact-subtype ${subtypeTone(subtype)}" data-risk="${subtypeFilters[subtype]}" title="${subtypeHints[subtype] || ''}">
      <span>${subtypeLabel(subtype)}</span><strong>${all}</strong><em>今年 ${recent}｜最近 ${latest}｜A ${mainA}</em>
    </button>`;
  }).join('');
  document.querySelectorAll('.subtype-card').forEach(btn => btn.addEventListener('click', () => {
    applyCandidateFilter({range:'all', risk:btn.dataset.risk});
    document.getElementById('stockCards').scrollIntoView({behavior:'smooth', block:'start'});
  }));
}

function setupFilters(){
  const sel = document.getElementById('candidateFilter');
  [...new Set([...latestGroups, ...recentGroups, ...allGroups].flatMap(r=>r.hit_candidates || [r.candidate]))].sort((a,b)=>candidateRank(a)-candidateRank(b)).forEach(c=>{
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
function groupRows(rows){
  const by = new Map();
  (rows || []).forEach(r => {
    const key = `${r.date}|${r.stock_id}`;
    if(!by.has(key)) by.set(key, []);
    by.get(key).push(r);
  });
  return [...by.values()].map(part => {
    const sorted = part.slice().sort((a,b)=>candidateRank(a.candidate)-candidateRank(b.candidate) || priceModeRank(a.price_mode)-priceModeRank(b.price_mode));
    const r = {...sorted[0]};
    const hit = [...new Set(sorted.map(x=>x.candidate))].sort((a,b)=>candidateRank(a)-candidateRank(b));
    const modes = [...new Set(sorted.map(x=>x.price_mode))].sort((a,b)=>priceModeRank(a)-priceModeRank(b));
    r.signal_group_id = `${r.stock_id}_${r.date}`;
    r.signal_date = r.date;
    r.hit_candidates = hit;
    r.hit_candidate_labels = hit.map(c=>shortCandidateLabel(c));
    r.price_modes = modes;
    r.price_mode_labels = modes.map(m=>m === 'adjusted' ? '還原價' : '原始價');
    r.alias_count = sorted.length;
    r.alias_rows = sorted;
    r.primary_reason = primaryReason(r);
    r.risk_reason = riskReasonText(r);
    r.priority_reason = displayPriorityLabel(r);
    return r;
  });
}
function candidateRank(c){ return c === 'A_repo50_c4_40_fixed20' ? 0 : c === 'B_magic_c4_40_fixed20' ? 1 : c === 'C_c4_25_fixed20' ? 2 : 9; }
function priceModeRank(m){ return m === 'raw' ? 0 : 1; }
function shortCandidateLabel(c){ return c === 'A_repo50_c4_40_fixed20' ? 'A組主清單' : c === 'B_magic_c4_40_fixed20' ? 'B組補看' : c === 'C_c4_25_fixed20' ? 'C組較嚴' : (labelMap[c] || c || '未分類'); }
function groupKey(r){ return r.signal_group_id || `${r.stock_id}_${r.date}`; }
function groupHitText(r){ return (r.hit_candidate_labels || (r.hit_candidates || [r.candidate]).map(shortCandidateLabel)).join(' / '); }
function groupModeText(r){ return (r.price_mode_labels || (r.price_modes || [r.price_mode]).map(m => m === 'adjusted' ? '還原價' : '原始價')).join(' / '); }
function hasCandidate(r, cand){ return cand === 'all' || (r.hit_candidates || [r.candidate]).includes(cand) || r.candidate === cand; }
function primaryReason(r){ return r.primary_reason || `${shortCandidateLabel(r.candidate)}命中；近20天漲幅 ${fmtPct(r.ret_20d)}，近20日均成交 ${fmtMoney(r.avg_amount_20d)}`; }
function riskReasonText(r){
  if(r.risk_reason) return r.risk_reason;
  const risks=[];
  if(isChase(r)) risks.push(`隔日開盤 ${fmtPct(r.next_open_gap)}，可能有追高風險`);
  if(isLowLiquidity(r)) risks.push('流動性不足');
  if(isVolgapDanger(r)) risks.push('成交量太集中，先避開');
  else if(isVolgapRescue(r)) risks.push('成交量有落差，但仍可看圖');
  else if(isVolumeGapWatch(r)) risks.push('成交量集中在少數幾天，要小心');
  if(isLongMaBear(r)) risks.push('長期均線偏空');
  if(isRet60Hot(r)) risks.push('前面60天已漲很多');
  return risks.length ? risks.join('；') : '主要風險不明顯，仍需看圖確認';
}

function cardWhyText(r){
  const group = (r.hit_candidate_labels || []).includes('A組主清單') ? '進入 A 組主清單' : `${groupHitText(r)}命中`;
  return `最近 20 天漲了 ${fmtPct(r.ret_20d)}，近20日均成交 ${fmtMoney(r.avg_amount_20d)}，所以${group}。`;
}
function riskV2ShortHint(r){
  const hint = String(r.risk_v2_action_hint_zh || '').trim();
  if(!hint) return '';
  return hint
    .replace('；仍需看圖形與基本面', '')
    .replace('；等回檔或整理後再研究', '')
    .replace('；已偏追高，不建議直接追價', '｜已偏追高')
    .replace('；只保留研究紀錄', '');
}
function riskV2Headline(r){
  const badge = String(r.risk_v2_primary_badge_zh || '').trim();
  const hint = riskV2ShortHint(r);
  if(badge && hint && hint !== badge) return `${badge}｜${hint.replace(`${badge}｜`, '')}`;
  return badge || displayPriorityLabel(r);
}
function riskV2ListText(value){
  if(Array.isArray(value)) return value.filter(Boolean).join('；');
  return String(value || '').split(';').filter(Boolean).join('；');
}
function riskV2DisplayOnlyText(r){ return isTrue(r.risk_v2_is_display_only) ? '只作研究顯示，不是買賣訊號' : '—'; }
function cardCautionText(r){
  if(r.risk_v2_action_hint_zh) return r.risk_v2_action_hint_zh;
  const risk = riskReasonText(r);
  if(String(risk).includes('追高') || String(risk).includes('隔日開盤')) return `隔天開盤高 ${fmtPct(r.next_open_gap)}，不要直接追價。`;
  if(String(risk).includes('流動性') || isLowLiquidity(r)) return '流動性不足，先確認是否容易進出。';
  if(String(risk).includes('太集中') || isVolgapDanger(r)) return '成交量太集中，先避開，除非看圖後確認不是假熱度。';
  if(String(risk).includes('集中') || isVolumeGapWatch(r)) return '成交量集中在少數幾天，要看圖確認熱度是否可靠。';
  if(String(risk).includes('長期均線') || isLongMaBear(r)) return '長期均線偏空，先看圖確認結構。';
  if(String(risk).includes('60天') || isRet60Hot(r)) return '前面 60 天已漲很多，先等降溫或回測。';
  return '沒有明顯紅旗，但仍要打開 K 線確認。';
}
function cardVersionText(r){
  return `${groupHitText(r)}；${groupModeText(r)}都成立，${r.alias_count || 1} 筆版本已合併。`;
}

function activeRows(){
  const range = document.getElementById('rangeFilter').value;
  if(range === 'all') return allGroups;
  return range === 'recent' ? recentGroups : latestGroups;
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
  const rows = recentGroups.filter(r => hasCandidate(r, 'A_repo50_c4_40_fixed20')).sort(compareRows('priority'));
  if(!rows.length){ target.innerHTML = '<div class="empty">近期沒有主規格 A 候選。</div>'; return; }
  const byKey = new Map(rows.map(r => [groupKey(r), r]));
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
  let rows = activeRows().filter(r => hasCandidate(r, cand)).filter(r => matchRisk(r, risk));
  if(q) rows = rows.filter(r => `${r.stock_id} ${r.stock_name} ${r.industry_category}`.toLowerCase().includes(q));
  rows = rows.slice().sort(compareRows(sort));
  document.getElementById('viewHint').textContent = `今日主清單｜${document.getElementById('rangeFilter').selectedOptions[0].textContent}｜${rows.length} 檔（同股同日已合併）`;
  document.getElementById('stockCards').innerHTML = rows.length ? rows.map(r => stockCardHtml(r)).join('') : '<div class="empty">沒有符合條件的候選。</div>';
  document.querySelectorAll('#stockCards .stock-card').forEach(card => card.addEventListener('click', () => showDetail(rows.find(r => groupKey(r) === card.dataset.key))));
}
function stockCardHtml(r, compact=false){
  const key = groupKey(r);
  return `<button class="stock-card signal-card ${compact ? 'compact-card' : ''} ${selectedDetailKey === key ? 'selected' : ''}" data-key="${key}">
    <div class="stock-head">
      <div><strong>${r.stock_id}</strong><span>${r.stock_name || ''}</span></div>
      <em>${riskV2Headline(r)}｜${priorityScore(r)}分</em>
    </div>
    <div class="signal-line"><b>出訊號：${r.signal_date || r.date}</b><span>${groupHitText(r)}</span></div>
    <div class="signal-reason"><label>為什麼出現</label><span>${cardWhyText(r)}</span></div>
    <div class="signal-reason risk"><label>要小心</label><span>${cardCautionText(r)}</span></div>
    <div class="signal-reason version"><label>版本</label><span>${cardVersionText(r)}</span></div>
    <div class="stock-sub"><span>${r.industry_category || '—'}</span><span>${groupModeText(r)}</span><span>版本 ${r.alias_count || 1} 筆已合併</span></div>
    <div class="metric-row">
      <div><label>近20天漲幅</label><b>${fmtPct(r.ret_20d)}</b></div>
      <div><label>日均成交</label><b>${fmtMoney(r.avg_amount_20d)}</b></div>
      <div><label>隔日開盤</label><b>${fmtPct(r.next_open_gap)}</b></div>
    </div>
  </button>`;
}

function klineUrl(r){
  const mode = r.price_mode === 'adjusted' ? 'adj' : 'raw';
  return `./data/kline/${mode}_${r.stock_id}.json`;
}
function klineModeLabel(mode){ return mode === 'adjusted' ? '還原價' : '原始價'; }
function klinePanelHtml(r){
  const mode = r.price_mode === 'adjusted' ? 'adjusted' : 'raw';
  return `<section class="kline-panel" id="klinePanel" data-kline-key="${rowKey(r)}">
    <div class="kline-head"><div><h3>K 線圖</h3><p>互動圖表：十字線、成交量、MA5 / MA20 / MA60、候選日標記。資料到看板截止日。</p></div><span id="klineStatus">載入中…</span></div>
    <div class="kline-toolbar" id="klineToolbar">
      <div class="kline-tool-group" aria-label="價格版本">
        <button type="button" data-kline-mode="raw" class="${mode === 'raw' ? 'active' : ''}">原始價</button>
        <button type="button" data-kline-mode="adjusted" class="${mode === 'adjusted' ? 'active' : ''}">還原價</button>
      </div>
      <div class="kline-tool-group" aria-label="時間區間">
        ${['1Y','ALL'].map(x => `<button type="button" data-kline-range="${x}" class="${currentKlineOptions.range === x ? 'active' : ''}">${x === 'ALL' ? '全部' : x}</button>`).join('')}
      </div>
      <label><input type="checkbox" data-kline-toggle="ma" ${currentKlineOptions.ma ? 'checked' : ''}> MA</label>
      <label><input type="checkbox" data-kline-toggle="volume" ${currentKlineOptions.volume ? 'checked' : ''}> 成交量</label>
      <label><input type="checkbox" data-kline-toggle="signal" ${currentKlineOptions.signal ? 'checked' : ''}> 候選日</label>
      <div class="kline-tool-group" aria-label="價格軸模式">
        <button type="button" data-kline-scale="normal" class="${currentKlineOptions.scale === 'normal' ? 'active' : ''}">一般</button>
        <button type="button" data-kline-scale="percentage" class="${currentKlineOptions.scale === 'percentage' ? 'active' : ''}">百分比</button>
        <button type="button" data-kline-scale="log" class="${currentKlineOptions.scale === 'log' ? 'active' : ''}">對數</button>
      </div>
      <div class="kline-tool-group" aria-label="圖表型態">
        <button type="button" data-kline-type="candles" class="${currentKlineOptions.type === 'candles' ? 'active' : ''}">Candles</button>
        <button type="button" data-kline-type="bars" class="${currentKlineOptions.type === 'bars' ? 'active' : ''}">Bars</button>
        <button type="button" data-kline-type="line" class="${currentKlineOptions.type === 'line' ? 'active' : ''}">Line</button>
        <button type="button" data-kline-type="area" class="${currentKlineOptions.type === 'area' ? 'active' : ''}">Area</button>
      </div>
      <button type="button" class="kline-action" data-kline-action="measure">測量</button>
      <button type="button" class="kline-action" data-kline-action="reset-measure">清除測量</button>
      <button type="button" class="kline-action" data-kline-action="reset">重置</button>
      <button type="button" class="kline-action" data-kline-action="fullscreen">放大</button>
    </div>
    <div class="kline-measure-info" id="klineMeasureInfo" data-active="false">測量：關閉</div>
    <div class="kline-cursor-info" id="klineCursorInfo" data-date="">移到圖上看 O / H / L / C / 漲跌幅 / 成交量</div>
    <div class="kline-legend" id="klineLegend">移到圖上看 OHLC / MA</div>
    <div class="kline-chart-wrap">
      <div class="kline-chart" id="klineChart" role="img" aria-label="${r.stock_id} K 線圖"></div>
      <div class="kline-tooltip" id="klineTooltip" hidden></div>
      <div class="kline-axis-label price" id="klinePriceLabel" hidden></div>
      <div class="kline-axis-label time" id="klineTimeLabel" hidden></div>
    </div>
  </section>`;
}
function bindKlineToolbar(){
  const panel = document.getElementById('klinePanel');
  if(!panel) return;
  panel.querySelectorAll('[data-kline-range]').forEach(btn => btn.addEventListener('click', () => setKlineRange(btn.dataset.klineRange)));
  panel.querySelectorAll('[data-kline-toggle]').forEach(input => input.addEventListener('change', () => {
    currentKlineOptions[input.dataset.klineToggle] = input.checked;
    saveKlineOptions();
    renderCurrentKlineFromState();
  }));
  panel.querySelectorAll('[data-kline-scale]').forEach(btn => btn.addEventListener('click', () => setKlineScale(btn.dataset.klineScale)));
  panel.querySelectorAll('[data-kline-type]').forEach(btn => btn.addEventListener('click', () => setKlineType(btn.dataset.klineType)));
  panel.querySelector('[data-kline-action="measure"]')?.addEventListener('click', () => { setKlineMeasure(!currentKlineOptions.measure); resetKlineMeasure(); });
  panel.querySelector('[data-kline-action="reset-measure"]')?.addEventListener('click', () => resetKlineMeasure());
  panel.querySelector('[data-kline-action="measure"]')?.classList.toggle('active', currentKlineOptions.measure);
  panel.querySelector('[data-kline-action="reset"]')?.addEventListener('click', () => resetCurrentKlineView());
  panel.querySelector('[data-kline-action="fullscreen"]')?.addEventListener('click', () => toggleKlineFullscreen());
  panel.querySelectorAll('[data-kline-mode]').forEach(btn => btn.addEventListener('click', () => {
    if(!currentKlineRow) return;
    const mode = btn.dataset.klineMode;
    panel.querySelectorAll('[data-kline-mode]').forEach(b => b.classList.toggle('active', b === btn));
    renderKline({...currentKlineRow, price_mode: mode});
  }));
}

function klineScaleMode(){
  if(currentKlineOptions.scale === 'percentage') return LightweightCharts.PriceScaleMode.Percentage;
  if(currentKlineOptions.scale === 'log') return LightweightCharts.PriceScaleMode.Logarithmic;
  return LightweightCharts.PriceScaleMode.Normal;
}
function applyKlineScaleMode(){
  if(!currentKlineChart || !window.LightweightCharts) return;
  currentKlineChart.priceScale('right').applyOptions({mode:klineScaleMode(), autoScale:true});
  const chart = document.getElementById('klineChart');
  if(chart) chart.dataset.scaleMode = currentKlineOptions.scale;
}
function toggleKlineFullscreen(force){
  const panel = document.getElementById('klinePanel');
  if(!panel) return;
  const active = typeof force === 'boolean' ? force : !panel.classList.contains('fullscreen');
  panel.classList.toggle('fullscreen', active);
  document.body.classList.toggle('kline-fullscreen-open', active);
  const btn = panel.querySelector('[data-kline-action="fullscreen"]');
  if(btn) btn.textContent = active ? '還原' : '放大';
  setTimeout(() => {
    const target = document.getElementById('klineChart');
    if(currentKlineChart && target) currentKlineChart.applyOptions({width:target.clientWidth, height:target.clientHeight});
    currentKlineChart?.timeScale().fitContent();
  }, 80);
}

async function renderKline(r){
  const key = `${r.stock_id}-${r.price_mode}`;
  currentKlineKey = key;
  currentKlineRow = r;
  const status = document.getElementById('klineStatus');
  const target = document.getElementById('klineChart');
  if(!status || !target) return;
  bindKlineToolbar();
  try{
    status.textContent = `${klineModeLabel(r.price_mode)}｜載入中…`;
    const res = await fetch(klineUrl(r));
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    if(currentKlineKey !== key) return;
    const rows = (payload.rows || []).filter(x => x.open && x.high && x.low && x.close);
    if(rows.length < 10) throw new Error('rows too few');
    currentKlinePayloadRows = rows;
    currentKlineSignalDate = r.date;
    const last = rows[rows.length - 1];
    status.textContent = `${klineModeLabel(r.price_mode)}｜${rows[0].date}～${last.date}｜收 ${fmtNum(last.close,2)}`;
    renderCurrentKlineFromState();
  }catch(err){
    if(currentKlineKey !== key) return;
    status.textContent = 'K 線資料讀取失敗';
    destroyKlineChart();
    target.innerHTML = '<div class="kline-empty">這檔暫時沒有可用 K 線資料。</div>';
    console.warn('kline failed', err);
  }
}
function destroyKlineChart(){
  if(currentKlineResizeObserver){ currentKlineResizeObserver.disconnect(); currentKlineResizeObserver = null; }
  const tooltip = document.getElementById('klineTooltip');
  const priceLabel = document.getElementById('klinePriceLabel');
  const timeLabel = document.getElementById('klineTimeLabel');
  const cursorInfo = document.getElementById('klineCursorInfo');
  const measureInfo = document.getElementById('klineMeasureInfo');
  if(tooltip){ tooltip.hidden = true; tooltip.innerHTML = ''; }
  if(priceLabel){ priceLabel.hidden = true; priceLabel.textContent = ''; }
  if(timeLabel){ timeLabel.hidden = true; timeLabel.textContent = ''; }
  if(cursorInfo){ cursorInfo.textContent = '移到圖上看 O / H / L / C / 漲跌幅 / 成交量'; cursorInfo.dataset.date = ''; }
  if(measureInfo){ measureInfo.textContent = currentKlineOptions.measure ? '測量：點第一根作為起點，再點第二根作為終點' : '測量：關閉'; measureInfo.dataset.active = String(currentKlineOptions.measure); }
  if(currentKlineChart){ currentKlineChart.remove(); currentKlineChart = null; }
}
function rowsForRange(rows, range){
  const n = { '1Y':260 }[range];
  return n ? rows.slice(-n) : rows;
}
function renderCurrentKlineFromState(){
  const target = document.getElementById('klineChart');
  if(!target || !currentKlinePayloadRows.length) return;
  const rows = rowsForRange(currentKlinePayloadRows, currentKlineOptions.range);
  if(window.LightweightCharts){
    renderInteractiveKline(target, rows, currentKlineSignalDate, currentKlineOptions);
  }else{
    target.innerHTML = klineSvg(rows, currentKlineSignalDate);
  }
}
function maSeries(rows, period){
  const out = [];
  let sum = 0;
  rows.forEach((r, i) => {
    sum += Number(r.close);
    if(i >= period) sum -= Number(rows[i-period].close);
    if(i >= period - 1) out.push({time:r.date, value:sum / period});
  });
  return out;
}
function renderInteractiveKline(target, rows, signalDate, opts={}){
  destroyKlineChart();
  target.innerHTML = '';
  const legend = document.getElementById('klineLegend');
  const chart = LightweightCharts.createChart(target, {
    width: target.clientWidth || 860,
    height: target.clientHeight || 380,
    layout: { background: { color: 'transparent' }, textColor: '#8fb0c8' },
    grid: { vertLines: { color: 'rgba(143,176,200,.12)' }, horzLines: { color: 'rgba(143,176,200,.14)' } },
    rightPriceScale: { borderColor: 'rgba(143,176,200,.22)', scaleMargins: { top: .08, bottom: opts.volume ? .28 : .08 }, mode:klineScaleMode() },
    timeScale: { borderColor: 'rgba(143,176,200,.22)', timeVisible: false },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { color:'rgba(32,224,255,.55)', width:1, style: LightweightCharts.LineStyle.Dashed, labelVisible:false },
      horzLine: { color:'rgba(32,224,255,.55)', width:1, style: LightweightCharts.LineStyle.Dashed, labelVisible:false },
    },
    handleScroll: { mouseWheel:true, pressedMouseMove:true, horzTouchDrag:true, vertTouchDrag:false },
    handleScale: { axisPressedMouseMove:true, mouseWheel:true, pinch:true },
    localization: { locale: 'zh-TW' },
  });
  currentKlineChart = chart;
  target.dataset.scaleMode = currentKlineOptions.scale;
  const ohlcData = rows.map(r => ({time:r.date, open:Number(r.open), high:Number(r.high), low:Number(r.low), close:Number(r.close)}));
  const lineData = rows.map(r => ({time:r.date, value:Number(r.close)}));
  let mainSeries;
  if(currentKlineOptions.type === 'bars'){
    mainSeries = chart.addBarSeries({upColor:'#ff6b6b', downColor:'#6dff9f'});
    mainSeries.setData(ohlcData);
  }else if(currentKlineOptions.type === 'line'){
    mainSeries = chart.addLineSeries({color:'#20e0ff', lineWidth:2});
    mainSeries.setData(lineData);
  }else if(currentKlineOptions.type === 'area'){
    mainSeries = chart.addAreaSeries({lineColor:'#20e0ff', topColor:'rgba(32,224,255,.28)', bottomColor:'rgba(32,224,255,.02)', lineWidth:2});
    mainSeries.setData(lineData);
  }else{
    mainSeries = chart.addCandlestickSeries({
      upColor:'#ff6b6b', downColor:'#6dff9f', borderUpColor:'#ff6b6b', borderDownColor:'#6dff9f', wickUpColor:'#ff9b9b', wickDownColor:'#9affbc'
    });
    mainSeries.setData(ohlcData);
  }
  if(opts.volume){
    const volume = chart.addHistogramSeries({ priceFormat:{type:'volume'}, priceScaleId:'', color:'rgba(143,176,200,.35)' });
    volume.priceScale().applyOptions({ scaleMargins:{ top:.78, bottom:0 } });
    volume.setData(rows.map(r => ({time:r.date, value:Number(r.volume || 0), color:Number(r.close) >= Number(r.open) ? 'rgba(255,107,107,.32)' : 'rgba(109,255,159,.28)'})));
  }
  const ma5Data = maSeries(rows,5), ma20Data = maSeries(rows,20), ma60Data = maSeries(rows,60);
  if(opts.ma){
    const ma5 = chart.addLineSeries({color:'#ffd166', lineWidth:1, priceLineVisible:false, lastValueVisible:false});
    const ma20 = chart.addLineSeries({color:'#20e0ff', lineWidth:1, priceLineVisible:false, lastValueVisible:false});
    const ma60 = chart.addLineSeries({color:'#d9b8ff', lineWidth:1, priceLineVisible:false, lastValueVisible:false});
    ma5.setData(ma5Data); ma20.setData(ma20Data); ma60.setData(ma60Data);
  }
  if(opts.signal && rows.some(r => r.date === signalDate)) mainSeries.setMarkers([{time:signalDate, position:'aboveBar', color:'#20e0ff', shape:'arrowDown', text:'候選'}]);
  const byDate = new Map(rows.map(r => [r.date, r]));
  const tooltip = document.getElementById('klineTooltip');
  const priceLabel = document.getElementById('klinePriceLabel');
  const timeLabel = document.getElementById('klineTimeLabel');
  const cursorInfo = document.getElementById('klineCursorInfo');
  const measureInfo = document.getElementById('klineMeasureInfo');
  const maMap = new Map();
  for(const item of ma5Data) maMap.set(item.time, {...(maMap.get(item.time)||{}), ma5:item.value});
  for(const item of ma20Data) maMap.set(item.time, {...(maMap.get(item.time)||{}), ma20:item.value});
  for(const item of ma60Data) maMap.set(item.time, {...(maMap.get(item.time)||{}), ma60:item.value});

  function cursorInfoText(bar){
    const idx = rows.findIndex(r => r.date === bar.date);
    const prevClose = idx > 0 ? Number(rows[idx-1].close) : Number(bar.open);
    const close = Number(bar.close);
    const change = close - prevClose;
    const pct = prevClose ? change / prevClose : 0;
    const up = change >= 0;
    const volumeText = `${(Number(bar.volume||0)/1000).toFixed(0)}張`;
    return {
      text:`${bar.date}｜O ${fmtNum(bar.open,2)}｜H ${fmtNum(bar.high,2)}｜L ${fmtNum(bar.low,2)}｜C ${fmtNum(bar.close,2)}｜漲跌 ${up ? '+' : ''}${fmtNum(change,2)} / ${up ? '+' : ''}${fmtPct(pct)}｜量 ${volumeText}`,
      change, pct
    };
  }
  function updateCursorInfo(bar){
    if(!cursorInfo || !bar) return;
    const info = cursorInfoText(bar);
    cursorInfo.textContent = info.text;
    cursorInfo.dataset.date = bar.date;
    cursorInfo.dataset.close = String(bar.close);
    cursorInfo.dataset.change = String(info.change);
    cursorInfo.dataset.pct = String(info.pct);
    cursorInfo.classList.toggle('up', info.change >= 0);
    cursorInfo.classList.toggle('down', info.change < 0);
  }

  function measureText(start, end){
    const si = rows.findIndex(r => r.date === start.date);
    const ei = rows.findIndex(r => r.date === end.date);
    const lo = Math.min(si, ei), hi = Math.max(si, ei);
    const slice = rows.slice(lo, hi + 1);
    const startClose = Number(start.close);
    const endClose = Number(end.close);
    const diff = endClose - startClose;
    const pct = startClose ? diff / startClose : 0;
    const high = Math.max(...slice.map(r => Number(r.high)));
    const low = Math.min(...slice.map(r => Number(r.low)));
    const bars = Math.abs(ei - si) + 1;
    return {text:`測量：${start.date} → ${end.date}｜${bars}根｜漲跌 ${diff >= 0 ? '+' : ''}${fmtNum(diff,2)} / ${diff >= 0 ? '+' : ''}${fmtPct(pct)}｜區間高 ${fmtNum(high,2)}｜區間低 ${fmtNum(low,2)}`, bars, diff, pct, high, low};
  }
  function updateMeasure(bar){
    if(!currentKlineOptions.measure || !measureInfo || !bar) return;
    if(!window.__magic26KlineMeasureStart || window.__magic26KlineMeasureEnd){
      window.__magic26KlineMeasureStart = bar;
      window.__magic26KlineMeasureEnd = null;
      measureInfo.textContent = `測量起點：${bar.date}｜收 ${fmtNum(bar.close,2)}｜再點第二根`;
      measureInfo.dataset.start = bar.date; measureInfo.dataset.end = ''; measureInfo.dataset.days = ''; measureInfo.dataset.pct = '';
      measureInfo.classList.remove('up','down');
      return;
    }
    window.__magic26KlineMeasureEnd = bar;
    const m = measureText(window.__magic26KlineMeasureStart, bar);
    measureInfo.textContent = m.text;
    measureInfo.dataset.start = window.__magic26KlineMeasureStart.date;
    measureInfo.dataset.end = bar.date;
    measureInfo.dataset.days = String(m.bars);
    measureInfo.dataset.pct = String(m.pct);
    measureInfo.classList.toggle('up', m.diff >= 0);
    measureInfo.classList.toggle('down', m.diff < 0);
  }
  function legendText(bar){
    const m = maMap.get(bar.date) || {};
    const maText = opts.ma ? `｜MA5 ${fmtNum(m.ma5,2)}｜MA20 ${fmtNum(m.ma20,2)}｜MA60 ${fmtNum(m.ma60,2)}` : '';
    const volumeText = opts.volume ? `｜量 ${(Number(bar.volume||0)/1000).toFixed(0)}張` : '';
    return `${bar.date}｜開 ${fmtNum(bar.open,2)} 高 ${fmtNum(bar.high,2)} 低 ${fmtNum(bar.low,2)} 收 ${fmtNum(bar.close,2)}${volumeText}${maText}`;
  }
  function tooltipHtml(bar){
    const m = maMap.get(bar.date) || {};
    const change = Number(bar.close) - Number(bar.open);
    const changeCls = change >= 0 ? 'up' : 'down';
    const maHtml = opts.ma ? `<div><span>MA5</span><b>${fmtNum(m.ma5,2)}</b></div><div><span>MA20</span><b>${fmtNum(m.ma20,2)}</b></div><div><span>MA60</span><b>${fmtNum(m.ma60,2)}</b></div>` : '';
    const volHtml = opts.volume ? `<div><span>量</span><b>${(Number(bar.volume||0)/1000).toFixed(0)} 張</b></div>` : '';
    return `<strong>${bar.date}</strong><div><span>開</span><b>${fmtNum(bar.open,2)}</b></div><div><span>高</span><b>${fmtNum(bar.high,2)}</b></div><div><span>低</span><b>${fmtNum(bar.low,2)}</b></div><div><span>收</span><b>${fmtNum(bar.close,2)}</b></div><div><span>漲跌</span><b class="${changeCls}">${change >= 0 ? '+' : ''}${fmtNum(change,2)}</b></div>${volHtml}${maHtml}`;
  }
  function hideTooltip(){
    if(tooltip) tooltip.hidden = true;
    if(priceLabel) priceLabel.hidden = true;
    if(timeLabel) timeLabel.hidden = true;
  }
  function showAxisLabels(bar, point, price){
    if(priceLabel && point){
      priceLabel.textContent = fmtNum(price ?? bar.close, 2);
      priceLabel.hidden = false;
      priceLabel.style.top = `${Math.max(0, Math.min(target.clientHeight - priceLabel.offsetHeight, point.y - priceLabel.offsetHeight/2))}px`;
      priceLabel.dataset.price = String(price ?? bar.close);
    }
    if(timeLabel && point){
      timeLabel.textContent = bar.date;
      timeLabel.hidden = false;
      timeLabel.style.left = `${Math.max(6, Math.min(target.clientWidth - timeLabel.offsetWidth - 6, point.x - timeLabel.offsetWidth/2))}px`;
      timeLabel.dataset.date = bar.date;
    }
  }
  function showTooltipAt(bar, point, price){
    if(legend) legend.textContent = legendText(bar);
    updateCursorInfo(bar);
    showAxisLabels(bar, point, price);
    if(!tooltip || !point) return;
    tooltip.innerHTML = tooltipHtml(bar);
    tooltip.hidden = false;
    const leftSide = point.x > target.clientWidth - 230;
    tooltip.style.left = `${Math.max(8, leftSide ? point.x - 214 : point.x + 14)}px`;
    tooltip.style.top = `${Math.max(8, Math.min(target.clientHeight - tooltip.offsetHeight - 8, point.y + 12))}px`;
    tooltip.dataset.date = bar.date;
    tooltip.dataset.close = String(bar.close);
  }
  target.onclick = ev => {
    if(!currentKlineOptions.measure) return;
    const rect = target.getBoundingClientRect();
    const x = Math.max(0, Math.min(target.clientWidth - 1, ev.clientX - rect.left));
    const plotW = Math.max(1, target.clientWidth - 70);
    const idx = Math.max(0, Math.min(rows.length - 1, Math.round((x / plotW) * (rows.length - 1))));
    updateMeasure(rows[idx]);
  };
  target.onmousemove = ev => {
    const rect = target.getBoundingClientRect();
    const x = Math.max(0, Math.min(target.clientWidth - 1, ev.clientX - rect.left));
    const y = Math.max(0, Math.min(target.clientHeight - 1, ev.clientY - rect.top));
    const plotW = Math.max(1, target.clientWidth - 70);
    const idx = Math.max(0, Math.min(rows.length - 1, Math.round((x / plotW) * (rows.length - 1))));
    showTooltipAt(rows[idx], {x, y}, mainSeries.coordinateToPrice(y));
  };
  target.onmouseleave = hideTooltip;
  if(legend) legend.textContent = legendText(rows[rows.length-1]);
  updateCursorInfo(rows[rows.length-1]);
  setKlineMeasure(currentKlineOptions.measure);
  resetKlineMeasure();
  chart.subscribeCrosshairMove(param => {
    const time = typeof param.time === 'string' ? param.time : null;
    const bar = time ? byDate.get(time) : null;
    if(legend) legend.textContent = bar ? legendText(bar) : legendText(rows[rows.length-1]);
    updateCursorInfo(bar || rows[rows.length-1]);
    if(!bar || !param.point || param.point.x < 0 || param.point.y < 0 || param.point.x > target.clientWidth || param.point.y > target.clientHeight){
      hideTooltip();
      return;
    }
    showTooltipAt(bar, param.point, mainSeries.coordinateToPrice(param.point.y));
  });
  chart.timeScale().fitContent();
  const ro = new ResizeObserver(entries => {
    const width = Math.floor(entries[0].contentRect.width);
    if(width > 0) chart.applyOptions({width});
  });
  currentKlineResizeObserver = ro;
  ro.observe(target);
  target.ondblclick = () => resetCurrentKlineView();
  target.dataset.chartEngine = 'lightweight-charts';
  target.dataset.chartRange = currentKlineOptions.range;
  target.dataset.scaleMode = currentKlineOptions.scale;
  target.dataset.chartType = currentKlineOptions.type;
}
function klineSvg(rows, signalDate){
  const w = 860, h = 320, pad = {l:48,r:16,t:18,b:54};
  const chartH = 210, volTop = 244, volH = 48;
  const highs = rows.map(r=>Number(r.high)), lows = rows.map(r=>Number(r.low));
  const vols = rows.map(r=>Number(r.volume || 0));
  const hi = Math.max(...highs), lo = Math.min(...lows);
  const maxVol = Math.max(...vols, 1);
  const xStep = (w-pad.l-pad.r) / rows.length;
  const y = v => pad.t + (hi - v) / Math.max(hi - lo, 1e-9) * chartH;
  const vy = v => volTop + volH - (v / maxVol) * volH;
  const ticks = [lo, (lo+hi)/2, hi];
  const grid = ticks.map(t => `<line x1="${pad.l}" x2="${w-pad.r}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" class="k-grid"/><text x="8" y="${(y(t)+4).toFixed(1)}" class="k-axis">${fmtNum(t,1)}</text>`).join('');
  const bars = rows.map((r,i)=>{
    const x = pad.l + i*xStep + xStep/2;
    const up = Number(r.close) >= Number(r.open);
    const cls = up ? 'up' : 'down';
    const top = y(Math.max(Number(r.open), Number(r.close)));
    const bot = y(Math.min(Number(r.open), Number(r.close)));
    const bodyH = Math.max(2, bot-top);
    const bw = Math.max(3, Math.min(8, xStep*.62));
    const volY = vy(Number(r.volume || 0));
    const sig = r.date === signalDate ? `<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${pad.t}" y2="${volTop+volH}" class="k-signal"/><text x="${Math.min(w-70, x+5).toFixed(1)}" y="14" class="k-signal-text">候選日</text>` : '';
    return `${sig}<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${y(Number(r.high)).toFixed(1)}" y2="${y(Number(r.low)).toFixed(1)}" class="wick ${cls}"/><rect x="${(x-bw/2).toFixed(1)}" y="${top.toFixed(1)}" width="${bw.toFixed(1)}" height="${bodyH.toFixed(1)}" class="candle ${cls}"/><rect x="${(x-bw/2).toFixed(1)}" y="${volY.toFixed(1)}" width="${bw.toFixed(1)}" height="${(volTop+volH-volY).toFixed(1)}" class="volume ${cls}"/>`;
  }).join('');
  const first = rows[0], last = rows[rows.length-1];
  return `<svg viewBox="0 0 ${w} ${h}" class="kline-svg" preserveAspectRatio="none">${grid}<line x1="${pad.l}" x2="${w-pad.r}" y1="${volTop}" y2="${volTop}" class="k-grid"/>${bars}<text x="${pad.l}" y="${h-18}" class="k-axis">${first.date}</text><text x="${w-pad.r-84}" y="${h-18}" class="k-axis">${last.date}</text><text x="${pad.l}" y="${h-36}" class="k-legend">紅漲｜綠跌｜直線＝候選日</text></svg>`;
}

function detailSectionHtml(title, items){
  return `<section class="detail-section"><h3>${title}</h3><div class="detail-grid">${items.map(([k,v,hint]) => `<div${hint ? ` title="${hint}"` : ''}><label>${k}</label><strong>${v ?? '—'}</strong></div>`).join('')}</div></section>`;
}
function showDetail(r){
  if(!r) return;
  selectedDetailKey = groupKey(r);
  document.getElementById('detailTitle').textContent = `${r.stock_id} ${r.stock_name || ''}`;
  document.getElementById('detailSubtitle').textContent = `出訊號 ${r.signal_date || r.date}｜${groupHitText(r)}｜${r.priority_reason || displayPriorityLabel(r)} ${priorityScore(r)}`;
  const aliasRows = r.alias_rows || [r];
  const sections = [
    ['訊號摘要', [
      ['出訊號日期', r.signal_date || r.date], ['資料算到', r.data_through || summaryData?.data_through || '—'], ['產生時間', r.generated_at || summaryData?.generated_at || '—'], ['合併版本', `${r.alias_count || aliasRows.length} 筆`],
      ['命中分組', groupHitText(r)], ['價格版本', groupModeText(r)], ['為什麼出現', cardWhyText(r)], ['要小心', cardCautionText(r)]
    ]],
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
      ['追高分級', r.risk_v2_label_zh || '—'], ['主提醒', r.risk_v2_primary_badge_zh || '—'], ['操作提示', r.risk_v2_action_hint_zh || '—'],
      ['觸發原因', riskV2ListText(r.risk_v2_reasons_zh) || '—'], ['規則版本', r.risk_v2_rule_version || '—'], ['用途', riskV2DisplayOnlyText(r)],
      ['後來60天漲幅', fmtPct(r.ret_60d_signal)], ['是否已漲太多', isRet60Hot(r) ? '超過150%' : (r.ret_60d_signal == null ? '待補' : '未超過')], ['其他提醒', round19TagsText(r) || '—', '原欄位：Round19標籤'],
      ['日線長均偏空', isTrue(r.risk_daily_long_ma_bear) ? '是' : '否'], ['週線長均偏空', isTrue(r.risk_weekly_long_ma_bear) ? '是' : '否'], ['長均分數', r.risk_long_ma_score ?? '—']
    ]],
    ['研究狀態', [
      ['查看分數', priorityScore(r)], ['目前判斷', classify(r)], ['漲幅區間', r.momentum_bucket_zh], ['原始分組', r.strategy_role_zh], ['查看順序', displayPriorityLabel(r)], ['原始標籤', r.research_tags]
    ]]
  ];
  const aliasHtml = `<section class="detail-section"><h3>合併來源</h3><div class="alias-list">${aliasRows.map(a=>`<span>${shortCandidateLabel(a.candidate)}｜${priceModeLabel(a.price_mode)}｜${a.date}</span>`).join('')}</div></section>`;
  document.getElementById('detailBody').innerHTML = `${klinePanelHtml(r)}<div class="detail-sections">${sections.map(([title, items]) => detailSectionHtml(title, items)).join('')}${aliasHtml}</div><div class="detail-tags">${riskTags(r)}</div>${externalLinksHtml(r)}`;
  renderKline(r);
  renderStockCards();
  renderMainAList();
  document.getElementById('detailPanel').scrollIntoView({behavior:'smooth', block:'nearest'});
}
function clearDetail(){
  selectedDetailKey = null;
  document.getElementById('detailTitle').textContent = '股票細節';
  document.getElementById('detailSubtitle').textContent = '點選今日主清單卡片後顯示完整欄位。';
  document.getElementById('detailBody').innerHTML = '<div class="detail-empty">尚未選取候選。</div>';
  renderStockCards();
  renderMainAList();
}
load().catch(err=>{document.getElementById('status').textContent='載入失敗'; console.error(err);});
