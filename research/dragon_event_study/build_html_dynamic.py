# -*- coding: utf-8 -*-
"""6.5年动态回看表:薄壳 HTML + 按版本 <script src> 动态加载 viewer/data/pool_vX.js。
双击 viewer/ 下的 html 直开(file:// 下 <script src> 可用,免起服务)。数据更新只需重跑 build_dynamic.py。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(HERE, "viewer")

HTML = r"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>龙头候选池 2020–2026 (6.5年) forward 回看表 · 动态</title>
<script src="data/meta.js"></script>
<style>
:root{--navy:#1a1a2e;--slate:#2c3e50;--slate2:#34495e;--green:#228B22;--red:#CC0000;
--orange:#FF8C00;--blue:#2196F3;--page:#f5f5f5;--grp:#3b5168;--purple:#7b1fa2;}
*{box-sizing:border-box}
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",Arial,sans-serif;margin:0;
background:var(--page);color:#222;font-size:13px}
.wrap{padding:14px 18px 60px}
.hdr{background:var(--navy);color:#fff;padding:14px 20px;border-radius:8px;margin-bottom:12px}
.hdr h1{margin:0 0 6px;font-size:18px}
.hdr .m{font-size:12px;color:#bbb;line-height:1.6}
.hdr .note{font-size:11px;color:#ffd27f;margin-top:6px}
.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;background:#fff;border-radius:8px;
padding:10px 14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.grp{display:flex;align-items:center;gap:6px}
.grp>span.lbl{font-size:11px;color:#888;margin-right:2px}
.seg{display:inline-flex;border:1px solid #ccc;border-radius:6px;overflow:hidden;flex-wrap:wrap}
.seg button{border:0;background:#fff;padding:5px 11px;cursor:pointer;font-size:12px;color:#444}
.seg button.on{background:var(--slate);color:#fff;font-weight:bold}
.chk{font-size:12px;color:#444;cursor:pointer;user-select:none;padding:3px 8px;border:1px solid #ddd;
border-radius:5px;background:#fff}
.chk.on{background:#eef3f8;border-color:var(--blue);color:var(--slate)}
select{font-size:12px;padding:4px 6px;border:1px solid #ccc;border-radius:5px;background:#fff}
.mini{display:flex;flex-wrap:wrap;gap:18px;align-items:center;background:#fff;border-radius:8px;
padding:8px 14px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);font-size:12px}
.mini b{font-size:14px}
.cmp{display:flex;gap:10px;flex-wrap:wrap}
.cmpcard{border:1px solid #eee;border-radius:6px;padding:6px 10px;font-size:11px;min-width:150px}
.cmpcard .t{font-weight:bold;margin-bottom:3px}
.dw{color:var(--green)} .tc{color:var(--orange)}
.legend{display:flex;flex-wrap:wrap;gap:16px;align-items:center;background:#fff;border-radius:8px;
padding:7px 14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);font-size:11px;color:#555}
.legend .item{display:flex;align-items:center;gap:5px}
.scaleimg{display:inline-block;height:14px;width:200px;border:1px solid #ccc;border-radius:2px;
background:linear-gradient(to right,#16602f,#7fc49b,#ffffff,#e69a90,#b01c1c)}
.swatch{display:inline-block;width:16px;height:14px;border-radius:2px;vertical-align:middle}
.sw-miss{background:repeating-linear-gradient(45deg,#e6e6e6,#e6e6e6 3px,#f4f4f4 3px,#f4f4f4 6px);
border:1px solid #ddd;color:#aaa;text-align:center;line-height:14px;font-size:10px}
.sw-ent{width:5px;background:var(--blue)}
.sw-sl{border:0;border-bottom:3px solid var(--purple);height:12px}
.tbox{overflow:auto;max-height:72vh;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.12);position:relative}
table{border-collapse:separate;border-spacing:0;width:max-content;min-width:100%}
th,td{padding:5px 7px;font-size:12px;white-space:nowrap;border-bottom:1px solid #f0f0f0}
thead th{position:sticky;top:0;z-index:5;background:var(--slate);color:#fff;text-align:center;font-weight:600}
td.num,th.num{font-family:"SF Mono","Consolas","Roboto Mono",monospace;text-align:right}
.frz{position:sticky;background:#fff;z-index:3}
thead .frz{z-index:6;background:var(--slate)}
tbody tr:nth-child(even) .frz{background:#fbfbfd}
tbody tr.gstart td{border-top:2px solid var(--grp)}
tbody tr:hover td{box-shadow:inset 0 2px 0 -1px var(--navy),inset 0 -2px 0 -1px var(--navy)}
tbody tr.gstart:hover td{box-shadow:inset 0 2px 0 0 var(--grp),inset 0 -2px 0 -1px var(--navy)}
.badge{display:inline-block;padding:1px 7px;border-radius:3px;color:#fff;font-size:11px}
.b-dw{background:var(--green)} .b-tc{background:var(--orange)}
tr.ent .frz{background:#eaf4fd!important}
tr.ent td.lead{box-shadow:inset 4px 0 0 0 var(--blue)}
.entbadge{background:var(--blue);color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold}
td.miss{background:repeating-linear-gradient(45deg,#e8e8e8,#e8e8e8 3px,#f5f5f5 3px,#f5f5f5 6px);
color:#999;text-align:center}
td.sl{border-bottom:3px solid var(--purple)}
.rowx{cursor:pointer}
.cap{padding:8px 14px;background:#fff8e1;color:#9a6a00;font-size:12px;border-top:1px solid #f0e0b0}
.spin{position:absolute;inset:0;background:rgba(255,255,255,.85);display:flex;align-items:center;
justify-content:center;font-size:14px;color:var(--slate);z-index:20}
.drawer{position:fixed;top:0;right:0;width:430px;max-width:92vw;height:100%;background:#fff;
box-shadow:-3px 0 16px rgba(0,0,0,.2);transform:translateX(100%);transition:.2s;z-index:50;overflow:auto;padding:18px}
.drawer.open{transform:translateX(0)}
.drawer h3{margin:0 0 4px;font-size:15px}.drawer .close{position:absolute;top:12px;right:16px;cursor:pointer;font-size:20px;color:#888}
.drawer table{width:100%;border-spacing:0}.drawer td{border-bottom:1px solid #f0f0f0;font-size:12px}.drawer td:first-child{color:#888;width:46%}
.ft{margin-top:14px;font-size:11px;color:#999;text-align:center}
th.s{cursor:pointer} th.s:hover{background:var(--slate2)}
</style></head><body><div class="wrap">
<div class="hdr"><h1>龙头候选池 · 2020–2026 (6.5年) · day1–20 forward 回看表 <span style="font-size:12px;color:#8fd">动态加载</span>
<a href="龙头候选池回看表_尾盘买入版.html" style="color:#ffb3f0;font-size:12px;text-decoration:none;border:1px solid #ffb3f0;border-radius:5px;padding:2px 10px;margin-left:10px">⇄ 切尾盘买入版</a></h1>
<div class="m">战车A龙头3 v1.4.0D_observer · 每日 top12 dragon · t=0 开盘买入裸持(day1=t=0收盘) · 全候选(含 trend_core 对照组) · 中台warehouse后端</div>
<div class="m" id="cutoff"></div>
<div class="note" id="note"></div></div>
<div class="bar">
<div class="grp"><span class="lbl">版本</span><div class="seg" id="vSeg"></div></div>
<div class="grp"><span class="lbl">年</span><div class="seg" id="ySeg"></div></div>
<div class="grp"><span class="lbl">月</span><div class="seg" id="mSeg"></div></div>
<div class="grp"><span class="lbl">tpl</span>
<span class="chk on" data-tpl="deep_water">deep_water</span>
<span class="chk on" data-tpl="trend_core">trend_core</span></div>
<div class="grp"><span class="lbl">入场</span>
<select id="entSel"><option value="all">全部</option><option value="1">仅 entered</option><option value="0">仅未入场</option></select></div>
<div class="grp"><span class="lbl">排序</span>
<select id="sortSel"><option value="entry_date">entry_date(按日分组)</option><option value="rank">rank</option>
<option value="dragon_score">dragon_score</option><option value="max_ret">max_ret</option><option value="final_ret">final_ret</option></select></div>
</div>
<div class="legend">
<span class="item"><b style="color:#555">色阶</b> 绿跌</span>
<span class="item"><span class="scaleimg"></span> 红涨</span>
<span class="item"><span class="swatch sw-miss">–</span> 未到期</span>
<span class="item"><span class="swatch sw-ent"></span> 已入场(2026-03~06才有)</span>
<span class="item"><span class="swatch sw-sl"></span> 首触7%追踪止损当日</span>
<span class="item" style="color:#888">只 D1–D20 染色;score/maxR/finR 素色</span>
</div>
<div class="mini" id="mini"></div>
<div class="tbox"><div class="spin" id="spin" style="display:none">加载数据中…</div>
<table><thead id="thead"></thead><tbody id="tbody"></tbody></table>
<div class="cap" id="cap" style="display:none"></div></div>
<div class="ft" id="ft"></div></div>
<div class="drawer" id="drawer"><span class="close" onclick="closeDrawer()">×</span><div id="dbody"></div></div>
<script>
const META=window.META; window.POOL=window.POOL||{};
const DAYS=Array.from({length:20},(_,i)=>'day'+(i+1));
const MAXRENDER=1500;
let state={ver:(META.versions.includes('v3')?'v3':META.versions[0]),
  year:META.years[META.years.length-1], month:'all',
  tpl:{deep_water:true,trend_core:true},ent:'all',sort:'entry_date',asc:true};

function cellColor(v){
  if(v==null||v===undefined||isNaN(v))return null;
  const cap=22;let t=Math.max(-1,Math.min(1,v/cap));const a=Math.abs(t);
  const w=[255,255,255];const tgt=t>=0?[176,28,28]:[22,96,52];
  const c=w.map((x,i)=>Math.round(x+(tgt[i]-x)*a));
  const lum=(0.2126*c[0]+0.7152*c[1]+0.0722*c[2]);
  return{bg:`rgb(${c[0]},${c[1]},${c[2]})`,fg:lum<150?'#fff':'#1a1a2e'};
}
function fmtPct(v){if(v==null||v===undefined||isNaN(v))return null;return(v>=0?'+':'')+v.toFixed(1)+'%';}
function plainRet(v){if(v==null||v===undefined||isNaN(v))return '<span style="color:#bbb">–</span>';
  const col=v>0?'#c0392b':v<0?'#1e8449':'#777';return `<span style="color:${col}">${fmtPct(v)}</span>`;}

function ensureVer(ver,cb){
  if(window.POOL[ver]){cb();return;}
  document.getElementById('spin').style.display='flex';
  const s=document.createElement('script');s.src='data/pool_'+ver+'.js';
  s.onload=()=>{document.getElementById('spin').style.display='none';cb();};
  s.onerror=()=>{document.getElementById('spin').textContent='加载 '+ver+' 数据失败(需与 data/ 同目录)';};
  document.head.appendChild(s);
}
function curRows(){
  const rows=window.POOL[state.ver]||[];
  return rows.filter(r=>{
    const y=r.entry_date.slice(0,4), mo=r.entry_date.slice(4,6);
    return (state.year==='all'||y===state.year)
      && (state.month==='all'||mo===state.month)
      && state.tpl[r.tpl]
      && (state.ent==='all'||String(r.entered||0)===state.ent);
  });
}
function sortRows(rs){
  const k=state.sort;const s=[...rs];
  s.sort((a,b)=>{let x=a[k],y=b[k];
    if(k==='entry_date'){x=a.entry_date+(''+a.rank).padStart(2,'0');y=b.entry_date+(''+b.rank).padStart(2,'0');}
    x=(x==null?-1e9:x);y=(y==null?-1e9:y);
    return state.asc?(x>y?1:x<y?-1:0):(x<y?1:x>y?-1:0);});
  return s;
}
const FRZ=[['rank','#',40],['code','代码',78],['name','名称',74],['entry_date','选股日',82],['tpl','tpl',86],['entered','入场',58]];
function buildHead(){
  let left=0;let h='<tr>';
  FRZ.forEach(c=>{h+=`<th class="frz s" style="left:${left}px" data-k="${c[0]}">${c[1]}</th>`;left+=c[2];});
  h+='<th class="s" data-k="dragon_score">score</th><th class="s" data-k="max_ret">maxR</th><th>peak</th><th class="s" data-k="final_ret">finR</th>';
  DAYS.forEach(d=>h+=`<th class="num">${d.replace('day','D')}</th>`);
  h+='</tr>';document.getElementById('thead').innerHTML=h;
  document.querySelectorAll('th.s').forEach(t=>t.onclick=()=>{const k=t.dataset.k;
    if(state.sort===k)state.asc=!state.asc;else{state.sort=k;state.asc=(k==='entry_date'||k==='rank');}
    document.getElementById('sortSel').value=(['entry_date','rank','dragon_score','max_ret','final_ret'].includes(k)?k:document.getElementById('sortSel').value);render();});
}
function tplBadge(t){return `<span class="badge ${t==='deep_water'?'b-dw':'b-tc'}">${t}</span>`;}
function render(){
  const all=sortRows(curRows());
  const rs=all.slice(0,MAXRENDER);
  const grouped=(state.sort==='entry_date');
  let left,html='',prevDate=null;
  for(const r of rs){
    left=0;const ec=r.entered?'ent':'';
    const gstart=grouped&&(r.entry_date!==prevDate);
    html+=`<tr class="rowx ${ec} ${gstart?'gstart':''}" data-id="${r.entry_date}|${r.code}">`;
    const fz=(w,inner,extra='')=>{const s=`<td class="frz ${extra}" style="left:${left}px">${inner}</td>`;left+=w;return s;};
    html+=fz(40,r.rank,'num lead');
    html+=fz(78,r.code);
    html+=fz(74,r.name||'');
    html+=fz(82,(grouped&&!gstart)?'<span style="color:#ccc">〃</span>':(r.entry_date.slice(0,4)+'-'+r.entry_date.slice(4,6)+'-'+r.entry_date.slice(6,8)));
    html+=fz(86,tplBadge(r.tpl));
    html+=fz(58,r.entered?'<span class="entbadge">✓买</span>':'');
    html+=`<td class="num">${r.dragon_score==null?'':(+r.dragon_score).toFixed(3)}</td>`;
    html+=`<td class="num">${plainRet(r.max_ret)}</td>`;
    html+=`<td class="num" style="color:#888">${r.day_to_peak||''}</td>`;
    html+=`<td class="num">${plainRet(r.final_ret)}</td>`;
    for(let i=1;i<=20;i++){const v=r['day'+i];const sl=(r.sl_7pct_hit_day===i)?'sl':'';
      if(v==null||v===undefined||isNaN(v))html+=`<td class="num miss ${sl}">–</td>`;
      else{const c=cellColor(v);html+=`<td class="num ${sl}" style="background:${c.bg};color:${c.fg}">${fmtPct(v)}</td>`;}}
    html+='</tr>';prevDate=r.entry_date;
  }
  document.getElementById('tbody').innerHTML=html||'<tr><td style="padding:20px">无数据(换筛选)</td></tr>';
  document.querySelectorAll('tr.rowx').forEach(tr=>tr.onclick=()=>openDrawer(tr.dataset.id));
  const cap=document.getElementById('cap');
  if(all.length>MAXRENDER){cap.style.display='block';cap.textContent=`筛选命中 ${all.length} 行,为流畅只渲染前 ${MAXRENDER} 行。请收窄 年/月/tpl 看全部。`;}
  else cap.style.display='none';
  renderMini(all);
  document.getElementById('ft').textContent=`${META.generated_for} · 当前版本 ${state.ver}(${(window.POOL[state.ver]||[]).length}行) · 视图命中 ${all.length} 行`;
}
function med(a){if(!a.length)return null;const s=[...a].sort((x,y)=>x-y);const m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;}
function statOf(rs,tpl,col){const a=rs.filter(r=>r.tpl===tpl).map(r=>r[col]).filter(v=>v!=null&&!isNaN(v));
  if(!a.length)return null;return{n:a.length,md:med(a),win:a.filter(v=>v>0).length/a.length*100};}
function renderMini(rs){
  let cmp='';
  [['day5','D5'],['day10','D10'],['day20','D20']].forEach(([c,lab])=>{
    const d=statOf(rs,'deep_water',c),t=statOf(rs,'trend_core',c);
    cmp+=`<div class="cmpcard"><div class="t">${lab} 中位 / 胜率</div>
    <div class="dw">deep_water: ${d?d.md.toFixed(1)+'% / '+d.win.toFixed(0)+'%':'—'}</div>
    <div class="tc">trend_core: ${t?t.md.toFixed(1)+'% / '+t.win.toFixed(0)+'%':'—'}</div></div>`;});
  document.getElementById('mini').innerHTML=
    `<div>命中 <b>${rs.length}</b> · deep_water ${rs.filter(r=>r.tpl==='deep_water').length} · trend_core ${rs.filter(r=>r.tpl==='trend_core').length} · 已入场 ${rs.filter(r=>r.entered).length}</div><div class="cmp">${cmp}</div>`;
}
const FIELDS=[['dragon_score','龙头评分'],['rank','排名'],['open_ratio','竞价涨幅'],['close_to_high','收高比'],
['auc_ratio','竞价量比'],['auc_amount','竞价额'],['ret3','3日涨幅'],['buy_price','t0开盘价'],
['max_ret','区间最大涨幅%'],['day_to_peak','到顶第几日'],['final_ret','末日收益%'],['days_available','有效天数'],
['window_incomplete','右侧截断'],['tp1_hit_day','+9%首达日'],['tp2_hit_day','+15%首达日'],['sl_7pct_hit_day','7%止损触发日'],
['is_big_meat_10','≥10%'],['is_super_meat_20','≥20%'],['entered','实际入场'],['entry_type','入场类型'],
['entry_score','入场评分'],['exit_date','实际出场日'],['exit_reason','出场原因'],['actual_pnl_pct','实际收益%'],['hold_days','持有天']];
function openDrawer(id){
  const r=(window.POOL[state.ver]||[]).find(x=>x.entry_date+'|'+x.code===id);if(!r)return;
  let h=`<h3>${r.code} ${r.name||''} <span class="badge ${r.tpl==='deep_water'?'b-dw':'b-tc'}">${r.tpl}</span></h3>
  <div style="color:#888;font-size:12px;margin-bottom:8px">${state.ver} · 选股日 ${r.entry_date} · rank ${r.rank} ${r.entered?'· <span class="entbadge">✓ 已入场</span>':''}</div><table>`;
  FIELDS.forEach(([k,lab])=>{let v=r[k];if(v==null||v===undefined)v='—';else if(typeof v==='number')v=Number.isInteger(v)?v:v.toFixed(4);
    h+=`<tr><td>${lab}</td><td>${v}</td></tr>`;});
  h+='</table><div style="margin-top:10px;font-size:12px;color:#666">day1–20 forward(day1=t0收盘):</div><table>';
  for(let i=1;i<=20;i++){const v=r['day'+i];h+=`<tr><td>day${i}</td><td>${v==null?'<span style="color:#bbb">未到期</span>':((v>=0?'+':'')+v.toFixed(2)+'%')}</td></tr>`;}
  h+='</table>';document.getElementById('dbody').innerHTML=h;document.getElementById('drawer').classList.add('open');
}
function closeDrawer(){document.getElementById('drawer').classList.remove('open');}
function buildSeg(id,vals,key,onpick){
  const el=document.getElementById(id);
  el.innerHTML=vals.map(v=>`<button data-v="${v[0]}" class="${String(state[key])===String(v[0])?'on':''}">${v[1]}</button>`).join('');
  el.querySelectorAll('button').forEach(b=>b.onclick=()=>{state[key]=b.dataset.v;
    el.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));(onpick||render)();});
}
function switchVer(){ensureVer(state.ver,render);}
function applyUrlParams(){
  try{const q=new URLSearchParams(location.search);
    if(q.get('ver')&&META.versions.includes(q.get('ver')))state.ver=q.get('ver');
    if(q.get('year'))state.year=q.get('year');
    if(q.get('month'))state.month=q.get('month');
    if(q.get('ent'))state.ent=q.get('ent');
    if(q.get('sort'))state.sort=q.get('sort');
    if(q.get('asc'))state.asc=(q.get('asc')==='1');
    const tp=q.get('tpl');
    if(tp==='deep_water')state.tpl={deep_water:true,trend_core:false};
    else if(tp==='trend_core')state.tpl={deep_water:false,trend_core:true};
  }catch(e){}
}
function init(){
  applyUrlParams();
  const es=document.getElementById('entSel');if(es)es.value=state.ent;
  const ss=document.getElementById('sortSel');if(ss)ss.value=state.sort;
  document.querySelectorAll('.chk[data-tpl]').forEach(ch=>ch.classList.toggle('on',state.tpl[ch.dataset.tpl]));
  const c=META.cutoffs||{};
  document.getElementById('cutoff').innerHTML=`数据截止 — 选股竞价: <b>${c.selection||'?'}</b> · forward日线: <b>${c.forward||'?'}</b>`+(c.today_settled==='True'?' (今日已定盘)':'')+` · 各版 ${ (META.counts&&META.counts[state.ver])||'?'} 行`;
  document.getElementById('note').textContent=META.note+' · entered 窗口:'+(META.entered_window||'');
  buildSeg('vSeg',META.versions.map(v=>[v,v]),'ver',switchVer);
  buildSeg('ySeg',[['all','全部'],...META.years.map(y=>[y,y])],'year');
  buildSeg('mSeg',[['all','全部'],...Array.from({length:12},(_,i)=>{const mm=String(i+1).padStart(2,'0');return [mm,mm];})],'month');
  document.querySelectorAll('.chk[data-tpl]').forEach(ch=>ch.onclick=()=>{state.tpl[ch.dataset.tpl]=!state.tpl[ch.dataset.tpl];ch.classList.toggle('on');render();});
  document.getElementById('entSel').onchange=e=>{state.ent=e.target.value;render();};
  document.getElementById('sortSel').onchange=e=>{state.sort=e.target.value;state.asc=(e.target.value==='entry_date'||e.target.value==='rank');render();};
  buildHead();ensureVer(state.ver,render);
}
init();
</script></body></html>"""


def main():
    os.makedirs(VIEWER, exist_ok=True)
    out = os.path.join(VIEWER, "龙头候选池forward回看表_6.5年.html")
    io.open(out, 'w', encoding='utf-8').write(HTML)
    print("HTML:", out)


if __name__ == '__main__':
    main()
