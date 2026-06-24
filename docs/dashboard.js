/* Iran Stock AI Dashboard — external JS */
'use strict';
const DATA = JSON.parse(document.getElementById('__DATA__').textContent);
const PERF = JSON.parse(document.getElementById('__PERF__').textContent);

function switchTab(t){
  ['main','perf'].forEach(function(n){
    document.getElementById('tab-'+n).classList.toggle('active',n===t);
    document.getElementById('tab-btn-'+n).classList.toggle('active',n===t);
  });
  if(t==='perf')renderPerf();
}
var _s=900;
(function tick(){
  var m=Math.floor(_s/60),s=_s%60;
  document.getElementById('cd').textContent='بروزرسانی: '+m+':'+(s<10?'0':'')+s;
  if(_s>0)_s--;
  setTimeout(tick,1000);
})();
var _tags={},_sk='score',_sa=false,_kf=null,_chartsOpen=true;
function toggleCharts(){
  _chartsOpen=!_chartsOpen;
  document.getElementById('chartsBody').style.display=_chartsOpen?'block':'none';
  document.getElementById('chartsToggle').classList.toggle('open',_chartsOpen);
}
function toggleTag(t){
  _tags[t]=!_tags[t];_kf=null;
  document.getElementById('btn'+t.charAt(0).toUpperCase()+t.slice(1)).classList.toggle('on',_tags[t]);
  render();
}
function kpiF(type){
  _kf=_kf===type?null:type;
  document.getElementById('fL').value='';document.getElementById('fG').value='';
  Object.keys(_tags).forEach(function(t){
    _tags[t]=false;
    var el=document.getElementById('btn'+t.charAt(0).toUpperCase()+t.slice(1));
    if(el)el.classList.remove('on');
  });
  render();
}
function filtered(){
  var q=(document.getElementById('q').value||'').toLowerCase();
  var fL=document.getElementById('fL').value,fG=document.getElementById('fG').value;
  var fS=document.getElementById('fS').value,fR=document.getElementById('fR').value;
  return DATA.filter(function(d){
    if(q&&!d.sym.toLowerCase().includes(q)&&!(d.sector||'').toLowerCase().includes(q))return false;
    if(fL&&d.label_fa!==fL)return false;
    if(fG&&d.grade!==fG)return false;
    if(fS&&d.sector!==fS)return false;
    if(fR&&d.rsi_band!==fR)return false;
    if(_tags.complete&&d.missing)return false;
    if(_tags.conflict&&!d.conflict)return false;
    if(_tags.changes&&!d.change)return false;
    if(_kf==='entry'&&d.label!=='Entry Candidate')return false;
    if(_kf==='highc'&&d.score<80)return false;
    if(_kf==='overbought'&&d.label!=='Avoid Entry Now - Overbought')return false;
    if(_kf==='conflict'&&!d.conflict)return false;
    if(_kf==='missing'&&!d.missing)return false;
    return true;
  });
}
function sorted(arr){
  return arr.slice().sort(function(a,b){
    var av=a[_sk],bv=b[_sk];
    if(typeof av==='number'&&typeof bv==='number')return _sa?av-bv:bv-av;
    av=String(av||'');bv=String(bv||'');
    return _sa?(av<bv?-1:av>bv?1:0):(bv<av?-1:bv>av?1:0);
  });
}
function srt(k,c){
  if(_sk===k)_sa=!_sa;else{_sk=k;_sa=false;}
  document.querySelectorAll('.arr').forEach(function(el){el.textContent='';});
  var a=document.getElementById('a'+c);if(a)a.textContent=_sa?'↑':'↓';
  render();
}
function e(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function render(){
  var rows=sorted(filtered()),html='';
  rows.forEach(function(d){
    var cls='row'+(d.missing?' is-missing':'')+(d.stale&&!d.missing?' is-stale':'');
    var sb=d.score?'<div class="sb-wrap"><div class="sb" style="width:'+Math.min(d.score,100)+'%;background:'+e(d.label_color)+'"></div></div>':'';
    var ci=d.change==='up'?'<span title="ارتقاء"> ⬆️</span>':d.change==='down'?'<span title="افت"> ⬇️</span>':d.change==='changed'?'<span title="تغییر"> 🔄</span>':'';
    var wi=d.conflict?'<span style="color:#ff9100;font-size:11px"> ⚠️</span>':'';
    var si=d.stale&&!d.missing?'<span style="color:#78909c;font-size:10px"> 🕐</span>':'';
    var vol=parseFloat(d.vol)||0,vc=vol>=2?'#00c853':vol>=1?'#ffd740':'#78909c';
    var sp=d.close_20d?'<canvas class="spark" data-p="'+e(d.close_20d)+'" width="80" height="26"></canvas>':'';
    html+='<tr class="'+cls+'" onclick="openDr('+DATA.indexOf(d)+')">'
      +'<td><b>'+e(d.sym)+'</b>'+ci+wi+si+'</td>'
      +'<td><span class="badge" style="color:'+e(d.label_color)+';background:'+e(d.label_bg)+'">'+e(d.label_fa)+'</span></td>'
      +'<td style="text-align:center"><b style="color:'+e(d.grade_color)+'">'+e(d.grade)+'</b></td>'
      +'<td style="text-align:center">'+(d.score?d.score.toFixed(0):'')+sb+'</td>'
      +'<td style="text-align:center"><span class="rbadge" style="color:'+e(d.rsi_color)+'">'+e(d.rsi)+'</span></td>'
      +'<td style="text-align:center">'+e(d.price)+'</td>'
      +'<td style="text-align:center;color:#90caf9;font-size:11px">'+e(d.sector)+'</td>'
      +'<td style="text-align:center;color:'+vc+'">'+(vol>0?vol.toFixed(1)+'x':'—')+'</td>'
      +'<td style="font-size:11px">'+e(d.sm)+'</td>'
      +'<td>'+sp+'</td></tr>';
  });
  document.getElementById('tb').innerHTML=html;
  document.getElementById('emp').style.display=rows.length?'none':'block';
  drawSparks();drawTopPicks();
  requestAnimationFrame(function(){drawDist();drawScatter();drawHeat();});
}
function drawSparks(){
  document.querySelectorAll('.spark').forEach(function(c){
    var p=c.dataset.p.split(',').map(Number).filter(function(n){return n>0;});
    if(p.length<2)return;
    var ctx=c.getContext('2d'),w=c.width,h=c.height,n=p.length;
    var mn=Math.min.apply(null,p),mx=Math.max.apply(null,p),rng=mx-mn||1;
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle=p[n-1]>=p[0]?'#00e676':'#ff5252';
    ctx.lineWidth=1.5;ctx.beginPath();
    p.forEach(function(v,i){var x=i/(n-1)*w,y=h-(v-mn)/rng*(h-4)-2;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.stroke();
  });
}
function drawTopPicks(){
  var picks=DATA.filter(function(d){return d.label==='Entry Candidate'&&d.score>=75&&!d.missing;})
    .sort(function(a,b){return b.score-a.score;}).slice(0,5);
  var bar=document.getElementById('tpBar');
  if(!picks.length){bar.style.display='none';return;}
  bar.style.display='block';
  document.getElementById('tpRow').innerHTML=picks.map(function(d){
    return '<div class="pick" onclick="openDr('+DATA.indexOf(d)+')">'
      +'<div class="pick-sym">'+e(d.sym)+'</div>'
      +'<div class="pick-sc">امتیاز '+d.score.toFixed(0)+' | <span style="color:'+e(d.grade_color)+'">'+e(d.grade)+'</span></div>'
      +'<div class="pick-gr">'+e(d.rsi_band)+' | '+e(d.sector)+'</div></div>';
  }).join('');
}
function drawDist(){
  var c=document.getElementById('cDist');if(!c)return;
  var W=c.offsetWidth||300;c.width=W;c.height=190;
  var ctx=c.getContext('2d');ctx.clearRect(0,0,W,190);
  var labels=['ورود قوی','ورود','تماشا — پولبک','تماشا — حجم','نگهداری','خروج / اشباع','داده ناقص'];
  var colors=['#00c853','#69f0ae','#ffd740','#ffab40','#40c4ff','#ff5252','#78909c'];
  var counts=labels.map(function(l){return DATA.filter(function(d){return d.label_fa===l;}).length;});
  var mx=Math.max.apply(null,counts)||1;
  var rowH=24,pad=4,labelW=110,barX=labelW+8,barMaxW=W-labelW-50;
  ctx.font='11px Tahoma,Arial,sans-serif';ctx.textAlign='right';ctx.textBaseline='middle';
  labels.forEach(function(l,i){
    var y=pad+i*rowH+rowH/2,bw=Math.max((counts[i]/mx)*barMaxW,1);
    ctx.fillStyle='#21262d';ctx.fillRect(barX,y-8,barMaxW,16);
    ctx.fillStyle=colors[i];ctx.fillRect(barX,y-8,bw,16);
    ctx.fillStyle='#c9d1d9';ctx.fillText(l,labelW,y);
    ctx.fillStyle=colors[i];ctx.textAlign='left';ctx.fillText(counts[i],barX+bw+4,y);ctx.textAlign='right';
  });
  c.onclick=function(ev){
    var rect=c.getBoundingClientRect(),y=ev.clientY-rect.top,i=Math.floor((y-pad)/rowH);
    if(i>=0&&i<labels.length&&counts[i]>0){document.getElementById('fL').value=labels[i];render();}
  };
  c.style.cursor='pointer';
}
function drawScatter(){
  var c=document.getElementById('cScatter');if(!c)return;
  var W=c.offsetWidth||300;c.width=W;c.height=190;
  var ctx=c.getContext('2d');ctx.clearRect(0,0,W,190);
  var PAD={t:10,r:10,b:30,l:30},pw=W-PAD.l-PAD.r,ph=190-PAD.t-PAD.b;
  var dz=PAD.l+pw*0.8;
  ctx.fillStyle='rgba(255,82,82,.07)';ctx.fillRect(dz,PAD.t,pw*0.2,ph);
  ctx.strokeStyle='#ff525255';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(dz,PAD.t);ctx.lineTo(dz,PAD.t+ph);ctx.stroke();
  ctx.strokeStyle='#30363d';ctx.beginPath();
  ctx.moveTo(PAD.l,PAD.t);ctx.lineTo(PAD.l,PAD.t+ph);
  ctx.moveTo(PAD.l,PAD.t+ph);ctx.lineTo(PAD.l+pw,PAD.t+ph);ctx.stroke();
  ctx.fillStyle='#484f58';ctx.font='9px Tahoma';ctx.textAlign='center';
  [0,25,50,75,100].forEach(function(v){ctx.fillText(v,PAD.l+pw*(v/100),PAD.t+ph+14);});
  ctx.textAlign='right';
  [0,25,50,75,100].forEach(function(v){ctx.fillText(v,PAD.l-4,PAD.t+ph-ph*(v/100)+3);});
  ctx.fillStyle='#8b949e';ctx.font='10px Tahoma';ctx.textAlign='center';
  ctx.fillText('RSI',PAD.l+pw/2,PAD.t+ph+26);
  var visible=filtered();
  DATA.forEach(function(d){
    var rsi=parseFloat(d.rsi)||0,sc=d.score||0;if(!rsi||!sc)return;
    var x=PAD.l+pw*(rsi/100),y=PAD.t+ph-ph*(sc/100);
    var vol=parseFloat(d.vol)||1,r=Math.min(Math.max(vol*2.5,3),10);
    var inFilter=visible.indexOf(d)>=0;
    ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);
    ctx.fillStyle=inFilter?d.label_color+'cc':'#30363d';ctx.fill();
    if(inFilter&&d.conflict){ctx.strokeStyle='#ff9100';ctx.lineWidth=2;ctx.stroke();}
  });
  var tt=document.getElementById('stt');
  c.onmousemove=function(ev){
    var rect=c.getBoundingClientRect(),mx=ev.clientX-rect.left,my=ev.clientY-rect.top,found=null,minD=999;
    DATA.forEach(function(d){
      var rsi=parseFloat(d.rsi)||0,sc=d.score||0;if(!rsi||!sc)return;
      var x=PAD.l+pw*(rsi/100),y2=PAD.t+ph-ph*(sc/100),dist=Math.sqrt((mx-x)*(mx-x)+(my-y2)*(my-y2));
      if(dist<14&&dist<minD){minD=dist;found=d;}
    });
    if(found){
      tt.style.display='block';tt.style.left=(ev.clientX+12)+'px';tt.style.top=(ev.clientY-10)+'px';
      tt.innerHTML='<b>'+e(found.sym)+'</b><br>Score: '+found.score.toFixed(0)+'<br>RSI: '+e(found.rsi)+'<br>'+e(found.label_fa);
      c.style.cursor='pointer';
    }else{tt.style.display='none';c.style.cursor='crosshair';}
  };
  c.onmouseleave=function(){tt.style.display='none';};
  c.onclick=function(ev){
    var rect=c.getBoundingClientRect(),mx=ev.clientX-rect.left,my=ev.clientY-rect.top,found=null,minD=999;
    DATA.forEach(function(d){
      var rsi=parseFloat(d.rsi)||0,sc=d.score||0;if(!rsi||!sc)return;
      var x=PAD.l+pw*(rsi/100),y2=PAD.t+ph-ph*(sc/100),dist=Math.sqrt((mx-x)*(mx-x)+(my-y2)*(my-y2));
      if(dist<14&&dist<minD){minD=dist;found=d;}
    });
    if(found)openDr(DATA.indexOf(found));
  };
}
function drawHeat(){
  var el=document.getElementById('cHeat');if(!el)return;
  var sectors={};
  DATA.forEach(function(d){
    if(!d.sector)return;
    if(!sectors[d.sector])sectors[d.sector]={n:0,sc:0,entry:0,over:0,miss:0};
    var s=sectors[d.sector];s.n++;s.sc+=d.score;
    if(d.label==='Entry Candidate')s.entry++;
    if(d.label==='Avoid Entry Now - Overbought')s.over++;
    if(d.missing)s.miss++;
  });
  var arr=Object.keys(sectors).map(function(k){
    var s=sectors[k];return{name:k,avg:s.n?Math.round(s.sc/s.n):0,entry:s.entry,over:s.over,miss:s.miss};
  }).sort(function(a,b){return b.avg-a.avg;});
  var maxAvg=arr.length?arr[0].avg:100;
  el.innerHTML=arr.map(function(s){
    var pct=maxAvg?s.avg/maxAvg*100:0;
    var bc=s.avg>=80?'#00c853':s.avg>=65?'#ffd740':s.avg>=50?'#ff9100':'#ff5252';
    var meta=(s.entry?'🟢'+s.entry+' ':'')+(s.over?'🔴'+s.over+' ':'')+(s.miss?'□'+s.miss:'');
    return '<div class="hm-row" onclick="filterBySector(\''+e(s.name)+'\')">'
      +'<div class="hm-name">'+e(s.name)+'</div>'
      +'<div class="hm-bar-wrap"><div class="hm-bar" style="width:'+pct+'%;background:'+bc+'">'+s.avg+'</div></div>'
      +'<div class="hm-meta">'+meta+'</div></div>';
  }).join('');
}
function filterBySector(sec){
  document.getElementById('fS').value=sec;render();
  document.getElementById('tb').scrollIntoView({behavior:'smooth',block:'start'});
}
function openDr(idx){
  var d=DATA[idx];if(!d)return;
  var cw=d.conflict?'<div class="wbox" style="background:#1a0e00;border:1px solid #ff910088;color:#ff9100">⚠️ امتیاز بالا اما RSI خطرناک</div>':'';
  var mw=d.missing?'<div class="wbox" style="background:#111518;border:1px solid #78909c88;color:#78909c">داده تکنیکال ناقص</div>':'';
  var sw=d.stale&&!d.missing?'<div class="wbox" style="background:#0d1117;border:1px solid #ffd74044;color:#ffd740">داده قدیمی</div>':'';
  var chg='';
  if(d.change){
    var ar=d.change==='up'?'⬆️':d.change==='down'?'⬇️':'🔄';
    chg='<div style="color:#8b949e;font-size:11px;margin-top:6px">'+ar+' از <b>'+e(d.prev_label_fa)+'</b> به <b style="color:'+e(d.label_color)+'">'+e(d.label_fa)+'</b></div>';
  }
  var sp=d.close_20d?'<canvas id="dsp" data-p="'+e(d.close_20d)+'" width="340" height="70" style="margin-top:10px;display:block"></canvas>':'';
  function r(l,v){return v?'<dt>'+l+'</dt><dd>'+e(v)+'</dd>':''}
  var vol=parseFloat(d.vol)||0;
  document.getElementById('dc').innerHTML=
    '<div style="padding-top:8px;margin-bottom:12px">'
    +'<div style="font-size:18px;font-weight:700">'+e(d.sym)+'</div>'
    +'<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
    +'<span class="badge" style="color:'+e(d.label_color)+';background:'+e(d.label_bg)+'">'+e(d.label_fa)+'</span>'
    +'<span style="color:'+e(d.grade_color)+';font-weight:700;font-size:15px">'+e(d.grade)+'</span>'
    +'<span style="color:#8b949e">امتیاز '+d.score.toFixed(0)+'</span>'
    +'</div>'+chg+'</div>'
    +cw+mw+sw
    +'<div class="dsec"><h4>دلایل تصمیم</h4><p style="color:#ccc;font-size:12px;line-height:1.8">'+e(d.reasons)+'</p></div>'
    +'<div class="dsec"><h4>عوامل امتیاز</h4><p style="color:#8b949e;font-size:11px;line-height:1.8">'+e(d.factors)+'</p></div>'
    +'<div class="dsec"><h4>مشخصات فنی</h4><dl class="dl">'
    +r('RSI',d.rsi+(d.rsi_band?' ('+d.rsi_band+')':''))
    +r('قیمت',d.price)+r('روند',d.trend?d.trend+'/6':'')
    +r('نسبت حجم',vol>0?vol.toFixed(2)+'x':'')
    +r('سکتور',d.sector)+r('حمایت',d.support)+r('مقاومت',d.resistance)
    +r('حد ضرر',d.stop_loss)+r('هدف',d.target_1)+r('R/R',d.rr)
    +'</dl></div>'
    +'<div class="dsec"><h4>پول هوشمند</h4><dl class="dl">'
    +r('پول هوشمند',d.sm)+r('توضیح',d.sm_fa)+r('صف',d.q)+r('توضیح صف',d.q_fa)
    +'</dl></div>'+sp;
  document.getElementById('ov').classList.add('open');
  document.body.style.overflow='hidden';
  if(d.close_20d){
    setTimeout(function(){
      var c=document.getElementById('dsp');if(!c)return;
      var p=c.dataset.p.split(',').map(Number).filter(function(n){return n>0;});
      if(p.length<2)return;
      var ctx=c.getContext('2d'),w=c.width,h=c.height,n=p.length;
      var mn=Math.min.apply(null,p),mx=Math.max.apply(null,p),rng=mx-mn||1;
      ctx.strokeStyle=p[n-1]>=p[0]?'#00e676':'#ff5252';
      ctx.lineWidth=2;ctx.beginPath();
      p.forEach(function(v,i){var x=i/(n-1)*w,y=h-(v-mn)/rng*(h-6)-3;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
      ctx.stroke();
    },50);
  }
}
function closeDr(ev){
  if(ev&&ev.target!==document.getElementById('ov'))return;
  document.getElementById('ov').classList.remove('open');
  document.body.style.overflow='';
}
document.addEventListener('keydown',function(ev){if(ev.key==='Escape')closeDr();});
function doExport(){
  var rows=[['نماد','وضعیت','رتبه','امتیاز','RSI','باند RSI','قیمت','سکتور','حجم','پول هوشمند','صف','دلایل']];
  filtered().forEach(function(d){
    var vol=parseFloat(d.vol)||0;
    rows.push([d.sym,d.label_fa,d.grade,d.score.toFixed(0),d.rsi,d.rsi_band,d.price,d.sector,
      vol>0?vol.toFixed(2)+'x':'',d.sm,d.q,d.reasons]);
  });
  var csv=rows.map(function(r){return r.map(function(c){return'"'+String(c||'').replace(/"/g,'""')+'"'}).join(',')}).join('\n');
  var a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,﻿'+encodeURIComponent(csv);
  a.download='iran_stock_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
}
function renderPerf(){
  var el=document.getElementById('perfContent');
  if(!PERF||!PERF.completed){
    el.innerHTML='<div class="perf-empty"><div style="font-size:2rem;margin-bottom:12px">📭</div>'
      +'<div>هنوز داده‌ای برای بک‌تست ثبت نشده.</div>'
      +'<div style="font-size:11px;margin-top:8px;color:#484f58">تعداد: '+(PERF.total_logged||0)+'</div></div>';
    return;
  }
  var wr=PERF.win_rate,ar=PERF.avg_ret;
  var wrColor=wr>=60?'#00c853':wr>=45?'#ffd740':'#ff5252';
  var arColor=ar>0?'#00c853':ar<0?'#ff5252':'#ffd740';
  var lc={'ورود قوی':'#00c853','ورود':'#69f0ae','تماشا — پولبک':'#ffd740','تماشا — حجم':'#ffab40','نگهداری':'#40c4ff','خروج / اشباع':'#ff5252'};
  var cards='<div class="perf-kpi">'
    +'<div class="perf-card" style="border-color:#1f3a5f"><div class="pv" style="color:#90caf9">'+PERF.total_logged+'</div><div class="pl">کل سیگنال</div></div>'
    +'<div class="perf-card"><div class="pv" style="color:#c9d1d9">'+PERF.completed+'</div><div class="pl">دارای نتیجه</div></div>'
    +'<div class="perf-card" style="border-color:'+wrColor+'44"><div class="pv" style="color:'+wrColor+'">'+wr+'%</div><div class="pl">موفقیت</div></div>'
    +'<div class="perf-card" style="border-color:'+arColor+'44"><div class="pv" style="color:'+arColor+'">'+(ar>0?'+':'')+ar+'%</div><div class="pl">میانگین بازده</div></div>'
    +'</div>';
  var byLabel=PERF.by_label||{};
  var labelOrder=['ورود قوی','ورود','تماشا — پولبک','تماشا — حجم','نگهداری','خروج / اشباع'];
  var labelRows='';
  labelOrder.forEach(function(l){
    var v=byLabel[l];if(!v||!v.n)return;
    var wc=v.win_rate>=60?'#00c853':v.win_rate>=45?'#ffd740':'#ff5252';
    var ac=v.avg_ret>0?'#00c853':v.avg_ret<0?'#ff5252':'#aaa';
    labelRows+='<div class="perf-row">'
      +'<div class="perf-label" style="color:'+(lc[l]||'#8b949e')+'">'+e(l)+'</div>'
      +'<div class="perf-bar-wrap"><div class="perf-bar" style="width:'+v.win_rate+'%;background:'+wc+'"></div></div>'
      +'<div class="perf-val" style="color:'+wc+'">'+v.win_rate+'%</div>'
      +'<div style="font-size:11px;color:'+ac+';min-width:70px">'+(v.avg_ret>0?'+':'')+v.avg_ret+'%</div>'
      +'<div style="font-size:10px;color:#484f58;min-width:40px">n='+v.n+'</div></div>';
  });
  var byGrade=PERF.by_grade||{};
  var gc={'A+':'#00e676','A':'#69f0ae','B':'#ffd740','C':'#ff9100','D':'#ff5252'};
  var gradeRows='';
  ['A+','A','B','C','D'].forEach(function(g){
    var v=byGrade[g];if(!v||!v.n)return;
    var wc=v.win_rate>=60?'#00c853':v.win_rate>=45?'#ffd740':'#ff5252';
    var ac=v.avg_ret>0?'#00c853':v.avg_ret<0?'#ff5252':'#aaa';
    gradeRows+='<div class="perf-row">'
      +'<div class="perf-label" style="color:'+(gc[g]||'#78909c')+';font-weight:700;font-size:15px">'+e(g)+'</div>'
      +'<div class="perf-bar-wrap"><div class="perf-bar" style="width:'+v.win_rate+'%;background:'+wc+'"></div></div>'
      +'<div class="perf-val" style="color:'+wc+'">'+v.win_rate+'%</div>'
      +'<div style="font-size:11px;color:'+ac+';min-width:70px">'+(v.avg_ret>0?'+':'')+v.avg_ret+'%</div>'
      +'<div style="font-size:10px;color:#484f58;min-width:40px">n='+v.n+'</div></div>';
  });
  var recentRows=(PERF.recent||[]).map(function(r){
    var rc=r.ret>0?'#00c853':r.ret<0?'#ff5252':'#aaa';
    return '<tr>'
      +'<td><span class="sym-link" onclick="openSymDrill(\''+e(r.sym)+'\')">'+e(r.sym)+'</span></td>'
      +'<td style="color:'+(lc[r.label_fa]||'#aaa')+'">'+e(r.label_fa)+'</td>'
      +'<td>'+e(r.grade)+'</td><td>'+e(r.date.slice(0,10))+'</td>'
      +'<td>'+e(r.entry)+'</td><td>'+e(r.exit)+'</td>'
      +'<td style="color:'+rc+';font-weight:600">'+(r.ret>0?'+':'')+r.ret+'%</td></tr>';
  }).join('');
  var curve=PERF.equity_curve||[];
  var rwr=PERF.rolling_wr||[];
  el.innerHTML='<div class="perf-section">'+cards
    +'<div class="perf-grid" style="margin-bottom:14px">'
    +'<div class="perf-box"><h3>📈 منحنی سرمایه</h3>'
    +(curve.length>1?'<canvas id="eqCurve" style="width:100%;height:140px;display:block"></canvas>':'<div style="color:#484f58;font-size:12px">داده کافی نیست</div>')
    +'</div>'
    +'<div class="perf-box"><h3>🎯 نرخ موفقیت رولینگ</h3>'
    +(rwr.length>1?'<canvas id="rwrChart" style="width:100%;height:140px;display:block"></canvas>':'<div style="color:#484f58;font-size:12px">داده کافی نیست</div>')
    +'</div></div>'
    +'<div class="perf-grid">'
    +'<div class="perf-box"><h3>📊 به تفکیک وضعیت</h3>'+(labelRows||'<div style="color:#484f58">داده کافی نیست</div>')+'</div>'
    +'<div class="perf-box"><h3>🏅 به تفکیک رتبه</h3>'+(gradeRows||'<div style="color:#484f58">داده کافی نیست</div>')+'</div>'
    +'</div><div style="margin-top:14px"><div class="perf-box"><h3>🕐 آخرین معاملات</h3>'
    +'<table class="recent-table"><thead><tr><th>نماد</th><th>وضعیت</th><th>رتبه</th><th>تاریخ</th><th>ورود</th><th>خروج</th><th>بازده</th></tr></thead>'
    +'<tbody>'+recentRows+'</tbody></table></div></div></div>';
  if(curve.length>1)setTimeout(function(){drawEquity(curve,'eqCurve');},0);
  if(rwr.length>1)setTimeout(function(){drawRollingWR(rwr);},0);
}
function drawEquity(curve,canvasId){
  var c=document.getElementById(canvasId||'eqCurve');if(!c)return;
  var dpr=window.devicePixelRatio||1,W=c.offsetWidth,H=c.offsetHeight||140;
  c.width=W*dpr;c.height=H*dpr;
  var ctx=c.getContext('2d');ctx.scale(dpr,dpr);
  var vals=curve.map(function(p){return p.e;}),dates=curve.map(function(p){return p.d;}),n=vals.length;
  var mn=Math.min.apply(null,vals),mx=Math.max.apply(null,vals);
  var pad={t:12,r:8,b:24,l:44},cw=W-pad.l-pad.r,ch=H-pad.t-pad.b;
  function xp(i){return pad.l+i/(n-1)*cw;}
  function yp(v){return pad.t+ch-(v-mn)/((mx-mn)||1)*ch;}
  ctx.strokeStyle='#30363d';ctx.lineWidth=1;ctx.setLineDash([3,3]);
  ctx.beginPath();ctx.moveTo(pad.l,yp(100));ctx.lineTo(pad.l+cw,yp(100));ctx.stroke();
  ctx.setLineDash([]);
  var isUp=vals[n-1]>=100;
  var grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ch);
  grad.addColorStop(0,isUp?'rgba(0,200,83,.3)':'rgba(255,82,82,.3)');
  grad.addColorStop(1,'rgba(0,0,0,0)');
  ctx.beginPath();ctx.moveTo(xp(0),yp(vals[0]));
  for(var i=1;i<n;i++)ctx.lineTo(xp(i),yp(vals[i]));
  ctx.lineTo(xp(n-1),pad.t+ch);ctx.lineTo(xp(0),pad.t+ch);ctx.closePath();
  ctx.fillStyle=grad;ctx.fill();
  ctx.beginPath();ctx.lineWidth=2;ctx.strokeStyle=isUp?'#00c853':'#ff5252';
  ctx.moveTo(xp(0),yp(vals[0]));
  for(var j=1;j<n;j++)ctx.lineTo(xp(j),yp(vals[j]));
  ctx.stroke();
  ctx.fillStyle='#8b949e';ctx.font='10px sans-serif';ctx.textAlign='right';
  ctx.fillText(mn.toFixed(1),pad.l-3,yp(mn)+3);ctx.fillText(mx.toFixed(1),pad.l-3,yp(mx)+3);
  ctx.textAlign='center';ctx.font='9px sans-serif';
  ctx.fillText(dates[0],xp(0),H-6);ctx.fillText(dates[n-1],xp(n-1),H-6);
  var lx=xp(n-1),ly=yp(vals[n-1]);
  ctx.beginPath();ctx.arc(lx,ly,4,0,Math.PI*2);ctx.fillStyle=isUp?'#00c853':'#ff5252';ctx.fill();
  ctx.fillStyle='#fff';ctx.font='bold 10px sans-serif';ctx.textAlign='left';
  ctx.fillText(vals[n-1].toFixed(1),lx+6,ly+4);
}
function drawRollingWR(rwr){
  var c=document.getElementById('rwrChart');if(!c)return;
  var dpr=window.devicePixelRatio||1,W=c.offsetWidth,H=c.offsetHeight||140;
  c.width=W*dpr;c.height=H*dpr;
  var ctx=c.getContext('2d');ctx.scale(dpr,dpr);
  var vals=rwr.map(function(p){return p.wr;}),dates=rwr.map(function(p){return p.d;}),n=vals.length;
  var pad={t:12,r:8,b:24,l:36},cw=W-pad.l-pad.r,ch=H-pad.t-pad.b;
  function xp(i){return pad.l+i/(n-1)*cw;}
  function yp(v){return pad.t+ch-(v/100)*ch;}
  [[50,'#30363d'],[60,'#1f3a1f']].forEach(function(pair){
    ctx.strokeStyle=pair[1];ctx.lineWidth=1;ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(pad.l,yp(pair[0]));ctx.lineTo(pad.l+cw,yp(pair[0]));ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle='#484f58';ctx.font='9px sans-serif';ctx.textAlign='right';
    ctx.fillText(pair[0]+'%',pad.l-2,yp(pair[0])+3);
  });
  var grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ch);
  grad.addColorStop(0,'rgba(88,166,255,.25)');grad.addColorStop(1,'rgba(0,0,0,0)');
  ctx.beginPath();ctx.moveTo(xp(0),yp(vals[0]));
  for(var i=1;i<n;i++)ctx.lineTo(xp(i),yp(vals[i]));
  ctx.lineTo(xp(n-1),pad.t+ch);ctx.lineTo(xp(0),pad.t+ch);ctx.closePath();
  ctx.fillStyle=grad;ctx.fill();
  ctx.beginPath();ctx.lineWidth=2;ctx.strokeStyle='#58a6ff';
  ctx.moveTo(xp(0),yp(vals[0]));
  for(var j=1;j<n;j++)ctx.lineTo(xp(j),yp(vals[j]));
  ctx.stroke();
  ctx.textAlign='center';ctx.font='9px sans-serif';ctx.fillStyle='#8b949e';
  ctx.fillText(dates[0],xp(0),H-6);ctx.fillText(dates[n-1],xp(n-1),H-6);
  var lx=xp(n-1),ly=yp(vals[n-1]);
  ctx.beginPath();ctx.arc(lx,ly,4,0,Math.PI*2);ctx.fillStyle='#58a6ff';ctx.fill();
  ctx.fillStyle='#fff';ctx.font='bold 10px sans-serif';ctx.textAlign='left';
  ctx.fillText(vals[n-1]+'%',lx+6,ly+4);
}
function openSymDrill(sym){
  var trades=(PERF.by_symbol||{})[sym];if(!trades||!trades.length)return;
  var wins=trades.filter(function(t){return t.win;}).length;
  var wr=Math.round(wins/trades.length*100);
  var avgRet=trades.reduce(function(s,t){return s+t.ret;},0)/trades.length;
  var wrColor=wr>=60?'#00c853':wr>=45?'#ffd740':'#ff5252';
  var arColor=avgRet>0?'#00c853':avgRet<0?'#ff5252':'#aaa';
  var lc={'ورود قوی':'#00c853','ورود':'#69f0ae'};
  var rows=trades.slice().reverse().map(function(t){
    var rc=t.ret>0?'#00c853':t.ret<0?'#ff5252':'#aaa';
    return '<tr><td>'+e(t.label_fa)+'</td><td>'+e(t.grade)+'</td><td>'+e(t.date.slice(0,10))+'</td>'
      +'<td>'+e(t.entry)+'</td><td>'+e(t.exit)+'</td>'
      +'<td style="color:'+rc+';font-weight:600">'+(t.ret>0?'+':'')+t.ret+'%</td></tr>';
  }).join('');
  var eq=100,symCurve=trades.map(function(t){eq*=(1+t.ret/100);return {d:t.date.slice(0,10),e:Math.round(eq*100)/100};});
  document.getElementById('dc').innerHTML=
    '<div style="margin-bottom:12px">'
    +'<div style="font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:6px">📌 '+e(sym)+'</div>'
    +'<div style="display:flex;gap:18px;font-size:12px;margin-bottom:14px">'
    +'<span>معاملات: <b style="color:#c9d1d9">'+trades.length+'</b></span>'
    +'<span>موفق: <b style="color:'+wrColor+'">'+wr+'%</b></span>'
    +'<span>میانگین: <b style="color:'+arColor+'">'+(avgRet>0?'+':'')+avgRet.toFixed(2)+'%</b></span></div>'
    +(symCurve.length>1?'<canvas id="symEq" style="width:100%;height:100px;display:block;margin-bottom:12px"></canvas>':'')
    +'<table class="recent-table"><thead><tr><th>وضعیت</th><th>رتبه</th><th>تاریخ</th><th>ورود</th><th>خروج</th><th>بازده</th></tr></thead>'
    +'<tbody>'+rows+'</tbody></table></div>';
  document.getElementById('ov').classList.add('open');
  document.body.style.overflow='hidden';
  if(symCurve.length>1)setTimeout(function(){
    drawEquity([{d:'شروع',e:100}].concat(symCurve),'symEq');
  },0);
}
document.getElementById('a3').textContent='↓';
window.addEventListener('resize',function(){drawDist();drawScatter();drawHeat();});
render();
