"""Embedded interface for the local Parison Workbench."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Parison Workbench</title>
<style>
:root{font:15px/1.5 system-ui,sans-serif;color:#172033;background:#f4f6f9}
*{box-sizing:border-box}body{margin:0}.shell{min-height:100vh;display:grid;grid-template-columns:15rem 1fr}
aside{background:#101828;color:#d0d5dd;padding:1.75rem 1rem;display:flex;flex-direction:column;gap:2rem}
.brand{padding:0 .75rem}.brand strong{display:block;color:#fff;font-size:1.15rem}.brand span{font-size:.8rem;color:#98a2b3}
nav{display:grid;gap:.35rem}.nav-item{display:flex;justify-content:space-between;align-items:center;padding:.65rem .75rem;border-radius:.45rem;color:#d0d5dd;text-decoration:none}
.nav-item.active{background:#344054;color:#fff;font-weight:650}.nav-item[aria-disabled=true]{color:#667085}.soon{font-size:.68rem;text-transform:uppercase;letter-spacing:.05em}
.local{margin-top:auto;padding:.75rem;border:1px solid #344054;border-radius:.5rem;font-size:.8rem}.local strong{display:block;color:#ecfdf3}.dot{display:inline-block;width:.5rem;height:.5rem;border-radius:50%;background:#32d583;margin-right:.4rem}
.workspace{min-width:0}.topbar{height:4.5rem;background:#fff;border-bottom:1px solid #e4e7ec;display:flex;align-items:center;justify-content:space-between;padding:0 2rem}
.topbar p{margin:0;color:#667085}.session{font-size:.8rem;color:#027a48;background:#ecfdf3;border:1px solid #abefc6;border-radius:999px;padding:.25rem .65rem}
main{max-width:70rem;margin:0 auto;padding:3rem 2rem 5rem}.eyebrow{margin:0 0 .4rem;color:#475467;font-size:.8rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
h1{font-size:2.25rem;line-height:1.15;margin:.2rem 0 .75rem;letter-spacing:-.03em}h2{margin:0 0 .35rem}.lede{max-width:46rem;color:#667085;font-size:1.05rem;margin:0 0 2rem}
.card{background:#fff;border:1px solid #d0d5dd;border-radius:.75rem;box-shadow:0 1px 2px #1018280d}.open-card{padding:1.4rem}
form{display:grid;grid-template-columns:1fr auto;gap:.75rem;align-items:end}label{display:grid;gap:.4rem;font-weight:650}label span{font-weight:400;color:#667085;font-size:.82rem}
input,button{font:inherit}input{width:100%;padding:.72rem .8rem;border:1px solid #98a2b3;border-radius:.45rem;background:#fff;color:#101828}input:focus{outline:3px solid #84adff55;border-color:#175cd3}
button{border:1px solid #175cd3;border-radius:.45rem;padding:.72rem 1rem;background:#175cd3;color:#fff;font-weight:650;cursor:pointer}button:hover{background:#1849a9}button:focus-visible{outline:3px solid #84adff}
.status{margin:1rem 0 0;color:#475467}.empty{margin-top:1.5rem;padding:3.5rem 2rem;text-align:center}.mark{width:3rem;height:3rem;margin:0 auto 1rem;border-radius:50%;display:grid;place-items:center;background:#eef4ff;color:#175cd3;font-size:1.25rem;font-weight:800}
.empty p{max-width:34rem;margin:.3rem auto;color:#667085}.evidence{margin-top:1.5rem;overflow:hidden}.evidence header{padding:1.25rem 1.4rem;border-bottom:1px solid #e4e7ec;display:flex;justify-content:space-between;align-items:center}
.outcome{font-size:.78rem;font-weight:750;border-radius:999px;padding:.25rem .6rem}.outcome.pass{color:#027a48;background:#ecfdf3}.outcome.other{color:#b42318;background:#fef3f2}
table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd3da;padding:.65rem .85rem;text-align:left;vertical-align:top;border-left:0;border-right:0}th{width:34%;background:#f8fafc;color:#344054}code{overflow-wrap:anywhere;color:#344054}
.boundary{margin-top:1.5rem;padding:1rem 1.2rem;border-left:3px solid #84adff;background:#eef4ff;color:#344054}.boundary strong{display:block;margin-bottom:.2rem}
@media(max-width:760px){.shell{grid-template-columns:1fr}aside{padding:1rem;gap:1rem}nav{grid-template-columns:repeat(3,1fr)}.nav-item{padding:.5rem;font-size:.8rem}.soon{display:none}.local{display:none}.topbar{padding:0 1rem}main{padding:2rem 1rem}form{grid-template-columns:1fr}}
</style>
</head>
<body><div class="shell">
<aside><div class="brand"><strong>Parison</strong><span>Verification workbench</span></div>
<nav aria-label="Workbench activities">
<span class="nav-item" aria-disabled="true">Plans <span class="soon">Next</span></span>
<span class="nav-item" aria-disabled="true">Run <span class="soon">Planned</span></span>
<span class="nav-item active" aria-current="page">Results</span>
<span class="nav-item" aria-disabled="true">History <span class="soon">Planned</span></span>
<span class="nav-item" aria-disabled="true">Investigate <span class="soon">Planned</span></span>
<span class="nav-item" aria-disabled="true">Compare <span class="soon">Planned</span></span>
</nav>
<div class="local"><strong><span class="dot"></span>Local only</strong>No network, credentials, or remote execution.</div></aside>
<div class="workspace"><header class="topbar"><p>Current workspace</p><span id="session" class="session" role="status">Connecting...</span></header>
<main><p class="eyebrow">Verified evidence</p><h1 id="heading">Results</h1>
<p class="lede">Open a published Parison bundle to verify its integrity and inspect a summary-safe result.</p>
<section class="card open-card"><form id="open"><label for="bundle">Bundle folder <span>Path relative to this workspace, for example <code>examples/output</code></span><input id="bundle" required placeholder="runs/example" autocomplete="off"></label><button>Verify and open</button></form><p id="status" class="status" role="status">Ready for a local bundle.</p></section>
<section id="empty" class="card empty"><div class="mark">P</div><h2>No result open</h2><p>Choose the bundle folder—not an individual <code>result.json</code> file. Parison verifies every manifest-covered artifact before showing evidence.</p></section>
<section id="result" class="card evidence" hidden><header><div><p class="eyebrow">Verification result</p><h2>Summary-safe evidence</h2></div><span id="outcome" class="outcome"></span></header><table><tbody id="evidence"></tbody></table></section>
<aside class="boundary"><strong>What PASS means</strong>Agreement under the displayed policy—not extraction truth, approval, or cutover authorization. This view excludes source paths, keys, values, and discrepancy samples.</aside>
</main></div></div>
<script>
const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);
const session=document.getElementById('session'),status=document.getElementById('status'),body=document.getElementById('evidence'),heading=document.getElementById('heading'),result=document.getElementById('result'),empty=document.getElementById('empty'),outcome=document.getElementById('outcome');
const post=(path,data)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Parison-Session':token},body:JSON.stringify(data)});
post('/api/session',{}).then(r=>r.ok?r.json():Promise.reject()).then(()=>session.textContent='Local workspace ready').catch(()=>{session.textContent='Session rejected';session.style.color='#b42318'});
document.getElementById('open').addEventListener('submit',async event=>{event.preventDefault();status.textContent='Verifying bundle...';body.replaceChildren();
const response=await post('/api/evidence',{bundle:document.getElementById('bundle').value});if(!response.ok){status.textContent='Bundle could not be verified. Select the bundle folder within this workspace.';result.hidden=true;empty.hidden=false;return}
const evidence=await response.json();const name=evidence.outcome||'Result';heading.textContent=name;outcome.textContent=name;outcome.className='outcome '+(name==='PASS'?'pass':'other');
const rows=(value,prefix='')=>{if(value&&typeof value==='object'&&!Array.isArray(value)){Object.keys(value).sort().forEach(key=>rows(value[key],prefix?prefix+'.'+key:key));return}const row=document.createElement('tr'),label=document.createElement('th'),cell=document.createElement('td'),code=document.createElement('code');label.scope='row';label.textContent=prefix;code.textContent=Array.isArray(value)?value.join(', '):JSON.stringify(value);cell.append(code);row.append(label,cell);body.append(row)};
rows(evidence);empty.hidden=true;result.hidden=false;status.textContent='Verified bundle integrity. Showing summary-safe evidence.'});
</script></body></html>""".encode()
