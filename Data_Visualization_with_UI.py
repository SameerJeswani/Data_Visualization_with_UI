import os
import json
import webbrowser
import tempfile
import pandas as pd
import numpy as np


# Helper — process dataframe & return data_json

def process_csv(df, fname):
    # Clean
    df.drop_duplicates(inplace=True)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    for col in df.select_dtypes(include="number").columns:
        df[col] = df[col].fillna(df[col].median())
    for col in df.select_dtypes(include="object").columns:
        mode_val = df[col].mode()
        if not mode_val.empty:
            df[col] = df[col].fillna(mode_val[0])

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()

    # NumPy stats
    numpy_stats = []
    for col in num_cols:
        values = df[col].dropna().values
        numpy_stats.append({
            "col":  col,
            "mean": round(float(np.mean(values)), 2),
            "std":  round(float(np.std(values)), 2),
            "min":  round(float(np.min(values)), 2),
            "max":  round(float(np.max(values)), 2),
        })

    # Histogram
    hist_data = {}
    if num_cols:
        col  = num_cols[0]
        vals = df[col].dropna()
        counts, edges = np.histogram(vals, bins=20)
        hist_data = {
            "col":    col,
            "labels": [round(float(e), 2) for e in edges[:-1]],
            "counts": counts.tolist(),
            "mean":   round(float(vals.mean()), 2),
            "median": round(float(vals.median()), 2),
        }

    # Pie chart
    pie_data = {}
    if cat_cols:
        col = cat_cols[0]
        vc  = df[col].value_counts().head(6)
        pie_data = {"title": f"Pie Chart — {col}", "labels": vc.index.tolist(), "values": vc.values.tolist()}
    elif num_cols:
        means = df[num_cols[:6]].mean()
        means = means[means > 0]
        if not means.empty:
            pie_data = {"title": "Pie Chart — Column Mean Share",
                        "labels": means.index.tolist(),
                        "values": [round(v, 2) for v in means.values.tolist()]}

    # Correlation heatmap
    corr_data = {}
    if len(num_cols) >= 2:
        corr = df[num_cols[:6]].corr().round(2)
        corr_data = {"labels": corr.columns.tolist(), "matrix": corr.values.tolist()}

    return json.dumps({
        "fname":       fname,
        "rows":        df.shape[0],
        "cols":        df.shape[1],
        "nulls":       int(df.isnull().sum().sum()),
        "dups":        0,
        "numpy_stats": numpy_stats,
        "hist":        hist_data,
        "pie":         pie_data,
        "corr":        corr_data,
    })


# Build HTML — Upload Page + Dashboard Page

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DataLens</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@300;400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0d0f14;--surface:#161a22;--surface2:#1e2330;
  --border:#2a3040;--accent:#4fffb0;--blue:#6b9fff;
  --red:#ff6b6b;--text:#e8edf5;--muted:#7a8499;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;min-height:100vh;}

/* NAV */
nav{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:13px 28px;display:flex;align-items:center;gap:12px;
}
.logo{font-family:'IBM Plex Mono',monospace;font-size:1.05rem;font-weight:600;color:var(--accent);}
.logo span{color:var(--text);}
.nbadge{
  font-family:'IBM Plex Mono',monospace;font-size:0.62rem;
  background:rgba(79,255,176,0.1);color:var(--accent);
  border:1px solid rgba(79,255,176,0.3);padding:3px 9px;border-radius:4px;
}
.nfile{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:0.68rem;color:var(--muted);}

/* ── UPLOAD PAGE */
#uploadPage{
  display:flex;align-items:center;justify-content:center;
  min-height:calc(100vh - 53px);padding:40px 20px;
}
.upload-box{
  background:var(--surface);border:1px solid var(--border);
  border-radius:16px;padding:48px 56px;text-align:center;
  max-width:480px;width:100%;
}
.upload-box h2{font-size:1.3rem;font-weight:600;margin-bottom:8px;}
.upload-box p{font-size:0.82rem;color:var(--muted);margin-bottom:32px;line-height:1.6;}

/* Drop zone */
.drop-zone{
  border:2px dashed var(--border);border-radius:12px;
  padding:36px 20px;cursor:pointer;transition:all .2s;
  margin-bottom:20px;position:relative;
}
.drop-zone:hover,.drop-zone.drag{border-color:var(--accent);background:rgba(79,255,176,0.04);}
.drop-zone input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;}
.dz-icon{font-size:2.2rem;margin-bottom:10px;}
.dz-text{font-size:0.82rem;color:var(--muted);line-height:1.6;}
.dz-text strong{color:var(--accent);}

/* File chip */
#fileChip{
  display:none;align-items:center;gap:10px;
  background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;padding:10px 14px;margin-bottom:20px;text-align:left;
}
#fileChip .fc-name{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--accent);word-break:break-all;}
#fileChip .fc-size{font-size:0.7rem;color:var(--muted);margin-top:2px;}

/* Run button */
#runBtn{
  width:100%;padding:13px;border:none;border-radius:10px;
  background:var(--accent);color:#0d0f14;
  font-family:'DM Sans',sans-serif;font-size:0.95rem;font-weight:600;
  cursor:pointer;transition:opacity .2s;
  display:none;
}
#runBtn:hover{opacity:.88;}
#runBtn:disabled{opacity:.4;cursor:not-allowed;}

#errMsg{color:var(--red);font-size:0.78rem;margin-top:12px;display:none;}

/* ── DASHBOARD PAGE */
#dashPage{display:none;}

.main{padding:20px 24px 24px;}

.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px;}
.mcard{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;}
.mcard .mval{font-family:'IBM Plex Mono',monospace;font-size:1.4rem;font-weight:600;color:var(--accent);}
.mcard .mlbl{font-size:0.68rem;color:var(--muted);margin-top:4px;}

.charts{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}
.ccard{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:15px;}
.ctitle{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;font-weight:600;color:var(--muted);margin-bottom:10px;}
.csub{font-size:0.62rem;color:var(--muted);margin-top:7px;opacity:.75;}

/* Back button */
.back-btn{
  background:none;border:1px solid var(--border);border-radius:8px;
  color:var(--muted);font-size:0.75rem;padding:5px 14px;cursor:pointer;
  margin-left:auto;font-family:'IBM Plex Mono',monospace;transition:all .2s;
}
.back-btn:hover{border-color:var(--accent);color:var(--accent);}

::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="logo">Data<span>Lens</span></div>
  <div class="nbadge">pandas &middot; numpy</div>
  <div class="nfile" id="nf"></div>
  <button class="back-btn" id="backBtn" style="display:none" onclick="goBack()">&#8592; Upload New</button>
</nav>

<!-- ── UPLOAD PAGE ── -->
<div id="uploadPage">
  <div class="upload-box">
    <h2>Upload your CSV</h2>
    <p>Select or drag & drop a <strong>.csv</strong> file to analyze it instantly in your browser.</p>

    <div class="drop-zone" id="dropZone">
      <input type="file" id="csvInput" accept=".csv">
      <div class="dz-icon">📂</div>
      <div class="dz-text"><strong>Choose CSV file</strong><br>or drag & drop here</div>
    </div>

    <div id="fileChip">
      <span style="font-size:1.2rem">📄</span>
      <div>
        <div class="fc-name" id="fcName"></div>
        <div class="fc-size" id="fcSize"></div>
      </div>
    </div>

    <button id="runBtn" onclick="runAnalysis()">▶ &nbsp; Run Analysis</button>
    <div id="errMsg">Only .csv files are supported.</div>
  </div>
</div>

<!-- ── DASHBOARD PAGE ── -->
<div id="dashPage">
  <div class="main">
    <div class="metrics" id="metrics"></div>
    <div class="charts">
      <div class="ccard">
        <div class="ctitle" id="ht">Histogram</div>
        <div style="position:relative;height:240px"><canvas id="hc"></canvas></div>
        <div class="csub" id="hs"></div>
      </div>
      <div class="ccard">
        <div class="ctitle" id="pt">Pie Chart</div>
        <div style="position:relative;height:240px"><canvas id="pc"></canvas></div>
      </div>
      <div class="ccard">
        <div class="ctitle">Correlation Heatmap</div>
        <div style="position:relative;height:240px"><canvas id="cc"></canvas></div>
        <div class="csub" id="cs"></div>
      </div>
    </div>
  </div>
</div>

<script>
const P = ['#4fffb0','#6b9fff','#ff6b6b','#f5c542','#c77dff','#ff9f1c'];
let currentFile = null;
let chartInstances = [];

// ── DRAG & DROP 
const dz = document.getElementById('dropZone');
dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('drag'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
dz.addEventListener('drop', e => {
  e.preventDefault(); dz.classList.remove('drag');
  const f = e.dataTransfer.files[0];
  if(f) setFile(f);
});
document.getElementById('csvInput').addEventListener('change', e => {
  if(e.target.files[0]) setFile(e.target.files[0]);
});

function setFile(file){
  document.getElementById('errMsg').style.display = 'none';
  if(!file.name.endsWith('.csv')){
    document.getElementById('errMsg').style.display = 'block';
    return;
  }
  currentFile = file;
  document.getElementById('fcName').textContent = file.name;
  document.getElementById('fcSize').textContent  = formatBytes(file.size);
  document.getElementById('fileChip').style.display = 'flex';
  document.getElementById('runBtn').style.display    = 'block';
}

function formatBytes(b){
  if(b < 1024) return b + ' B';
  if(b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(2) + ' MB';
}

// ── RUN ANALYSIS 
function runAnalysis(){
  if(!currentFile) return;
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.textContent = 'Analyzing…';

  const reader = new FileReader();
  reader.onload = e => {
    try {
      const D = parseCSVtoData(currentFile.name, e.target.result);
      renderDashboard(D);
      // Switch pages
      document.getElementById('uploadPage').style.display = 'none';
      document.getElementById('dashPage').style.display   = 'block';
      document.getElementById('nf').textContent           = currentFile.name;
      document.getElementById('backBtn').style.display    = 'block';
    } catch(err) {
      document.getElementById('errMsg').textContent = 'Error: ' + err.message;
      document.getElementById('errMsg').style.display = 'block';
    }
    btn.disabled = false;
    btn.textContent = '▶   Run Analysis';
  };
  reader.readAsText(currentFile);
}

// ── GO BACK 
function goBack(){
  document.getElementById('dashPage').style.display   = 'none';
  document.getElementById('uploadPage').style.display = 'flex';
  document.getElementById('nf').textContent           = '';
  document.getElementById('backBtn').style.display    = 'none';
  // Destroy old charts
  chartInstances.forEach(c => c.destroy());
  chartInstances = [];
  document.getElementById('metrics').innerHTML = '';
}

// ── CSV PARSER 
function parseCSVtoData(fname, text){
  const lines = text.trim().split(/\\r?\\n/);
  if(lines.length < 2) throw new Error('CSV has no data rows.');

  // Parse header
  const headers = splitCSVLine(lines[0]);
  const rows = [];
  for(let i = 1; i < lines.length; i++){
    const vals = splitCSVLine(lines[i]);
    if(vals.length === 0) continue;
    const row = {};
    headers.forEach((h, idx) => row[h] = vals[idx] !== undefined ? vals[idx] : '');
    rows.push(row);
  }

  // Detect numeric columns
  const numCols = [], catCols = [];
  headers.forEach(h => {
    const sample = rows.slice(0,100).map(r=>r[h]).filter(v=>v!=='');
    const isNum  = sample.length > 0 && sample.every(v => !isNaN(parseFloat(v)) && isFinite(v));
    if(isNum) numCols.push(h); else catCols.push(h);
  });

  // Convert numeric
  rows.forEach(row => {
    numCols.forEach(h => { row[h] = row[h]==='' ? null : parseFloat(row[h]); });
  });

  // Clean: fill numeric nulls with median, deduplicate
  const cleanRows = dedup(rows, headers);
  numCols.forEach(h => {
    const vals = cleanRows.map(r=>r[h]).filter(v=>v!==null);
    const med  = median(vals);
    cleanRows.forEach(r => { if(r[h]===null) r[h]=med; });
  });

  // NumPy stats
  const numpy_stats = numCols.map(h => {
    const vals = cleanRows.map(r=>r[h]).filter(v=>v!==null);
    return { col:h, mean:round2(mean(vals)), std:round2(std(vals)), min:round2(Math.min(...vals)), max:round2(Math.max(...vals)) };
  });

  // Histogram (first numeric)
  let hist_data = {};
  if(numCols.length > 0){
    const h   = numCols[0];
    const vs  = cleanRows.map(r=>r[h]).filter(v=>v!==null).sort((a,b)=>a-b);
    const mn  = vs[0], mx = vs[vs.length-1];
    const bin = (mx - mn) / 20 || 1;
    const counts = Array(20).fill(0);
    const labels = [];
    for(let i=0;i<20;i++) labels.push(round2(mn + i*bin));
    vs.forEach(v => {
      let idx = Math.floor((v-mn)/bin);
      if(idx>=20) idx=19;
      counts[idx]++;
    });
    hist_data = { col:h, labels, counts, mean:round2(mean(vs)), median:round2(median(vs)) };
  }

  // Pie chart
  let pie_data = {};
  if(catCols.length > 0){
    const h  = catCols[0];
    const vc = {};
    cleanRows.forEach(r => { const v=r[h]||''; vc[v]=(vc[v]||0)+1; });
    const sorted = Object.entries(vc).sort((a,b)=>b[1]-a[1]).slice(0,6);
    pie_data = { title:`Pie Chart — ${h}`, labels:sorted.map(x=>x[0]), values:sorted.map(x=>x[1]) };
  } else if(numCols.length > 0){
    const cols = numCols.slice(0,6);
    const means = cols.map(h => ({ h, v: round2(mean(cleanRows.map(r=>r[h]).filter(v=>v!==null))) })).filter(x=>x.v>0);
    if(means.length > 0)
      pie_data = { title:'Pie Chart — Column Mean Share', labels:means.map(x=>x.h), values:means.map(x=>x.v) };
  }

  // Correlation heatmap
  let corr_data = {};
  if(numCols.length >= 2){
    const cols = numCols.slice(0,6);
    const matrix = cols.map(a => cols.map(b => {
      const va = cleanRows.map(r=>r[a]), vb = cleanRows.map(r=>r[b]);
      return round2(pearson(va, vb));
    }));
    corr_data = { labels: cols, matrix };
  }

  return { fname, rows:cleanRows.length, cols:headers.length, nulls:0, dups:0, numpy_stats, hist:hist_data, pie:pie_data, corr:corr_data };
}

// ── MATH HELPERS 
function mean(arr){ return arr.reduce((a,b)=>a+b,0)/arr.length; }
function median(arr){ const s=[...arr].sort((a,b)=>a-b); const m=Math.floor(s.length/2); return s.length%2?s[m]:(s[m-1]+s[m])/2; }
function std(arr){ const m=mean(arr); return Math.sqrt(arr.reduce((a,b)=>a+(b-m)**2,0)/arr.length); }
function round2(v){ return Math.round(v*100)/100; }
function dedup(rows, headers){
  const seen=new Set();
  return rows.filter(r=>{ const k=headers.map(h=>r[h]).join('|'); if(seen.has(k))return false; seen.add(k);return true; });
}
function pearson(a, b){
  const n=a.length, ma=mean(a), mb=mean(b);
  const num=a.reduce((s,v,i)=>s+(v-ma)*(b[i]-mb),0);
  const den=Math.sqrt(a.reduce((s,v)=>s+(v-ma)**2,0)*b.reduce((s,v)=>s+(v-mb)**2,0));
  return den===0?0:num/den;
}
function splitCSVLine(line){
  const res=[]; let cur='', inQ=false;
  for(let i=0;i<line.length;i++){
    if(line[i]==='"'){ inQ=!inQ; continue; }
    if(line[i]===','&&!inQ){ res.push(cur.trim()); cur=''; }
    else cur+=line[i];
  }
  res.push(cur.trim());
  return res;
}

// ── RENDER DASHBOARD 
function renderDashboard(D){
  // Metric cards
  const mr = document.getElementById('metrics');
  mr.innerHTML = '';
  D.numpy_stats.slice(0,4).forEach(s => {
    mr.innerHTML += `<div class="mcard"><div class="mval">${s.mean.toLocaleString()}</div><div class="mlbl">Mean of ${s.col}</div></div>`;
  });
  for(let i=D.numpy_stats.length;i<4;i++)
    mr.innerHTML += `<div class="mcard"><div class="mval" style="color:var(--muted)">—</div><div class="mlbl">—</div></div>`;

  // Histogram
  if(D.hist && D.hist.col){
    document.getElementById('ht').textContent = 'Histogram — ' + D.hist.col;
    document.getElementById('hs').textContent = `Mean = ${D.hist.mean}  |  Median = ${D.hist.median}  |  bins = 20`;
    const c = new Chart(document.getElementById('hc'), {
      type:'bar',
      data:{
        labels: D.hist.labels.map(v => v>=1000?(v/1000).toFixed(0)+'k':v),
        datasets:[{data:D.hist.counts,backgroundColor:'#378ADD',borderWidth:0,borderRadius:2}]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{
          x:{ticks:{font:{size:9},color:'#7a8499',maxTicksLimit:8,autoSkip:true,maxRotation:40},grid:{color:'rgba(255,255,255,0.04)'}},
          y:{ticks:{font:{size:9},color:'#7a8499'},grid:{color:'rgba(255,255,255,0.04)'}}
        }
      }
    });
    chartInstances.push(c);
  }

  // Pie chart
  if(D.pie && D.pie.labels && D.pie.labels.length > 0){
    document.getElementById('pt').textContent = D.pie.title;
    const c = new Chart(document.getElementById('pc'), {
      type:'pie',
      data:{labels:D.pie.labels,datasets:[{data:D.pie.values,backgroundColor:P,borderWidth:2,borderColor:'#161a22'}]},
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{
          legend:{position:'bottom',labels:{color:'#7a8499',font:{size:9},boxWidth:10,padding:7}},
          tooltip:{callbacks:{label:c=>{const t=c.dataset.data.reduce((a,b)=>a+b,0);return c.label+': '+((c.raw/t)*100).toFixed(1)+'%';}}}
        }
      }
    });
    chartInstances.push(c);
  }

  // Correlation heatmap
  if(D.corr && D.corr.labels && D.corr.labels.length >= 2){
    const lb=D.corr.labels, mx=D.corr.matrix, n=lb.length;
    function cc(v){return v>=0.7?'#1D9E75':v>=0.3?'#63B3ED':v>=0?'#4A5568':v>=-0.3?'#744210':'#9B2C2C';}
    const ds=[];
    for(let i=0;i<n;i++) for(let j=0;j<n;j++)
      ds.push({data:[{x:j,y:i,v:mx[i][j]}],backgroundColor:cc(mx[i][j]),pointRadius:Math.min(26,190/n),pointStyle:'rect'});
    const c = new Chart(document.getElementById('cc'), {
      type:'scatter', data:{datasets:ds},
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>lb[c.raw.y]+' × '+lb[c.raw.x]+': r='+c.raw.v.toFixed(2)}}},
        scales:{
          x:{type:'linear',min:-0.5,max:n-0.5,ticks:{callback:v=>lb[v]||'',stepSize:1,font:{size:8},color:'#7a8499'},grid:{display:false}},
          y:{type:'linear',min:-0.5,max:n-0.5,reverse:true,ticks:{callback:v=>lb[v]||'',stepSize:1,font:{size:8},color:'#7a8499'},grid:{display:false}}
        }
      },
      plugins:[{afterDraw(ch){
        const cx=ch.ctx;
        ch.data.datasets.forEach(ds=>ds.data.forEach(pt=>{
          const xp=ch.scales.x.getPixelForValue(pt.x),yp=ch.scales.y.getPixelForValue(pt.y);
          cx.fillStyle='#fff';cx.font='500 9px IBM Plex Mono,monospace';
          cx.textAlign='center';cx.textBaseline='middle';
          cx.fillText(pt.v.toFixed(2),xp,yp);
        }));
      }}]
    });
    chartInstances.push(c);
    if(n===2) document.getElementById('cs').textContent = lb[0]+' ↔ '+lb[1]+': r = '+mx[0][1].toFixed(2);
  }
}
</script>
</body>
</html>
"""

# Launch the upload page in browser

with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(HTML)
    tmp = f.name

print("\nDataLens opening in browser...")
print("Upload your CSV file from the UI and click Run Analysis.")
webbrowser.open("file://" + tmp)
print("Done!")