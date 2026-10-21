"""Embedded interface for the local Parison Workbench."""

PLAN_CONTROLS_SCRIPT = r"""
let planRevision=0,controlBusy=false,pendingControl=false,controlsSource='',lastControls=null;
const policyControls=document.getElementById('policy-controls'),controlsStatus=document.getElementById('controls-status'),effectivePolicy=document.getElementById('effective-policy'),inputLocations=document.getElementById('plan-inputs');
function invalidatePlan(){planRevision++;downloadPlan.disabled=true;policySha.textContent='Revalidate to compute';effectivePolicy.textContent='Revalidate the current draft to review its effective policy.';}
function controlAvailability(disabled){policyControls.querySelectorAll('button,input,select').forEach(control=>control.disabled=disabled);}
function controlButton(text,action){const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=text;button.addEventListener('click',action);return button;}
async function editControl(path,operation,value,focusPath){
  if(controlBusy)return;
  const focusedPath=focusPath??document.activeElement?.dataset.path;
  const source=planSource.value;invalidatePlan();const revision=planRevision;
  controlBusy=true;pendingControl=false;controlAvailability(true);downloadPlan.disabled=true;validatePlan.disabled=true;
  controlsStatus.textContent='Applying field edit to the JSON draft...';
  try{
    const response=await post('/api/edit-plan',{source,path,operation,value});
    if(revision!==planRevision||source!==planSource.value)return;
    if(!response.ok)throw Error();
    const edited=await response.json();
    if(revision!==planRevision||source!==planSource.value)return;
    invalidatePlan();planSource.value=edited.source;renderPlanControls(edited.controls);
    planStatus.textContent='Draft changed. Validate changes before downloading.';
    controlsStatus.textContent='Field edit applied. The draft remains unapproved.';
    const target=Array.from(policyControls.querySelectorAll('[data-path]')).find(control=>control.dataset.path===focusedPath);
    if(target)target.focus();
  }catch(error){if(revision===planRevision&&lastControls)renderPlanControls(lastControls);controlsStatus.textContent='Edit was not applied. Enter a valid value, or edit the JSON source and refresh controls.';}
  finally{controlBusy=false;if(token){validatePlan.disabled=pendingControl;if(controlsSource===planSource.value)controlAvailability(false);}}
}
function renderPlanControls(root){
  pendingControl=false;
  lastControls=root;
  controlsSource=planSource.value;
  const expanded=new Set(Array.from(policyControls.querySelectorAll('details[open]')).map(item=>item.dataset.path));
  const initial=policyControls.childElementCount===0;
  policyControls.replaceChildren();
  function render(node){
    const field=document.createElement('div');field.className='policy-field';
    const name=node.path.length?String(node.path[node.path.length-1]):'Policy';
    const fullName=node.path.map(String).join(' / ');
    const heading=document.createElement('div');heading.className='control-heading';
    const title=document.createElement('span');title.textContent=name+(node.required?' (required)':'');heading.append(title);
    if(!node.present){
      field.classList.add('field-row');const note=document.createElement('span');note.className='control-note';note.textContent='Not set in source';
      const add=controlButton('Add '+name,()=>editControl(node.path,'set',node.initial));field.append(heading,note,add);return field;
    }
    if(node.children){
      const details=document.createElement('details');details.dataset.path=JSON.stringify(node.path);
      details.open=expanded.has(details.dataset.path)||(initial&&node.path.length===1&&name==='scope');
      const summary=document.createElement('summary');summary.textContent=name+(node.required?' (required)':'');details.append(summary);
      const contents=document.createElement('div');contents.className='control-children';
      if(node.description){const description=document.createElement('p');description.className='control-note';description.textContent=node.description;contents.append(description);}
      node.children.forEach(child=>contents.append(render(child)));
      if(node.kind==='array')contents.append(controlButton('Add item to '+name,()=>editControl([...node.path,node.children.length],'set',node.initial)));
      if(node.additional){
        const addRow=document.createElement('div');addRow.className='add-property';
        const key=document.createElement('input');key.type='text';key.setAttribute('aria-label','New property in '+fullName);key.placeholder='New property name';
        const add=controlButton('Add property',()=>{if(!key.value){key.focus();return}if(node.children.some(child=>child.path.at(-1)===key.value)){controlsStatus.textContent='That property already exists. Edit its current control.';return}editControl([...node.path,key.value],'set',node.additional_initial);});
        addRow.append(key,add);contents.append(addRow);
      }
      if(!node.required&&node.path.length)contents.append(controlButton('Remove '+name,()=>editControl(node.path,'remove',null)));
      details.append(contents);field.append(details);return field;
    }
    field.classList.add('field-row');
    const label=document.createElement('label');label.textContent=name+(node.required?' (required)':'');
    if(node.fixed){const fixed=document.createElement('code');fixed.textContent=node.value;field.append(label,fixed);if(!node.required)field.append(controlButton('Remove '+name,()=>editControl(node.path,'remove',null)));return field;}
    let input;
    const options=node.kind==='boolean'?['true','false']:node.choices;
    if(options.length){
      input=document.createElement('select');const blank=document.createElement('option');blank.value='';blank.textContent='Choose explicitly';blank.disabled=true;input.append(blank);
      options.forEach(value=>{const option=document.createElement('option');option.value=value;const decoded=JSON.parse(value);option.textContent=String(decoded);input.append(option);});input.value=options.includes(node.value)?node.value:'';
    }else{
      input=document.createElement('input');input.type='text';
      input.value=node.kind==='string'&&typeof JSON.parse(node.value)==='string'?JSON.parse(node.value):node.value;
      if(node.kind==='json')input.title='Enter a JSON string or number, keeping any quotes explicit.';
    }
    input.setAttribute('aria-label',fullName);input.dataset.path=JSON.stringify(node.path);
    if(options.length){input.addEventListener('change',()=>editControl(node.path,'set',input.value));}
    else{
      let dirty=false;
      input.addEventListener('input',()=>{dirty=true;pendingControl=true;invalidatePlan();validatePlan.disabled=true;planStatus.textContent='Finish editing the field to apply it to the JSON draft.';});
      input.addEventListener('blur',event=>{if(!dirty)return;dirty=false;editControl(node.path,'set',node.kind==='string'?JSON.stringify(input.value):input.value,event.relatedTarget?.dataset.path||'');});
      input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();input.blur();}});
    }
    label.append(input);field.append(label);
    if(node.description){const description=document.createElement('span');description.className='control-note';description.textContent=node.description;field.append(description);}
    if(!node.required)field.append(controlButton('Remove '+name,()=>editControl(node.path,'remove',null)));
    return field;
  }
  root.children.forEach(node=>policyControls.append(render(node)));
  controlAvailability(controlBusy);controlsStatus.textContent='Controls follow the released recipe schema. Unset fields stay omitted; review their effective values below.';
}
document.getElementById('refresh-controls').addEventListener('click',async()=>{
  const source=planSource.value,revision=planRevision;controlsStatus.textContent='Reading controls from the JSON draft...';
  try{const response=await post('/api/plan-controls',{source});if(!response.ok)throw Error();const data=await response.json();if(revision!==planRevision||source!==planSource.value)return;renderPlanControls(data.controls);}
  catch(error){if(revision===planRevision)controlsStatus.textContent='Controls could not be read. Use a JSON object with recipe_version 1 through 6, then refresh.';}
});
document.getElementById('plan-input-form').addEventListener('submit',async event=>{
  event.preventDefault();const baseline=document.getElementById('plan-baseline').value,candidate=document.getElementById('plan-candidate').value,status=document.getElementById('plan-input-status'),revision=planRevision;
  status.textContent='Checking the explicit local input locations...';
  try{
    const response=await post('/api/plan-inputs',{baseline,candidate});
    if(revision!==planRevision||baseline!==document.getElementById('plan-baseline').value||candidate!==document.getElementById('plan-candidate').value)return;
    if(!response.ok)throw Error();
    document.getElementById('baseline').value=baseline;document.getElementById('candidate').value=candidate;
    status.textContent='Input locations copied to Run. Choose a saved recipe there; preflight and execution require a separate submission.';
  }catch(error){status.textContent='Input locations were rejected. Choose existing files or supported partitions inside this workspace and keep structured selectors explicit.';}
});
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Parison Workbench</title>
<style>
:root{font:15px/1.5 system-ui,sans-serif;color:#172033;background:#f4f6f9;--canvas:#f4f6f9;--surface:#fff;--surface-subtle:#f8fafc;--ink:#172033;--ink-strong:#101828;--ink-muted:#475467;--ink-soft:#667085;--border:#d0d5dd;--border-strong:#98a2b3;--nav:#101828;--nav-hover:#1d2939;--nav-active:#344054;--nav-text:#d0d5dd;--nav-muted:#98a2b3;--action:#175cd3;--action-hover:#1849a9;--focus:#84adff;--success:#027a48;--success-surface:#ecfdf3;--error:#b42318;--error-surface:#fef3f2;--info-surface:#eef4ff;--space-1:.25rem;--space-2:.5rem;--space-3:.75rem;--space-4:1rem;--space-6:1.5rem;--space-8:2rem}
*{box-sizing:border-box}body{margin:0}.shell{min-height:100vh;display:grid;grid-template-columns:15rem 1fr}
aside{background:var(--nav);color:var(--nav-text);padding:1.75rem var(--space-4);display:flex;flex-direction:column;gap:var(--space-8)}
.brand{padding:0 var(--space-3)}.brand strong{display:block;color:#fff;font-size:1.15rem}.brand span{font-size:.8rem;color:var(--nav-muted)}
nav{display:grid;gap:.35rem}.nav-item{display:flex;justify-content:space-between;align-items:center;width:100%;padding:.65rem var(--space-3);border:0;border-radius:.45rem;background:transparent;color:var(--nav-text);text-align:left;font-weight:400}
.nav-item:hover{background:var(--nav-hover)}.nav-item.active{background:var(--nav-active);color:#fff;font-weight:650}.nav-item[aria-disabled=true]{color:var(--nav-muted);cursor:default}.nav-item[aria-disabled=true]:hover{background:transparent}
.soon{font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}
.local{margin-top:auto;padding:var(--space-3);border:1px solid var(--nav-active);border-radius:.5rem;font-size:.8rem}.local strong{display:block;color:var(--success-surface)}.dot{display:inline-block;width:.5rem;height:.5rem;border-radius:50%;background:#32d583;margin-right:.4rem}
.workspace{min-width:0}.topbar{height:4.5rem;background:var(--surface);border-bottom:1px solid #e4e7ec;display:flex;align-items:center;justify-content:space-between;padding:0 var(--space-8)}.session-actions{display:flex;align-items:center;gap:var(--space-3)}
.topbar p{margin:0;color:var(--ink-soft)}.session{font-size:.8rem;color:var(--success);background:var(--success-surface);border:1px solid #abefc6;border-radius:999px;padding:var(--space-1) .65rem}
main{max-width:70rem;margin:0 auto;padding:3rem var(--space-8) 5rem}
h1{font-size:2.25rem;line-height:1.15;margin:0 0 var(--space-3);letter-spacing:-.03em}h2{margin:0 0 .35rem}.lede{max-width:46rem;color:var(--ink-soft);font-size:1.05rem;margin:0 0 var(--space-8)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:.75rem;box-shadow:0 1px 2px #1018280d}.open-card{padding:1.4rem}#run-form{grid-template-columns:repeat(2,minmax(0,1fr))}#compare-form{grid-template-columns:1fr 1fr auto}#run-form button,#compare-form button{align-self:end}
form{display:grid;grid-template-columns:1fr auto;gap:var(--space-3);align-items:end}label{display:grid;gap:.4rem;font-weight:650}label span{font-weight:400;color:var(--ink-soft);font-size:.82rem}.actions{display:flex;flex-wrap:wrap;gap:var(--space-2)}
input,button,textarea{font:inherit}input{width:100%;padding:.72rem .8rem;border:1px solid var(--border-strong);border-radius:.45rem;background:var(--surface);color:var(--ink-strong)}input:focus,textarea:focus{outline:3px solid #84adff55;border-color:var(--action)}
button{border:1px solid var(--action);border-radius:.45rem;padding:.72rem var(--space-4);background:var(--action);color:#fff;font-weight:650;cursor:pointer}button:hover{background:var(--action-hover)}button:focus-visible{outline:3px solid var(--focus)}
button:disabled{cursor:wait;opacity:.6}
.secondary{background:var(--surface);color:var(--nav-active);border-color:var(--border-strong)}.secondary:hover{background:#f2f4f7}.clear{padding:.45rem .7rem}
.status{margin:var(--space-4) 0 0;color:var(--ink-muted)}.empty{margin-top:var(--space-6);padding:3.5rem var(--space-8);text-align:center}.mark{width:3rem;height:3rem;margin:0 auto var(--space-4);border-radius:50%;display:grid;place-items:center;background:var(--info-surface);color:var(--action);font-size:1.25rem;font-weight:800}
.empty p{max-width:34rem;margin:.3rem auto;color:var(--ink-soft)}.evidence{margin-top:var(--space-6);overflow:hidden}.evidence header{padding:1.25rem 1.4rem;border-bottom:1px solid #e4e7ec;display:flex;justify-content:space-between;align-items:center}
.outcome{font-size:.78rem;font-weight:750;border-radius:999px;padding:var(--space-1) .6rem}.outcome.pass{color:var(--success);background:var(--success-surface)}.outcome.other{color:var(--error);background:var(--error-surface)}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{border:1px solid #ccd3da;padding:.65rem .85rem;text-align:left;vertical-align:top;border-left:0;border-right:0;overflow-wrap:anywhere}tbody th{width:34%}th{background:var(--surface-subtle);color:var(--nav-active)}#history-view table{table-layout:fixed}#history-view th:nth-child(1){width:28%}#history-view th:nth-child(2),#history-view th:nth-child(3){width:14%}#history-view th:nth-child(4){width:44%}code{overflow-wrap:anywhere;color:var(--nav-active)}
.boundary{margin-top:var(--space-6);padding:var(--space-4) 1.2rem;border-left:3px solid var(--focus);background:var(--info-surface);color:var(--nav-active)}.boundary strong{display:block;margin-bottom:.2rem}
.editor{margin-top:var(--space-6);overflow:hidden}.editor header{padding:1.25rem 1.4rem;border-bottom:1px solid #e4e7ec;display:flex;justify-content:space-between;align-items:center}.meta{display:flex;flex-wrap:wrap;gap:var(--space-2);padding:var(--space-4) 1.4rem;background:var(--surface-subtle);border-bottom:1px solid #e4e7ec}.meta span{padding:.2rem .55rem;border:1px solid var(--border);border-radius:999px;background:var(--surface);font-size:.78rem}.digest{overflow-wrap:anywhere}.editor-body{padding:1.4rem}.editor-body label{display:block;margin-bottom:.45rem}.editor textarea{display:block;width:100%;min-height:25rem;resize:vertical;padding:.85rem;border:1px solid var(--border-strong);border-radius:.45rem;background:var(--ink-strong);color:#f2f4f7;font:13px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;tab-size:2}.editor-footer{display:flex;justify-content:space-between;gap:var(--space-4);align-items:center;margin-top:var(--space-4)}.editor-footer .status{margin:0;min-width:12rem}.commands{margin-top:var(--space-6);padding:1.2rem 1.4rem}.commands pre{overflow:auto;margin:var(--space-3) 0 0;padding:var(--space-4);border-radius:.45rem;background:var(--ink-strong);color:#f2f4f7}.commands code{color:inherit}
h3{margin:0 0 var(--space-2);font-size:1.1rem}.control-note{color:var(--ink-muted);font-size:.87rem;max-width:72ch}.policy-field{min-width:0;border-top:1px solid var(--border);padding:var(--space-3) 0}.control-children{padding:0 0 var(--space-3) var(--space-4)}summary{cursor:pointer;font-weight:650;padding:var(--space-3) 0;min-height:44px;overflow-wrap:anywhere}summary:focus-visible{outline:3px solid var(--focus)}.field-row{display:flex;flex-wrap:wrap;align-items:center;gap:var(--space-3)}.field-row label{flex:1;min-width:10rem;margin:0}.field-row input,.field-row select{margin-top:var(--space-2)}.field-row button{align-self:end}.control-heading{font-weight:650;flex:1;overflow-wrap:anywhere}.add-property{display:flex;gap:var(--space-2);margin:var(--space-4) 0}.add-property input{min-width:0}.add-property button{flex-shrink:0}.source-details{margin-top:var(--space-6);border-top:1px solid var(--border)}.source-details button{margin-top:var(--space-3)}.source-details pre,#plan-inputs pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;color:var(--ink-muted)}select{font:inherit;max-width:100%;width:100%;padding:.72rem .8rem;border:1px solid var(--border-strong);border-radius:.45rem;background:var(--surface);color:var(--ink-strong)}select:focus{outline:3px solid var(--focus)}#plan-input-form{grid-template-columns:1fr 1fr;margin-top:var(--space-4)}#plan-input-form button{grid-column:1/-1;justify-self:start}.policy-field code{word-break:break-word}.policy-field button{font-size:.85rem;min-height:44px}.editor-body>.editor-footer{border-top:1px solid var(--border);padding-top:var(--space-4)}
@media(max-width:760px){.shell{grid-template-columns:1fr}aside{padding:var(--space-4);gap:var(--space-4)}nav{grid-template-columns:repeat(3,1fr)}.nav-item{padding:var(--space-2);font-size:.8rem}.soon{display:none}.local{display:none}.topbar{padding:0 var(--space-4)}main{padding:var(--space-8) var(--space-4)}form,#run-form,#compare-form,#plan-input-form{grid-template-columns:1fr}.open-card .actions{display:grid;grid-template-columns:1fr 1fr}.editor header,.evidence header{align-items:flex-start;gap:var(--space-3)}.editor-footer{align-items:stretch;flex-direction:column}.editor-footer .status{min-width:0}.editor-footer .actions{display:grid;grid-template-columns:1fr}.editor-footer button{width:100%}.editor-body{padding:var(--space-4)}.empty{padding:var(--space-8) var(--space-4)}.field-row{align-items:stretch;flex-direction:column}.control-children{padding-left:var(--space-3)}.add-property{flex-wrap:wrap}.add-property input{flex:1;min-width:8rem}}
</style>
</head>
<body><div class="shell">
<aside><div class="brand"><strong>Parison</strong><span>Verification workbench</span></div>
<nav aria-label="Workbench activities">
<button class="nav-item" data-view="plans" type="button">Plans</button>
<button class="nav-item" data-view="run" type="button">Run</button>
<button class="nav-item active" data-view="results" type="button" aria-current="page">Results</button>
<button class="nav-item" data-view="history" type="button">History</button>
<button class="nav-item" data-view="investigate" type="button">Investigate</button>
<button class="nav-item" data-view="compare" type="button">Compare</button>
</nav>
<div class="local"><strong><span class="dot"></span>Local only</strong>No network, credentials, or remote execution.</div></aside>
<div class="workspace"><header class="topbar"><p>Current workspace</p><div class="session-actions"><span id="session" class="session" role="status">Connecting...</span><button id="shutdown" class="secondary clear" type="button">Stop workbench</button></div></header>
<main><section id="plans-view" hidden><h1>Plans</h1>
<p class="lede">Open a CLI-native recipe to review the exact JSON and its effective policy identity before execution.</p>
<section class="card open-card"><form id="open-plan"><label for="recipe">Recipe file <span>Choose a JSON file or enter its path relative to this workspace.</span><input id="recipe" required placeholder="recipes/example.json" autocomplete="off"></label><div class="actions"><button id="choose-recipe" class="secondary" type="button">Choose file...</button><button>Validate and open</button></div></form><p id="plan-open-status" class="status" role="status">Ready for a local recipe.</p></section>
<section id="plan-empty" class="card empty"><div class="mark">{ }</div><h2>No plan open</h2><p>Open an existing Parison recipe. The Python engine validates it before the editor displays its exact source.</p></section>
<section id="plan-editor" class="card editor" hidden><header><h2>Verification plan</h2><button id="clear-plan" class="secondary clear" type="button">Clear plan</button></header>
<div class="meta"><span>Unapproved draft</span><span id="recipe-version"></span><span id="comparison-mode"></span><span class="digest">Policy <code id="policy-sha"></code></span></div>
<div class="editor-body"><h3>Policy controls</h3><p id="controls-status" class="control-note" role="status"></p><div id="policy-controls"></div>
<details class="source-details"><summary>Recipe JSON source</summary><label for="plan-source">Exact recipe source</label><textarea id="plan-source" spellcheck="false"></textarea><button id="refresh-controls" class="secondary" type="button">Refresh controls from JSON</button></details>
<details class="source-details"><summary>Effective policy, including defaults</summary><p class="control-note">Computed by the Python loader for the last validated draft. Omitted source settings remain visible here.</p><pre id="effective-policy"></pre></details>
<div class="editor-footer"><p id="plan-status" class="status" role="status"></p><div class="actions"><button id="validate-plan" class="secondary" type="button">Validate changes</button><button id="download-plan" type="button">Download unapproved draft</button></div></div></div></section>
<section id="plan-inputs" class="card commands" hidden><h2>Local input locations</h2><p class="control-note">Select workspace-relative files or explicit structured locators. These locations stay separate from recipe JSON.</p>
<form id="plan-input-form"><label for="plan-baseline">Baseline location<input id="plan-baseline" required placeholder="inputs/baseline.csv" autocomplete="off"></label><label for="plan-candidate">Candidate location<input id="plan-candidate" required placeholder="inputs/candidate.csv" autocomplete="off"></label><button>Copy input locations to Run</button></form>
<details><summary>Structured locator examples</summary><pre>json:inputs/data.json#/rows
xml:inputs/data.xml#root/record
xlsx:inputs/data.xlsx#Sheet1!A1:B20
sqlite:inputs/data.db#records</pre></details><p id="plan-input-status" class="status" role="status">Choose both inputs explicitly. Run performs record preflight when you submit it.</p></section>
<section id="commands" class="card commands" hidden><h2>Equivalent CLI</h2><pre><code>parison validate-recipe plan.json
parison compare --recipe plan.json --baseline BASELINE --candidate CANDIDATE --output RUN_DIRECTORY</code></pre></section>
<aside class="boundary"><strong>Policy review required</strong>This editor never approves keys, tolerances, scope, exclusions, sensitivity, or repairs. A downloaded draft remains unapproved until you review and validate it.</aside></section>
<section id="run-view" hidden><h1>Run</h1><p class="lede">Preflight and execute one reviewed recipe against explicit local inputs. Every run publishes a new immutable bundle.</p>
<section class="card open-card"><form id="run-form"><label for="run-recipe">Recipe <input id="run-recipe" required placeholder="recipes/example.json" autocomplete="off"></label><label for="baseline">Baseline <input id="baseline" required placeholder="inputs/baseline.csv" autocomplete="off"></label><label for="candidate">Candidate <input id="candidate" required placeholder="inputs/candidate.csv" autocomplete="off"></label><label for="output">New output bundle <input id="output" required placeholder="runs/rehearsal-001" autocomplete="off"></label><div class="actions"><button id="start-run">Preflight and run</button><button id="cancel-run" class="secondary" type="button" disabled>Cancel run</button></div></form><p id="run-status" class="status" role="status">Ready. Execution begins only when you submit this form.</p></section>
<section id="run-result" class="card evidence" hidden><header><h2>Published result</h2><span id="run-outcome" class="outcome"></span></header><table><tbody id="run-evidence"></tbody></table></section>
<aside class="boundary"><strong>Execution is not approval</strong>A completed run records agreement or differences under the selected policy. It does not authorize a migration or cutover.</aside></section>
<section id="results-view"><h1 id="heading">Results</h1>
<p class="lede">Open a published Parison bundle to verify its integrity and inspect a summary-safe result.</p>
<section class="card open-card"><form id="open"><label for="bundle">Bundle folder <span>Choose a folder or enter its path relative to this workspace.</span><input id="bundle" required placeholder="runs/example" autocomplete="off"></label><div class="actions"><button id="choose" class="secondary" type="button">Choose folder...</button><button>Verify and open</button></div></form><p id="status" class="status" role="status">Ready for a local bundle.</p></section>
<section id="empty" class="card empty"><div class="mark">P</div><h2>No result open</h2><p>Choose the bundle folder—not an individual <code>result.json</code> file. Parison verifies every manifest-covered artifact before showing evidence.</p></section>
<section id="result" class="card evidence" hidden><header><h2>Summary-safe evidence</h2><div class="actions"><span id="outcome" class="outcome"></span><button id="clear" class="secondary clear" type="button">Clear result</button></div></header><table><tbody id="evidence"></tbody></table></section>
<aside class="boundary"><strong>What PASS means</strong>Agreement under the displayed policy—not extraction truth, approval, or cutover authorization. This view excludes source paths, keys, values, and discrepancy samples.</aside>
</section>
<section id="history-view" hidden><h1>History</h1><p class="lede">Browse immutable runs registered by this workspace. Catalog state is verified when history is loaded.</p><button id="refresh-history" type="button">Refresh history</button><p id="history-status" class="status" role="status">History has not been loaded.</p><section class="card evidence"><table><thead><tr><th>Bundle</th><th>Outcome</th><th>Integrity</th><th>Bundle SHA-256</th></tr></thead><tbody id="history-body"></tbody></table></section></section>
<section id="investigate-view" hidden><h1>Investigate</h1><p class="lede">Verify one run and group every discrepancy by summary-safe classification and policy reference.</p><section class="card open-card"><form id="investigate-form"><label for="investigate-bundle">Run bundle <input id="investigate-bundle" required placeholder="runs/rehearsal-001" autocomplete="off"></label><button>Analyze discrepancies</button></form><p id="investigate-status" class="status" role="status">Ready for a workspace-relative run bundle.</p></section><section id="investigate-result" class="card evidence" hidden><table><tbody id="investigate-body"></tbody></table></section><aside class="boundary"><strong>Summary-safe by default</strong>Groups contain counts, classifications and policy references—not source paths, keys, values or discrepancy samples.</aside></section>
<section id="compare-view" hidden><h1>Compare</h1><p class="lede">Compare two cataloged rehearsals only when they have the exact same policy identity.</p><section class="card open-card"><form id="compare-form"><label for="left-bundle">Earlier bundle <input id="left-bundle" required placeholder="runs/rehearsal-001" autocomplete="off"></label><label for="right-bundle">Later bundle <input id="right-bundle" required placeholder="runs/rehearsal-002" autocomplete="off"></label><button>Compare rehearsals</button></form><p id="compare-status" class="status" role="status">Ready for two workspace-relative bundle paths.</p></section><section id="compare-result" class="card evidence" hidden><table><tbody id="compare-body"></tbody></table></section></section>
</main></div></div>
<script>
let token=location.hash.slice(1);history.replaceState(null,'',location.pathname);
const session=document.getElementById('session'),status=document.getElementById('status'),body=document.getElementById('evidence'),heading=document.getElementById('heading'),result=document.getElementById('result'),empty=document.getElementById('empty'),outcome=document.getElementById('outcome');
const post=(path,data)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Parison-Session':token},body:JSON.stringify(data)});
post('/api/session',{}).then(r=>r.ok?r.json():Promise.reject()).then(()=>session.textContent='Local workspace ready').catch(()=>{session.textContent='Session rejected';session.style.color='#b42318'});
document.getElementById('shutdown').addEventListener('click',async event=>{event.currentTarget.disabled=true;session.textContent='Stopping...';try{const response=await post('/api/shutdown',{});if(!response.ok)throw Error();token='';planRevision++;document.querySelectorAll('button,input,textarea,select').forEach(control=>control.disabled=true);session.textContent='Workbench stopped';session.style.color='#475467'}catch(error){event.currentTarget.disabled=false;session.textContent='Could not stop workbench'} });
document.querySelectorAll('[data-view]').forEach(item=>item.addEventListener('click',()=>{document.querySelectorAll('[data-view]').forEach(other=>{other.classList.toggle('active',other===item);other.toggleAttribute('aria-current',other===item)});document.querySelectorAll('main>section[id$="-view"]').forEach(view=>view.hidden=view.id!==item.dataset.view+'-view')}));
const form=document.getElementById('open'),bundle=document.getElementById('bundle'),choose=document.getElementById('choose');
choose.addEventListener('click',async()=>{choose.disabled=true;status.textContent='Choose a bundle folder inside this workspace...';try{const response=await post('/api/choose-bundle',{});if(response.status===204){status.textContent='Folder selection cancelled.';return}if(!response.ok){status.textContent='Folder could not be selected. Choose a folder inside this workspace or enter its relative path.';return}bundle.value=(await response.json()).bundle;form.requestSubmit()}catch(error){status.textContent='Folder picker unavailable. Enter a workspace-relative path instead.'}finally{choose.disabled=false}});
form.addEventListener('submit',async event=>{event.preventDefault();status.textContent='Verifying bundle...';body.replaceChildren();
const response=await post('/api/evidence',{bundle:bundle.value});if(!response.ok){status.textContent='Bundle could not be verified. Select the bundle folder within this workspace.';result.hidden=true;empty.hidden=false;return}
const evidence=await response.json();const name=evidence.outcome||'Result';heading.textContent=name;outcome.textContent=name;outcome.className='outcome '+(name==='PASS'?'pass':'other');
const rows=(value,prefix='',target=body)=>{if(value&&typeof value==='object'&&!Array.isArray(value)){Object.keys(value).sort().forEach(key=>rows(value[key],prefix?prefix+'.'+key:key,target));return}const row=document.createElement('tr'),label=document.createElement('th'),cell=document.createElement('td'),code=document.createElement('code');label.scope='row';label.textContent=prefix;code.textContent=Array.isArray(value)?value.join(', '):JSON.stringify(value);cell.append(code);row.append(label,cell);target.append(row)};
rows(evidence);empty.hidden=true;result.hidden=false;status.textContent='Verified bundle integrity. Showing summary-safe evidence.'});
document.getElementById('clear').addEventListener('click',()=>{body.replaceChildren();result.hidden=true;empty.hidden=false;heading.textContent='Results';heading.style.color='';outcome.textContent='';form.reset();status.textContent='Result cleared. Ready for a local bundle.';bundle.focus()});
const planForm=document.getElementById('open-plan'),recipe=document.getElementById('recipe'),chooseRecipe=document.getElementById('choose-recipe'),planOpenStatus=document.getElementById('plan-open-status'),planEmpty=document.getElementById('plan-empty'),planEditor=document.getElementById('plan-editor'),commands=document.getElementById('commands'),planSource=document.getElementById('plan-source'),planStatus=document.getElementById('plan-status'),validatePlan=document.getElementById('validate-plan'),downloadPlan=document.getElementById('download-plan'),policySha=document.getElementById('policy-sha');
chooseRecipe.addEventListener('click',async()=>{chooseRecipe.disabled=true;planOpenStatus.textContent='Choose a recipe file inside this workspace...';try{const response=await post('/api/choose-recipe',{});if(response.status===204){planOpenStatus.textContent='File selection cancelled.';return}if(!response.ok){planOpenStatus.textContent='File could not be selected. Choose a file inside this workspace or enter its relative path.';return}recipe.value=(await response.json()).recipe;planForm.requestSubmit()}catch(error){planOpenStatus.textContent='File picker unavailable. Enter a workspace-relative path instead.'}finally{chooseRecipe.disabled=false}});
const showPolicy=plan=>{
  document.getElementById('recipe-version').textContent='Recipe v'+plan.recipe_version;document.getElementById('comparison-mode').textContent=plan.comparison_mode;policySha.textContent=plan.policy_sha256;effectivePolicy.textContent=plan.effective_policy;
  if(plan.controls){renderPlanControls(plan.controls);}else{policyControls.replaceChildren();controlsStatus.textContent=plan.controls_notice;document.querySelector('.source-details').open=true;}
};
planForm.addEventListener('submit',async event=>{
  event.preventDefault();const revision=++planRevision;planOpenStatus.textContent='Validating recipe...';
  try{
    const response=await post('/api/plan',{recipe:recipe.value});if(!response.ok)throw Error();const plan=await response.json();if(revision!==planRevision)return;
    planSource.value=plan.source;policyControls.replaceChildren();showPolicy(plan);downloadPlan.disabled=false;validatePlan.disabled=false;planStatus.textContent='Loaded plan passed Python validation. It remains an unapproved draft.';planEmpty.hidden=true;planEditor.hidden=false;commands.hidden=false;inputLocations.hidden=false;planOpenStatus.textContent='Validated recipe and computed its effective policy identity.';
  }catch(error){if(revision!==planRevision)return;planOpenStatus.textContent='Recipe could not be validated. Select a Parison recipe within this workspace.';planEditor.hidden=true;commands.hidden=true;inputLocations.hidden=true;planEmpty.hidden=false;}
});
planSource.addEventListener('input',()=>{pendingControl=false;invalidatePlan();validatePlan.disabled=controlBusy;controlAvailability(true);controlsStatus.textContent='JSON source changed. Refresh controls from JSON before using them.';try{const value=JSON.parse(planSource.value);if(!value||Array.isArray(value)||typeof value!=='object')throw Error('top level must be an object');planStatus.textContent='Valid JSON; authoritative Parison validation is required before download.'}catch(error){planStatus.textContent='Invalid JSON: '+error.message}});
validatePlan.addEventListener('click',async()=>{
  const source=planSource.value,revision=planRevision;validatePlan.disabled=true;planStatus.textContent='Validating changes with Parison...';
  try{
    const response=await post('/api/validate-plan',{source});
    if(planRevision!==revision||planSource.value!==source)return;
    if(!response.ok){downloadPlan.disabled=true;policySha.textContent='Validation failed';planStatus.textContent='Plan failed authoritative Parison validation. Review the fields or JSON source and try again.';return;}
    const plan=await response.json();if(planRevision!==revision||planSource.value!==source)return;
    showPolicy(plan);downloadPlan.disabled=false;planStatus.textContent='Changes passed Python validation. The downloadable draft remains unapproved.';
  }catch(error){if(planRevision===revision)planStatus.textContent='Plan could not be validated.';}
  finally{if(token)validatePlan.disabled=controlBusy||pendingControl;}
});
downloadPlan.addEventListener('click',()=>{const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([planSource.value.endsWith('\\n')?planSource.value:planSource.value+'\\n'],{type:'application/json'}));link.download='plan.json';link.click();URL.revokeObjectURL(link.href);planStatus.textContent='Downloaded validated, unapproved draft.'});
document.getElementById('clear-plan').addEventListener('click',()=>{planRevision++;pendingControl=false;lastControls=null;planForm.reset();planSource.value='';policyControls.replaceChildren();effectivePolicy.textContent='';policySha.textContent='';downloadPlan.disabled=true;planEditor.hidden=true;commands.hidden=true;inputLocations.hidden=true;document.getElementById('plan-input-form').reset();document.getElementById('plan-input-status').textContent='Choose both inputs explicitly. Run performs record preflight when you submit it.';planEmpty.hidden=false;planOpenStatus.textContent='Plan cleared. Ready for a local recipe.';recipe.focus()});
const runForm=document.getElementById('run-form'),runStatus=document.getElementById('run-status'),runResult=document.getElementById('run-result'),runEvidence=document.getElementById('run-evidence'),runOutcome=document.getElementById('run-outcome'),startRun=document.getElementById('start-run'),cancelRun=document.getElementById('cancel-run');let cancelRequested=false;
runForm.addEventListener('submit',async event=>{event.preventDefault();cancelRequested=false;startRun.disabled=true;cancelRun.disabled=false;runStatus.textContent='Preflighting inputs...';runEvidence.replaceChildren();const labels={preflight:'Preflighting inputs...',comparing:'Comparing records...',publishing:'Publishing immutable evidence...',verifying:'Verifying the published bundle...',cataloging:'Registering local history...',cancelling:'Stopping safely...'};const progress=setInterval(async()=>{try{const response=await post('/api/run-status',{});if(response.ok){const phase=(await response.json()).phase;if(labels[phase])runStatus.textContent=labels[phase]}}catch(error){}},500);try{const response=await post('/api/run',{recipe:document.getElementById('run-recipe').value,baseline:document.getElementById('baseline').value,candidate:document.getElementById('candidate').value,output:document.getElementById('output').value});if(!response.ok){runStatus.textContent=cancelRequested?'Run cancelled. No partial bundle was published.':response.status===409?'Another run is already active.':'Run was rejected. Check the plan, inputs, output path, and resource limits.';runResult.hidden=true;return}const executed=await response.json(),evidence=executed.evidence;runOutcome.textContent=evidence.outcome;runOutcome.className='outcome '+(evidence.outcome==='PASS'?'pass':'other');rows(evidence,'',runEvidence);runResult.hidden=false;runStatus.textContent='Run completed, published, verified, and registered in local history.'}catch(error){runStatus.textContent='Run connection failed.'}finally{clearInterval(progress);startRun.disabled=false;cancelRun.disabled=true}});
cancelRun.addEventListener('click',async()=>{cancelRun.disabled=true;cancelRequested=true;runStatus.textContent='Cancellation requested. Waiting for the current input operation to stop safely...';const response=await post('/api/cancel-run',{});if(!response.ok){cancelRequested=false;runStatus.textContent='The run completed before cancellation could be applied.'}});
const historyBody=document.getElementById('history-body'),historyStatus=document.getElementById('history-status');document.getElementById('refresh-history').addEventListener('click',async()=>{historyStatus.textContent='Verifying cataloged runs...';historyBody.replaceChildren();const response=await post('/api/history',{});if(!response.ok){historyStatus.textContent='History could not be verified.';return}const runs=await response.json();runs.forEach(run=>{const row=document.createElement('tr');[run.bundle,run.outcome,run.state,run.bundle_sha256].forEach(value=>{const cell=document.createElement('td');cell.textContent=value;row.append(cell)});historyBody.append(row)});historyStatus.textContent=runs.length?runs.length+' run(s) loaded.':'No Workbench runs are registered yet.'});
const investigateForm=document.getElementById('investigate-form'),investigateStatus=document.getElementById('investigate-status'),investigateResult=document.getElementById('investigate-result'),investigateBody=document.getElementById('investigate-body');investigateForm.addEventListener('submit',async event=>{event.preventDefault();investigateStatus.textContent='Verifying evidence and grouping discrepancies...';investigateBody.replaceChildren();const response=await post('/api/investigate',{bundle:document.getElementById('investigate-bundle').value});if(!response.ok){investigateStatus.textContent='Investigation rejected. Select a verified run bundle inside this workspace.';investigateResult.hidden=true;return}const analysis=await response.json(),nonzero=analysis.groups.filter(group=>group.count>0).length;rows(analysis,'',investigateBody);investigateResult.hidden=false;investigateStatus.textContent=nonzero?nonzero+' nonzero discrepancy group(s) loaded.':'The run has no discrepancies.'});
const compareForm=document.getElementById('compare-form'),compareStatus=document.getElementById('compare-status'),compareResult=document.getElementById('compare-result'),compareBody=document.getElementById('compare-body');compareForm.addEventListener('submit',async event=>{event.preventDefault();compareStatus.textContent='Verifying and comparing cataloged runs...';compareBody.replaceChildren();const response=await post('/api/compare',{left:document.getElementById('left-bundle').value,right:document.getElementById('right-bundle').value});if(!response.ok){compareStatus.textContent='Comparison rejected. Both runs must be current, cataloged, and use the exact same policy.';compareResult.hidden=true;return}const comparison=await response.json();rows(comparison,'',compareBody);compareResult.hidden=false;compareStatus.textContent=comparison.changed?'Rehearsal evidence changed. Review the fields below.':'No summary-safe evidence fields changed.'});
__PLAN_CONTROLS__
</script></body></html>""".replace("__PLAN_CONTROLS__", PLAN_CONTROLS_SCRIPT).encode()
