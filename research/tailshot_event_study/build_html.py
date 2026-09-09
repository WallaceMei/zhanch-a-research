# -*- coding: utf-8 -*-
"""尾盘选股 forward 回看表 — 薄壳 HTML(data/meta.js + data/pool.js 动态加载)。双击直开。"""
import io, os
HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(HERE, 'viewer')

HTML = r"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>尾盘选股 V2 · 长样本 forward 回看表</title>
<script src="data/meta.js"></script>
<style>
:root{--navy:#14233b;--slate:#2c3e50;--slate2:#34495e;--green:#1e8449;--red:#c0392b;--blue:#2196F3;--page:#f5f6f8;--grp:#3b5168;}
*{box-sizing:border-box}
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",Arial,sans-serif;margin:0;background:var(--page);color:#222;font-size:13px}
.wrap{padding:14px 18px 60px}
.hdr{background:var(--navy);color:#fff;padding:14px 20px;border-radius:8px;margin-bottom:12px}
.hdr h1{margin:0 0 6px;font-size:18px}
.hdr .m{font-size:12px;color:#b8c4d6;line-height:1.6}
.hdr .note{font-size:11px;color:#ffd27f;margin-top:6px}
.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;background:#fff;border-radius:8px;padding:10px 14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.grp{display:flex;align-items:center;gap:6px}
.grp>span.lbl{font-size:11px;color:#888;margin-right:2px}
.seg{display:inline-flex;border:1px solid #ccc;border-radius:6px;overflow:hidden;flex-wrap:wrap}
.seg button{border:0;background:#fff;padding:5px 11px;cursor:pointer;font-size:12px;color:#444}
.seg button.on{background:var(--slate);color:#fff;font-weight:bold}
.chk{font-size:12px;color:#444;cursor:pointer;user-select:none;padding:3px 9px;border:1px solid #ddd;border-radius:5px;background:#fff}
.chk.on{background:#eef3f8;border-color:var(--blue);color:var(--slate);font-weight:bold}
select{font-size:12px;padding:4px 6px;border:1px solid #ccc;border-radius:5px;background:#fff}
.mini{display:flex;flex-wrap:wrap;gap:16px;align-items:stretch;background:#fff;border-radius:8px;padding:10px 14px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);font-size:12px}
.kpi{display:flex;flex-direction:column;gap:2px;padding-right:16px;border-right:1px solid #eee}
.kpi .v{font-size:20px;font-weight:bold;color:var(--navy)} .kpi .l{font-size:11px;color:#888}
.cmp{display:flex;gap:8px;flex-wrap:wrap}
.cmpcard{border:1px solid #eee;border-radius:6px;padding:5px 9px;font-size:11px;min-width:120px}
.cmpcard .t{font-weight:bold;margin-bottom:3px;color:#555}
.monthbar{display:flex;gap:3px;align-items:flex-end;height:60px;margin-top:2px}
.mb{width:26px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;font-size:9px;color:#888}
.mb i{width:18px;display:block;border-radius:2px 2px 0 0;font-style:normal}
.legend{display:flex;flex-wrap:wrap;gap:16px;align-items:center;background:#fff;border-radius:8px;padding:7px 14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.1);font-size:11px;color:#555}
.scaleimg{display:inline-block;height:14px;width:180px;border:1px solid #ccc;border-radius:2px;background:linear-gradient(to right,#16602f,#7fc49b,#ffffff,#e69a90,#b01c1c)}
.swatch{display:inline-block;width:16px;height:14px;border-radius:2px;vertical-align:middle}
.sw-miss{background:repeating-linear-gradient(45deg,#e6e6e6,#e6e6e6 3px,#f4f4f4 3px,#f4f4f4 6px);border:1px solid #ddd;color:#aaa;text-align:center;line-height:14px;font-size:10px}
.tbox{overflow:auto;max-height:70vh;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.12);position:relative}
table{border-collapse:separate;border-spacing:0;width:max-content;min-width:100%}
th,td{padding:5px 7px;font-size:12px;white-space:nowrap;border-bottom:1px solid #f0f0f0}
thead th{position:sticky;top:0;z-index:5;background:var(--slate);color:#fff;text-align:center;font-weight:600}
td.num,th.num{font-family:"SF Mono","Consolas","Roboto Mono",monospace;text-align:right}
.frz{position:sticky;background:#fff;z-index:3}
thead .frz{z-index:6;background:var(--slate)}
tbody tr:nth-child(even) .frz{background:#fbfbfd}
tbody tr.gstart td{border-top:2px solid var(--grp)}
tbody tr:hover td{box-shadow:inset 0 2px 0 -1px var(--navy),inset 0 -2px 0 -1px var(--navy)}
.b15{background:var(--red);color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold}
.b20{background:#7b1fa2;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold}
.bsl{background:#546e7a;color:#fff;padding:1px 5px;border-radius:3px;font-size:10px}
td.miss{background:repeating-linear-gradient(45deg,#e8e8e8,#e8e8e8 3px,#f5f5f5 3px,#f5f5f5 6px);color:#999;text-align:center}
.rowx{cursor:pointer}
.cap{padding:8px 14px;background:#fff8e1;color:#9a6a00;font-size:12px;border-top:1px solid #f0e0b0}
.spin{position:absolute;inset:0;background:rgba(255,255,255,.85);display:flex;align-items:center;justify-content:center;font-size:14px;color:var(--slate);z-index:20}
.drawer{position:fixed;top:0;right:0;width:420px;max-width:92vw;height:100%;background:#fff;box-shadow:-3px 0 16px rgba(0,0,0,.2);transform:translateX(100%);transition:.2s;z-index:50;overflow:auto;padding:18px}
.drawer.open{transform:translateX(0)}
.drawer h3{margin:0 0 4px;font-size:15px}.drawer .close{position:absolute;top:12px;right:16px;cursor:pointer;font-size:20px;color:#888}
.drawer table{width:100%;border-spacing:0}.drawer td{border-bottom:1px solid #f0f0f0;font-size:12px}.drawer td:first-child{color:#888;width:48%}
.ft{margin-top:14px;font-size:11px;color:#999;text-align:center}
th.s{cursor:pointer} th.s:hover{background:var(--slate2)}
</style></head><body><div class="wrap">
<div class="hdr"><h1>尾盘选股 V2 · 长样本 forward 回看表 <span style="font-size:12px;color:#8fd">动态加载</span></h1>
<div class="m">尾盘5层评分选股(缩量/贴MA10/活跃度/回踩/尾盘支撑) · 次日开盘买入基准 · D1=次日,dN=第N交易日收盘累计收益% · <b style="color:#ffd27f">hit15=次日"开盘→盘中最高"≥+1.5%</b>(命名坑:15=1.5%) · hit20≥+2.0%</div>
<div class="m" id="cutoff"></div>
<div class="note" id="note"></div></div>
<div class="bar">
<div class="grp"><span class="lbl">年</span><div class="seg" id="ySeg"></div></div>
<div class="grp"><span class="lbl">月</span><div class="seg" id="mSeg"></div></div>
<div class="grp"><span class="lbl">尾盘</span>
<span class="chk on" data-tk="1">尾盘✓(V2信号)</span><span class="chk on" data-tk="0">尾盘✗(被刷)</span></div>
<div class="grp"><span class="lbl">分档</span>
<span class="chk on" data-bk="70+">70+</span><span class="chk on" data-bk="60-70">60-70</span>
<span class="chk on" data-bk="50-60">50-60</span><span class="chk on" data-bk="<50">&lt;50</span></div>
<div class="grp"><span class="lbl">rank</span>
<select id="rkSel"><option value="all">全部</option><option value="1-3">rank1-3</option><option value="4-5">rank4-5</option><option value="6+">rank6+</option></select></div>
<div class="grp"><span class="lbl">仅命中</span>
<select id="hitSel"><option value="all">全部</option><option value="h15">仅 hit15</option><option value="h20">仅 hit20</option><option value="hsl">仅 止损</option></select></div>
<div class="grp"><span class="lbl">排序</span>
<select id="sortSel"><option value="signal_date">选股日(按日分组)</option><option value="v3">v3b反推分</option><option value="score">V2 score</option><option value="rank">rank</option><option value="mh1">次日最高</option><option value="maxR">区间最高</option><option value="finR">末日</option></select></div>
</div>
<div class="legend">
<span>色阶 <b style="color:var(--green)">绿跌</b> <span class="scaleimg"></span> <b style="color:var(--red)">红涨</b></span>
<span><span class="swatch sw-miss">–</span> 未到期(不补0)</span>
<span><span class="b15">15</span> 次日开→高≥+1.5% · <span class="b20">20</span> ≥+2.0% · <span class="bsl">SL</span> 开→低≤-2.0%</span>
<span style="color:#888">只 D1–D10 与次日最高 染色</span>
</div>
<div class="mini" id="mini"></div>
<div class="tbox"><div class="spin" id="spin" style="display:none">加载数据中…</div>
<table><thead id="thead"></thead><tbody id="tbody"></tbody></table>
<div class="cap" id="cap" style="display:none"></div></div>
<div class="ft" id="ft"></div></div>
<div class="drawer" id="drawer"><span class="close" onclick="closeDrawer()">×</span><div id="dbody"></div></div>
<script>
const META=window.META; let POOL=[];
const DAYS=Array.from({length:10},(_,i)=>'d'+(i+1));
const MAXRENDER=1500;
function bkOf(s){return s>=70?'70+':s>=60?'60-70':s>=50?'50-60':'<50';}
let state={year:'all',month:'all',bk:{'70+':true,'60-70':true,'50-60':true,'<50':true},
  tk:{'1':true,'0':true},rk:'all',hit:'all',sort:'signal_date',asc:true};
function cellColor(v){
  if(v==null||isNaN(v))return null;
  const cap=15;let t=Math.max(-1,Math.min(1,v/cap));const a=Math.abs(t);
  const w=[255,255,255];const tgt=t>=0?[176,28,28]:[22,96,52];
  const c=w.map((x,i)=>Math.round(x+(tgt[i]-x)*a));
  const lum=(0.2126*c[0]+0.7152*c[1]+0.0722*c[2]);
  return{bg:`rgb(${c[0]},${c[1]},${c[2]})`,fg:lum<150?'#fff':'#14233b'};
}
function fmtPct(v){if(v==null||isNaN(v))return null;return(v>=0?'+':'')+v.toFixed(1)+'%';}
function plainRet(v){if(v==null||isNaN(v))return '<span style="color:#bbb">–</span>';
  const col=v>0?'#c0392b':v<0?'#1e8449':'#777';return `<span style="color:${col}">${fmtPct(v)}</span>`;}
function rkMatch(r){if(state.rk==='all')return true;const k=r.rk2;if(k==null)return false;
  return state.rk==='1-3'?k<=3:state.rk==='4-5'?(k>=4&&k<=5):k>=6;}
function curRows(){
  return POOL.filter(r=>{
    const y=r.signal_date.slice(0,4),mo=r.signal_date.slice(4,6);
    return (state.year==='all'||y===state.year)&&(state.month==='all'||mo===state.month)
      &&state.bk[bkOf(r.score)]&&state.tk[String(r.tok||0)]&&rkMatch(r)
      &&(state.hit==='all'||(state.hit==='h15'&&r.h15)||(state.hit==='h20'&&r.h20)||(state.hit==='hsl'&&r.hsl));
  });
}
function sortRows(rs){const k=state.sort;const s=[...rs];
  s.sort((a,b)=>{let x,y;
    if(k==='signal_date'){x=a.signal_date+(''+a.rank).padStart(2,'0');y=b.signal_date+(''+b.rank).padStart(2,'0');}
    else{x=a[k];y=b[k];x=(x==null?-1e9:x);y=(y==null?-1e9:y);}
    return state.asc?(x>y?1:x<y?-1:0):(x<y?1:x>y?-1:0);});
  return s;}
const FRZ=[['rk2','#',38],['code','代码',80],['name','名称',80],['signal_date','选股日',84],['score','score',54],['tok','尾盘',48]];
function buildHead(){
  let left=0;let h='<tr>';
  FRZ.forEach(c=>{h+=`<th class="frz s" style="left:${left}px" data-k="${c[0]}">${c[1]}</th>`;left+=c[2];});
  h+='<th class="s num" data-k="v3" title="反推评分: +MA张口 -回踩天 -尾盘通过 -当日涨跌 当日内rank加权, test段验证过">v3b</th><th class="s num" data-k="mh1">次日高</th><th>命中</th><th class="s num" data-k="maxR">区间高</th><th>顶日</th><th class="s num" data-k="finR">末日</th>';
  DAYS.forEach(d=>h+=`<th class="num">${d.toUpperCase()}</th>`);
  h+='</tr>';document.getElementById('thead').innerHTML=h;
  document.querySelectorAll('th.s').forEach(t=>t.onclick=()=>{const k=t.dataset.k;
    if(state.sort===k)state.asc=!state.asc;else{state.sort=k;state.asc=(k==='signal_date'||k==='rank');}
    render();});
}
function render(){
  const all=sortRows(curRows());
  const rs=all.slice(0,MAXRENDER);
  const grouped=(state.sort==='signal_date');
  let left,html='',prevDate=null;
  for(const r of rs){
    left=0;
    const gstart=grouped&&(r.signal_date!==prevDate);
    html+=`<tr class="rowx ${gstart?'gstart':''}" data-id="${r.signal_date}|${r.code}">`;
    const fz=(w,inner,extra='')=>{const s=`<td class="frz ${extra}" style="left:${left}px">${inner}</td>`;left+=w;return s;};
    html+=fz(38,r.rk2!=null?r.rk2:'<span style="color:#ccc">–</span>','num');
    html+=fz(80,r.code);
    html+=fz(80,r.name||'');
    html+=fz(84,(grouped&&!gstart)?'<span style="color:#ccc">〃</span>':(r.signal_date.slice(0,4)+'-'+r.signal_date.slice(4,6)+'-'+r.signal_date.slice(6,8)));
    html+=fz(54,`<b>${r.score==null?'':r.score}</b>`,'num');
    html+=fz(48,r.tok?'<span style="color:#1e8449;font-weight:bold">✓</span>':'<span style="color:#aaa">✗</span>');
    html+=`<td class="num" style="color:#7b1fa2;font-weight:${(r.v3||0)>=75?'bold':'normal'}">${r.v3==null?'':r.v3.toFixed(0)}</td>`;
    // 次日最高
    {const v=r.mh1;if(v==null)html+='<td class="num miss">–</td>';else{const c=cellColor(v);html+=`<td class="num" style="background:${c.bg};color:${c.fg}">${fmtPct(v)}</td>`;}}
    // 命中徽章
    let bd='';if(r.h20)bd='<span class="b20">20</span>';else if(r.h15)bd='<span class="b15">15</span>';if(r.hsl)bd+=' <span class="bsl">SL</span>';
    html+=`<td style="text-align:center">${bd||'<span style="color:#ccc">·</span>'}</td>`;
    html+=`<td class="num">${plainRet(r.maxR)}</td>`;
    html+=`<td class="num" style="color:#888">${r.day_to_peak||''}</td>`;
    html+=`<td class="num">${plainRet(r.finR)}</td>`;
    for(let i=1;i<=10;i++){const v=r['d'+i];
      if(v==null)html+='<td class="num miss">–</td>';
      else{const c=cellColor(v);html+=`<td class="num" style="background:${c.bg};color:${c.fg}">${fmtPct(v)}</td>`;}}
    html+='</tr>';prevDate=r.signal_date;
  }
  document.getElementById('tbody').innerHTML=html||'<tr><td style="padding:20px">无数据(换筛选)</td></tr>';
  document.querySelectorAll('tr.rowx').forEach(tr=>tr.onclick=()=>openDrawer(tr.dataset.id));
  const cap=document.getElementById('cap');
  if(all.length>MAXRENDER){cap.style.display='block';cap.textContent=`命中 ${all.length} 行,只渲染前 ${MAXRENDER}。请收窄筛选。`;}
  else cap.style.display='none';
  renderMini(all);
  document.getElementById('ft').textContent=`${META.generated_for} · 全库 ${POOL.length} 信号 · 视图命中 ${all.length}`;
}
function med(a){if(!a.length)return null;const s=[...a].sort((x,y)=>x-y);const m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;}
function rate(a,f){const v=a.filter(f).length;return a.length?100*v/a.length:0;}
function renderMini(rs){
  const n=rs.length;
  const h15=rate(rs,r=>r.h15),h20=rate(rs,r=>r.h20);
  const d1=rs.map(r=>r.d1).filter(v=>v!=null),d5=rs.map(r=>r.d5).filter(v=>v!=null),d10=rs.map(r=>r.d10).filter(v=>v!=null);
  let cmp='';
  [['70+'],['60-70'],['50-60'],['<50']].forEach(([bk])=>{
    const a=rs.filter(r=>bkOf(r.score)===bk);
    cmp+=`<div class="cmpcard"><div class="t">${bk} (n=${a.length})</div>hit15 <b>${rate(a,r=>r.h15).toFixed(0)}%</b> · D1中位 ${a.length?med(a.map(r=>r.d1).filter(v=>v!=null)).toFixed(1):'–'}%</div>`;});
  // 月度 hit15 柱
  const mon={};rs.forEach(r=>{const ym=r.signal_date.slice(0,6);(mon[ym]=mon[ym]||[]).push(r);});
  const yms=Object.keys(mon).sort();
  let bars=yms.map(ym=>{const h=rate(mon[ym],r=>r.h15);const col=h>=50?'#1e8449':h>=40?'#f0a30a':'#c0392b';
    return `<div class="mb"><span>${Math.round(h)}</span><i style="height:${Math.max(3,h*0.5)}px;background:${col}"></i><span>${ym.slice(2,4)}/${ym.slice(4,6)}</span></div>`;}).join('');
  document.getElementById('mini').innerHTML=
    `<div class="kpi"><span class="v">${n}</span><span class="l">命中信号</span></div>
     <div class="kpi"><span class="v" style="color:var(--red)">${h15.toFixed(0)}%</span><span class="l">hit15 次日开→高≥+1.5%</span></div>
     <div class="kpi"><span class="v">${h20.toFixed(0)}%</span><span class="l">hit20 ≥+2.0%</span></div>
     <div class="kpi"><span class="v">${d1.length?med(d1).toFixed(1):'–'}%</span><span class="l">D1收盘中位</span></div>
     <div class="kpi" style="border:0"><span class="v">${d1.length?rate(d1,v=>v>0).toFixed(0):'–'}%</span><span class="l">D1收红率</span></div>
     <div style="flex:1"><div style="font-size:11px;color:#888;margin-bottom:2px">分档 hit15</div><div class="cmp">${cmp}</div></div>
     <div><div style="font-size:11px;color:#888">月度 hit15%</div><div class="monthbar">${bars}</div></div>`;
}
const FIELDS=[['score','V2评分'],['v3','v3b反推分(0-100,当日内相对)'],['tok','尾盘通过(V2 gate)'],['rk2','V2排名(过尾盘内)'],['rank','当日全候选位次'],['env','环境组'],['pvr','缩量比'],['ma10d','MA10距%'],
['luc','10日涨停数'],['pbd','回踩天'],['tsp','尾盘通过数'],['gap','次日跳空%'],['og','开盘组'],['eg','出场组'],
['mh1','次日开→高%'],['noh','次日开→高%'],['noc','次日开→收%'],['h15','hit15 开→高≥1.5%'],['h20','hit20 ≥2.0%'],['hsl','SL 开→低≤-2.0%'],
['maxR','区间最大涨幅%'],['day_to_peak','到顶第几日'],['finR','末日收益%'],['final_day','末日'],['days_available','有效天'],['window_incomplete','右侧截断']];
function openDrawer(id){
  const r=POOL.find(x=>x.signal_date+'|'+x.code===id);if(!r)return;
  let h=`<h3>${r.code} ${r.name||''} <b style="font-size:12px;color:#888">score ${r.score}</b></h3>
  <div style="color:#888;font-size:12px;margin-bottom:8px">选股日 ${r.signal_date} · rank ${r.rank} ${r.h15?'· <span class="b15">15</span>':''}${r.h20?' <span class="b20">20</span>':''}${r.hsl?' <span class="bsl">SL</span>':''}</div><table>`;
  FIELDS.forEach(([k,lab])=>{let v=r[k];if(v==null||v===undefined)v='—';else if(v===true)v='是';else if(v===false)v='否';
    h+=`<tr><td>${lab}</td><td>${v}</td></tr>`;});
  h+='</table><div style="margin-top:10px;font-size:12px;color:#666">D1–D10 收盘收益(次日开盘买入基准):</div><table>';
  for(let i=1;i<=10;i++){const v=r['d'+i];h+=`<tr><td>D${i}</td><td>${v==null?'<span style="color:#bbb">未到期</span>':((v>=0?'+':'')+v.toFixed(2)+'%')}</td></tr>`;}
  h+='</table>';document.getElementById('dbody').innerHTML=h;document.getElementById('drawer').classList.add('open');
}
function closeDrawer(){document.getElementById('drawer').classList.remove('open');}
function buildSeg(id,vals,key){
  const el=document.getElementById(id);
  el.innerHTML=vals.map(v=>`<button data-v="${v[0]}" class="${String(state[key])===String(v[0])?'on':''}">${v[1]}</button>`).join('');
  el.querySelectorAll('button').forEach(b=>b.onclick=()=>{state[key]=b.dataset.v;
    el.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));render();});
}
function applyUrl(){try{const q=new URLSearchParams(location.search);
  if(q.get('year'))state.year=q.get('year');if(q.get('month'))state.month=q.get('month');
  if(q.get('rk'))state.rk=q.get('rk');if(q.get('hit'))state.hit=q.get('hit');if(q.get('sort'))state.sort=q.get('sort');
}catch(e){}}
function init(){
  applyUrl();
  document.getElementById('rkSel').value=state.rk;document.getElementById('hitSel').value=state.hit;document.getElementById('sortSel').value=state.sort;
  const c=META.cutoff||{};
  document.getElementById('cutoff').innerHTML=`区间 <b>${META.range}</b> · 全候选 <b>${META.count}</b>(其中过尾盘 <b>${META.count_pass||'?'}</b>) · hit15: 全候选 <b>${META.hit15_overall}%</b> / 过尾盘 <b>${META.hit15_pass||'?'}%</b> · 数据截止 <b>${c.signal||'?'}</b>`;
  document.getElementById('note').textContent=META.note+' · '+(c.note||'');
  buildSeg('ySeg',[['all','全部'],...META.years.map(y=>[y,y])],'year');
  buildSeg('mSeg',[['all','全部'],...Array.from({length:12},(_,i)=>{const mm=String(i+1).padStart(2,'0');return [mm,mm];})],'month');
  document.querySelectorAll('.chk[data-bk]').forEach(ch=>{ch.classList.toggle('on',state.bk[ch.dataset.bk]);
    ch.onclick=()=>{state.bk[ch.dataset.bk]=!state.bk[ch.dataset.bk];ch.classList.toggle('on');render();};});
  document.querySelectorAll('.chk[data-tk]').forEach(ch=>{ch.classList.toggle('on',state.tk[ch.dataset.tk]);
    ch.onclick=()=>{state.tk[ch.dataset.tk]=!state.tk[ch.dataset.tk];ch.classList.toggle('on');render();};});
  document.getElementById('rkSel').onchange=e=>{state.rk=e.target.value;render();};
  document.getElementById('hitSel').onchange=e=>{state.hit=e.target.value;render();};
  document.getElementById('sortSel').onchange=e=>{state.sort=e.target.value;state.asc=(e.target.value==='signal_date'||e.target.value==='rank');render();};
  buildHead();
  const s=document.createElement('script');s.src='data/pool.js';
  document.getElementById('spin').style.display='flex';
  s.onload=()=>{POOL=window.POOL||[];document.getElementById('spin').style.display='none';render();};
  s.onerror=()=>{document.getElementById('spin').textContent='加载 data/pool.js 失败(需与本页同目录)';};
  document.head.appendChild(s);
}
init();
</script></body></html>"""

def main():
    os.makedirs(VIEWER, exist_ok=True)
    out = os.path.join(VIEWER, '尾盘选股forward回看表.html')
    io.open(out,'w',encoding='utf-8').write(HTML)
    print('HTML:', out)

if __name__ == '__main__':
    main()
