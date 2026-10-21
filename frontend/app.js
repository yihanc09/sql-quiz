const $ = (selector) => document.querySelector(selector);
const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = {questions:[], total:20, user:null, records:{}, drafts:{}, results:{}, hints:{}, relationships:[], page:'guide', busy:false, storageWarning:null, retrievalDrafts:{}, retrievalResults:{}, generationResults:{}, generatingQuestion:null, toolTabs:{}, database:null, mode:'login'};
let tables = [];
const scenarios = {
  1:['The catalog team wants to know how many artists are available.',['artist']],
  2:['The catalog manager wants to identify artists with the largest album catalogs.',['artist','album']],
  3:['The content team wants to compare average track length across genres.',['genre','track']],
  4:['The marketing team wants to identify the highest-spending customers.',['customer','invoice']],
  5:['The sales team wants to identify which music genres sell the most tracks.',['genre','track','invoice_line']]
};
function resultTable(columns, rows){
  return `<div class="table-scroll"><table><thead><tr>${columns.map(c=>`<th scope="col">${escapeHTML(c)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(v=>`<td>${v===null?'<span class="muted">NULL</span>':escapeHTML(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function questionHint(qid){
  const q=state.questions.find(q=>q.id===qid), live=state.hints[qid];
  return `<section class="hint-content" aria-label="Question guidance"><div class="tool-intro"><span class="tool-kicker">A LITTLE GUIDANCE</span><h3>Start with the approach.</h3><p>Use these clues as you build your query.</p></div><div class="hint-step"><span class="hint-step-number">1</span><div><h4>Connect the right tables</h4><p>${escapeHTML(q.hint.connections)}</p></div></div><div class="hint-step"><span class="hint-step-number">2</span><div><h4>Shape your result</h4><p>${escapeHTML(q.hint.approach)}</p></div></div><details class="worked-solution" ${live?'open':''}><summary>Reference SQL & expected result</summary><div class="solution-body"><p class="table-description">Run the instructor query to see the current expected output.</p><button class="button small full" data-action="hint">${live?'Refresh live reference':'Load live reference'}</button>${live?`<pre class="reference-sql"><code>${escapeHTML(live.expected_sql)}</code></pre><p class="table-description">${live.rows.length} rows · refreshed ${escapeHTML(live.loadedAt)}</p>${resultTable(live.columns,live.rows)}`:'<p class="table-description">Your editor stays unchanged when you open a reference.</p>'}</div></details></section>`;
}
function renderHint(qid){
  const target=$('#hint-content');if(target)target.innerHTML=questionHint(qid);syncBusy();
}
let toastTimer;
function toast(message, error=false){ $('#toast').textContent=message; $('#toast').dataset.error=String(error); $('#toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').hidden=true,6000); }
async function api(path, data){
  const response=await fetch(`/api/${path}`,data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await response.json();
  if(!response.ok){
    if(response.status===401){state.user=null; state.records={}; state.drafts={}; state.results={}; state.hints={}; state.retrievalDrafts={}; state.retrievalResults={}; state.generationResults={}; state.generatingQuestion=null; state.toolTabs={}; render(); if(!$('#auth-dialog').open) showAuth();}
    const error=new Error(result.error || 'Request failed. Please retry.'); error.payload=result; throw error;
  }
  return result;
}
function gradeFor(qid){ const record=state.records[qid]; return record && record.score !== null && record.score !== undefined && record.sql_answer === (state.drafts[qid] || '') ? record : null; }
function progress(){const grades=state.questions.map(q=>gradeFor(q.id)).filter(Boolean);return {count:grades.length,score:grades.reduce((sum,r)=>sum+Number(r.score),0)};}
function hydrate(data){state.user=data.user;state.storageWarning=data.warning || null;state.records=data.records || {};state.drafts={};state.results={};state.hints={};state.retrievalDrafts={};state.retrievalResults={};state.generationResults={};state.generatingQuestion=null;state.toolTabs={};for(const [qid,record] of Object.entries(state.records))state.drafts[qid]=record.sql_answer || '';}
function badge(grade){return grade ? `<span class="grade-tag ${grade.is_correct?'correct':'incorrect'}">${grade.is_correct?'Correct':'Not yet correct'}</span>`:'<span class="grade-tag">Not graded</span>';}
function navigation(){
  $('#navigation').innerHTML=`<a href="#guide" class="nav-item ${state.page==='guide'?'active':''}" ${state.page==='guide'?'aria-current="page"':''}><span class="nav-icon">▤</span><span class="nav-text">Dataset guide</span></a><div class="nav-divider"></div>${state.questions.map(q=>`<a href="#question-${q.id}" class="nav-item ${state.page===q.id?'active':''}" ${state.page===q.id?'aria-current="page"':''}><span class="nav-icon nav-number">0${q.id}</span><span class="nav-text">${escapeHTML(q.title)}</span>${gradeFor(q.id)?.is_correct?'<span class="nav-check" aria-label="Correct">✓</span>':''}</a>`).join('')}<div class="nav-divider"></div><a href="#results" class="nav-item ${state.page==='results'?'active':''}" ${state.page==='results'?'aria-current="page"':''}><span class="nav-icon">◴</span><span class="nav-text">Quiz results</span></a>`;
}
function stats(){const p=progress();return `<div class="stats"><div class="stat"><div class="stat-icon">▤</div><div><strong>05</strong><span>SQL questions</span></div></div><div class="stat"><div class="stat-icon">◴</div><div><strong>${p.score} <small>/ ${state.total}</small></strong><span>Points earned</span></div></div><div class="stat"><div class="stat-icon">✓</div><div><strong>${p.count} <small>/ 5</small></strong><span>Questions graded</span></div></div></div>`;}
function authCallout(){return state.user?(state.storageWarning?`<div class="auth-callout" role="status">${escapeHTML(state.storageWarning)}</div>`:''):`<div class="auth-callout">Explore the dataset guide, then <button data-action="signin">sign in</button> to run SQL, save answers, and submit for grading.</div>`;}
function guide(){return `<div class="page-heading"><div><div class="eyebrow">LEARN BY DOING</div><h1>Your SQL workspace.</h1><p class="description">Explore a real-world dataset. Turn business questions into SQL.</p></div><span class="pill"><span class="status-dot"></span> PostgreSQL · Chinook</span></div>
  <section class="hero"><div class="hero-copy"><div class="eyebrow">IDS706 · SQL PRACTICE</div><h2>A little curiosity.<br>A powerful query.</h2><p>Step inside the Chinook Music Store. Explore artists, albums, and customer purchases across five practical SQL challenges.</p><a class="button" href="#question-1">Start the quiz <span>→</span></a></div><div class="hero-art" aria-hidden="true"><div class="code-card"><div class="window-dots"><i></i><i></i><i></i></div><pre><b>SELECT</b> curiosity,<br>       practice<br><b>FROM</b> your_potential<br><b>WHERE</b> growth = <em>TRUE</em>;</pre><div class="code-result"><span class="status-dot"></span> A new way to think in SQL.</div></div></div></section>
  ${stats()}${authCallout()}
  <div class="section-header"><h2>Meet your dataset</h2><span>One music store. Eleven connected tables.</span></div>
  <div class="guide-grid"><section class="panel"><div class="panel-head"><h3>Chinook Music Store</h3><span class="pill">public schema</span></div><div class="schema-list">${tables.map(t=>`<div class="schema-row"><span class="table-icon" aria-hidden="true">▦</span><div><strong>public.${t[0]}</strong><p>${escapeHTML(t[1])} <span aria-hidden="true">·</span> ${escapeHTML(t[2])}</p></div></div>`).join('')}</div><div class="schema-hint">Use the <code>public.</code> schema prefix in every query. Table references stay available as you work.</div></section>
  <div><section class="panel"><div class="panel-head"><h3>A simple path to progress</h3><span class="muted">01 — 04</span></div><div class="panel-body"><ol class="steps"><li><span class="step-number">1</span><div><strong>Understand the question</strong><p>Read the business scenario and explore the relevant tables.</p></div></li><li><span class="step-number">2</span><div><strong>Write & run your SQL</strong><p>Use Run Query to inspect your results. Experiment at your own pace.</p></div></li><li><span class="step-number">3</span><div><strong>Submit for feedback</strong><p>Submit for Grading to check your answer and save your score.</p></div></li><li><span class="step-number">4</span><div><strong>Review & refine</strong><p>View your results, revisit questions, and improve your answers.</p></div></li></ol></div></section><section class="panel skills-box"><div class="panel-body"><h3>Skills you’ll put to work</h3><div class="skill-list">${['SELECT','JOIN','COUNT','AVG','SUM','GROUP BY','ORDER BY'].map(s=>`<code>${s}</code>`).join('')}</div><div class="learning-note">No need to memorize the dataset.<br>Your database reference is always close by.</div></div></section></div></div>`;}
function reference(qid){
  const relevant=state.questions.find(q=>q.id===qid).tables;
  const ordered=[...tables].sort((a,b)=>Number(relevant.includes(b[0]))-Number(relevant.includes(a[0])));
  return `<div class="schema-browser"><div class="tool-intro"><span class="tool-kicker">DATABASE REFERENCE</span><h3>Know your tables.</h3><p>Use the <code>public.</code> prefix in your queries.</p></div><label for="schema-filter" class="field-label">Find a table or column</label><input id="schema-filter" type="search" placeholder="Try artist, quantity, invoice…" autocomplete="off"><p id="schema-count" class="table-description" aria-live="polite">${tables.length} tables · relevant tables first</p>${ordered.map(t=>{
    const definition=state.database?.tables.find(item=>item.name===t[0]);
    return `<details class="schema-table" data-schema-table="${escapeHTML(t[0])}" data-search="${escapeHTML((t[0]+' '+t[2]).toLowerCase())}" ${t[0]===relevant[0]?'open':''}><summary><span>public.${escapeHTML(t[0])}</span>${relevant.includes(t[0])?'<span class="relevant-tag">This question</span>':''}</summary><div class="schema-table-body"><p class="table-description">${escapeHTML(t[1])}</p><ul class="schema-columns">${(definition?.columns || t[2].split(', ').map(name=>({name,type:''}))).map(c=>`<li><code>${escapeHTML(c.name)}</code><span>${definition?.primary_key.includes(c.name)?'<b class="key-label">PK</b> ':''}${escapeHTML(c.type)}</span></li>`).join('')}</ul></div></details>`;
  }).join('')}<p id="schema-empty" class="table-description" hidden>No matching tables or columns.</p><details class="schema-relationships"><summary>Table relationships</summary><pre>${escapeHTML(state.relationships.join('\n'))}</pre></details></div>`;
}
function retrievalPanel(qid){
  const q=state.questions.find(q=>q.id===qid), question=state.retrievalDrafts[qid] ?? q.description;
  return `<section class="knowledge-search"><div class="tool-intro"><span class="tool-kicker">CHROMADB + OPENAI</span><h3>Turn your question into SQL.</h3><p>Describe what you want to query. AI uses related database knowledge to draft your SQL.</p></div><label for="knowledge-question" class="field-label">What would you like to find?</label><textarea id="knowledge-question" rows="4" maxlength="2000" placeholder="Which tables connect customers to purchases?">${escapeHTML(question)}</textarea><button class="button primary full" data-action="generate"><span id="generate-label">Generate SQL</span><span aria-hidden="true">↗</span></button><button class="button full retrieve-only" data-action="retrieve">Search knowledge only</button><p class="tool-footnote">Review generated SQL before running it.</p><div id="generation-output" class="generation-output" aria-live="polite"></div><div id="retrieval-output" class="retrieval-output" aria-live="polite"></div></section>`;
}
function renderGeneration(qid){
  const output=$('#generation-output');if(!output)return;
  const data=state.generationResults[qid];if(!data){output.innerHTML='';return;}
  output.innerHTML=`${data.error?`<div class="feedback error">${escapeHTML(data.error)}</div>`:''}${data.sql?`<section class="generated-sql"><div class="generated-heading"><h4>Generated SQL</h4><span>${escapeHTML(data.model)}</span></div><p class="generated-question">${escapeHTML(data.question)}</p><details class="generation-sources"><summary>Sources used for this SQL (${data.retrieval?.results.length || 0})</summary><ul>${(data.retrieval?.results || []).map(item=>`<li><code>${escapeHTML(item.id)}</code></li>`).join('')}</ul></details>${data.question!==state.retrievalDrafts[qid] && state.retrievalDrafts[qid]!==undefined?'<p class="tool-footnote">Generated for the earlier question shown above.</p>':''}<pre class="reference-sql"><code>${escapeHTML(data.sql)}</code></pre><button class="button full" data-action="use-generated">Use in editor →</button><p class="tool-footnote">Replaces the editor draft. Does not run or save it.</p></section>`:''}`;
  syncBusy();
}
function renderKnowledgeResults(qid){
  const output=$('#retrieval-output');if(!output)return;const data=state.retrievalResults[qid];
  if(!data){output.innerHTML='<div class="knowledge-empty"><span aria-hidden="true">⌕</span><p>Related knowledge will appear here.</p><small>Your SQL draft stays in the editor.</small></div>';return;}
  if(data.error){output.innerHTML=`<div class="feedback error">${escapeHTML(data.error)}</div>`;return;}
  output.innerHTML=`<div class="retrieval-summary"><strong>${data.results.length} related sources</strong><span>Closest matches first</span></div><p class="retrieval-query">${escapeHTML(data.question)}</p>${data.results.map(item=>`<details class="retrieval-hit"><summary><span class="source-kind">${escapeHTML(item.metadata.kind || 'source')}</span><span class="source-name">${escapeHTML(item.metadata.table || item.id.replace(/^(semantics|example)\./,'').replaceAll('_',' '))}</span><span class="source-distance" title="Cosine distance; lower is closer">${Number(item.distance).toFixed(3)}</span></summary><p class="table-description">Source: ${escapeHTML(item.metadata.source)}</p><pre>${escapeHTML(item.text)}</pre></details>`).join('')}<details class="retrieval-diagnostics"><summary>Retrieval details</summary><p class="table-description">Searched: ${escapeHTML(data.question)}</p><p class="table-description">${data.backend==='cloud'?'Chroma Cloud':'Local Chroma'} · ${data.indexed_documents} indexed documents · ${data.embedding_dimensions} dimensions · ${escapeHTML(data.model)}<br>Cosine distance is not a confidence score. Lower values indicate closer vectors.</p></details>`;
}
function learningTools(qid){
  const tab=state.toolTabs[qid] || 'hint';
  return `<dialog id="learning-tools" class="learning-tools" aria-labelledby="tools-title"><header class="tools-header"><div><span class="tool-kicker">YOUR LEARNING TOOLKIT</span><h2 id="tools-title">A hand when you need it.</h2></div><button class="tools-close" data-action="close-tools" aria-label="Close learning tools">×</button></header><div class="tool-tabs" role="tablist" aria-label="Learning tools">${[['hint','Hint'],['knowledge','Knowledge'],['schema','Schema']].map(([key,label])=>`<button id="tool-tab-${key}" role="tab" data-tool-tab="${key}" aria-selected="${tab===key}" aria-controls="tool-panel-${key}" tabindex="${tab===key?0:-1}">${label}</button>`).join('')}</div><div class="tools-body"><section id="tool-panel-hint" role="tabpanel" aria-labelledby="tool-tab-hint" tabindex="0" ${tab==='hint'?'':'hidden'}><div id="hint-content">${questionHint(qid)}</div></section><section id="tool-panel-knowledge" role="tabpanel" aria-labelledby="tool-tab-knowledge" tabindex="0" ${tab==='knowledge'?'':'hidden'}>${retrievalPanel(qid)}</section><section id="tool-panel-schema" role="tabpanel" aria-labelledby="tool-tab-schema" tabindex="0" ${tab==='schema'?'':'hidden'}>${reference(qid)}</section></div></dialog>`;
}
const compactWorkspace=()=>window.matchMedia('(max-width: 1100px)').matches;
function selectTool(name,focus=false){
  if(!['hint','knowledge','schema'].includes(name))return;
  state.toolTabs[state.page]=name;
  document.querySelectorAll('[data-tool-tab]').forEach(button=>{const active=button.dataset.toolTab===name;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
  ['hint','knowledge','schema'].forEach(key=>{const panel=$(`#tool-panel-${key}`);if(panel)panel.hidden=key!==name;});
  if(focus)$(`#tool-tab-${name}`)?.focus();
}
function openTool(name,table){
  const dialog=$('#learning-tools');if(!dialog)return;
  if(compactWorkspace()&&!dialog.open)dialog.showModal();
  selectTool(name,true);
  if(table){
    $('#schema-filter').value='';filterSchema('');
    const detail=[...document.querySelectorAll('[data-schema-table]')].find(item=>item.dataset.schemaTable===table);
    if(detail){detail.open=true;detail.scrollIntoView({block:'nearest',behavior:'smooth'});}
  }
}
function filterSchema(value){
  const query=value.trim().toLowerCase();let visible=0;
  document.querySelectorAll('[data-schema-table]').forEach(item=>{item.hidden=!item.dataset.search.includes(query);if(!item.hidden)visible++;});
  $('#schema-count').textContent=`${visible} of ${tables.length} tables`;
  $('#schema-empty').hidden=visible>0;
}
function configureTools(){
  const dialog=$('#learning-tools');if(!dialog)return;
  if(!compactWorkspace())dialog.show();
  dialog.addEventListener('cancel',event=>{if(!compactWorkspace())event.preventDefault();});
  $('#schema-filter').addEventListener('input',event=>filterSchema(event.target.value));
}
function resizeTools(){
  const dialog=$('#learning-tools');if(!dialog)return;
  if(dialog.open)dialog.close();
  if(!compactWorkspace())dialog.show();
}
function question(qid){
  const q=state.questions.find(q=>q.id===qid), total=state.questions.length;
  return `<div class="workspace-toolbar"><div class="workspace-location"><span>SQL PRACTICE</span><span class="workspace-separator">/</span><span>Question ${String(qid).padStart(2,'0')} of ${String(total).padStart(2,'0')}</span></div><div class="workspace-pagination"><a class="button small" href="${qid===1?'#guide':`#question-${qid-1}`}" aria-label="${qid===1?'Back to dataset guide':'Previous question'}">← <span>${qid===1?'Guide':'Previous'}</span></a><a class="button small" href="${qid===total?'#results':`#question-${qid+1}`}"><span>${qid===total?'Results':'Next'}</span> →</a></div></div>${authCallout()}<div class="question-layout workspace-grid"><div class="answer-column"><section class="panel question-brief" aria-labelledby="question-title"><div class="brief-meta"><span class="tool-kicker">QUESTION ${String(qid).padStart(2,'0')}</span><div><span class="points-label">${q.points} points</span></div></div><h1 id="question-title">${escapeHTML(q.title)}</h1><p class="question-task">${escapeHTML(q.description)}</p><div class="brief-footer"><div class="table-chips" aria-label="Relevant tables">${q.tables.map(name=>`<button data-open-tool="schema" data-table="${escapeHTML(name)}" title="View ${escapeHTML(name)} schema">public.${escapeHTML(name)}</button>`).join('')}</div><div class="help-shortcuts"><button data-open-tool="hint" aria-haspopup="dialog" aria-controls="learning-tools">? Hint</button><button data-open-tool="knowledge" aria-haspopup="dialog" aria-controls="learning-tools">⌕ Knowledge</button></div></div><details class="business-context"><summary>Business context</summary><p>${escapeHTML(scenarios[qid][0])}</p></details></section><section class="panel editor-panel" aria-label="Your SQL answer"><div class="panel-head"><label for="sql-editor" class="editor-label">SQL editor <span class="editor-language">PostgreSQL</span></label><span id="save-status" class="save-status"></span></div><div class="editor-wrap"><div id="line-numbers" class="line-numbers" aria-hidden="true">1</div><textarea id="sql-editor" spellcheck="false" autocapitalize="off" autocomplete="off" aria-label="SQL query for ${escapeHTML(q.title)}" placeholder="-- Your query starts here
SELECT ...">${escapeHTML(state.drafts[qid] || '')}</textarea></div><div class="editor-actions"><button class="button save-button" data-action="save">Save draft</button><div class="action-group"><button class="button primary" data-action="run">▷ Run query</button><button class="button" data-action="submit">Submit answer →</button></div></div><div class="editor-note"><span>Read-only · 500 rows max · 10s timeout</span><span><kbd>⌘</kbd> / <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to run</span></div></section><section id="query-output" class="panel result-panel" aria-label="Query results" aria-live="polite"></section></div>${learningTools(qid)}</div>`;
}
function updateEditor(){
  const editor=$('#sql-editor');if(!editor)return;
  const qid=state.page;const record=state.records[qid];const sql=state.drafts[qid] || '';
  $('#line-numbers').textContent=Array.from({length:Math.max(9,sql.split('\n').length)},(_,i)=>i+1).join('\n');
  $('#save-status').textContent=!sql?'Draft':record?.sql_answer===sql?(gradeFor(qid)?'Saved & graded':'Saved draft'):'Unsaved changes';
  renderOutput(); navigation();
}
function renderOutput(){
  const output=$('#query-output');if(!output)return;const qid=state.page;const result=state.results[qid];const grade=gradeFor(qid);
  output.innerHTML=`<div class="panel-head"><h3>Query results</h3>${grade?badge(grade):`<span class="muted table-description">${result?.table?`${result.table.data.length} rows returned`:'Output'}</span>`}</div>${result?.table?`<div class="table-scroll"><table><thead><tr>${result.table.columns.map(c=>`<th scope="col">${escapeHTML(c)}</th>`).join('')}</tr></thead><tbody>${result.table.data.map(row=>`<tr>${row.map(v=>`<td>${v===null?'<span class="muted">NULL</span>':escapeHTML(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<div class="result-empty">Run your query to see the results here.</div>'}${result && result.sql !== (state.drafts[qid] || '')?'<div class="feedback incorrect">This output is from an earlier version of your query. Run again to refresh it.</div>':''}${result?.error?`<div class="feedback error">${escapeHTML(result.error)}</div>`:''}${result?.warning?`<div class="feedback incorrect">${escapeHTML(result.warning)}</div>`:''}${grade?`<div class="feedback ${grade.is_correct?'':'incorrect'}">${grade.is_correct?'✓ Correct':'Not yet correct'} · ${grade.score} / 4 points.${result?.grade?.feedback?' '+escapeHTML(result.grade.feedback):''}</div>`:''}`;
}
function results(){const p=progress();return `<div class="page-heading"><div><div class="eyebrow">YOUR PROGRESS</div><h1>Every query counts.</h1><p class="description">Review your scores and pick up where you left off.</p></div><span class="pill">${p.count===5?'All questions graded':'Keep exploring'}</span></div>${stats()}${authCallout()}<section class="panel"><div class="panel-head"><h3>Quiz results</h3><span class="muted table-description">${p.count} of 5 graded</span></div><div class="panel-body"><div class="section-header"><span>${p.count===5?'All five questions have been graded. You can still revise your answers.':'Submit each answer for grading to record your score.'}</span><strong>${p.score} / ${state.total}</strong></div><progress class="full" value="${p.count}" max="5" aria-label="Questions graded">${p.count} / 5</progress></div><div class="table-scroll"><table class="results-table"><thead><tr><th scope="col">QUESTION</th><th scope="col">STATUS</th><th scope="col">SCORE</th><th scope="col">ACTION</th></tr></thead><tbody>${state.questions.map(q=>{const g=gradeFor(q.id);return `<tr><td>0${q.id} &nbsp; ${escapeHTML(q.title)}</td><td>${badge(g)}</td><td>${g?g.score:'—'} / ${q.points}</td><td><a class="button small" href="#question-${q.id}">Review ↗</a></td></tr>`;}).join('')}</tbody></table></div><div class="panel-body"><p class="table-description">Editing an answer clears its displayed grade until you submit again. Only saved drafts and submitted grades are restored after signing in again.</p></div></section><div class="page-navigation"><a class="button" href="#question-1">← Review answers</a>${state.user?'<button class="button primary" data-action="logout">Finish & sign out →</button>':''}</div>`;}
function render(){
  navigation();$('#account-button').textContent=state.user?'Sign out ↗':'Sign in ↗';$('#account-button').title=state.user?.email || 'Sign in';
  $('#page-name').textContent=state.page==='guide'?'Dataset guide':state.page==='results'?'Quiz results':`Question ${state.page}`;
  $('#main').classList.toggle('question-page',typeof state.page==='number');
  $('#main').innerHTML=state.page==='guide'?guide():state.page==='results'?results():question(state.page);
  if(typeof state.page==='number'){
    updateEditor();renderGeneration(state.page);renderKnowledgeResults(state.page);configureTools();
    $('#knowledge-question').addEventListener('input',e=>{state.retrievalDrafts[state.page]=e.target.value;renderGeneration(state.page);});
    const editor=$('#sql-editor');editor.addEventListener('input',()=>{state.drafts[state.page]=editor.value;updateEditor();});
    editor.addEventListener('scroll',()=>$('#line-numbers').scrollTop=editor.scrollTop);
    editor.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();perform('run');}if(e.key==='Tab'&&!e.shiftKey){e.preventDefault();editor.setRangeText('  ',editor.selectionStart,editor.selectionEnd,'end');editor.dispatchEvent(new Event('input'));}});
  }
  syncBusy();
}
function syncBusy(){document.querySelectorAll('[data-action="save"],[data-action="run"],[data-action="submit"],[data-action="hint"],[data-action="retrieve"],[data-action="generate"],[data-action="use-generated"]').forEach(b=>{b.disabled=state.busy;});const label=$('#generate-label');if(label)label.textContent=state.generatingQuestion===state.page?'Generating…':'Generate SQL';}
function route(){const previous=state.page;const hash=location.hash;const match=hash.match(/^#question-([1-5])$/);state.page=match?Number(match[1]):hash==='#results'?'results':'guide';render();if(previous!==state.page)window.scrollTo({top:0,behavior:'instant'});}
function showAuth(){setMode('login');$('#auth-dialog').showModal();$('#email').focus();}
function setMode(mode){state.mode=mode;$('#auth-title').textContent=mode==='login'?'Welcome back.':'Make room for progress.';$('#auth-submit').textContent=mode==='login'?'Sign in →':'Create account →';$('#login-tab').classList.toggle('selected',mode==='login');$('#signup-tab').classList.toggle('selected',mode==='signup');$('#password').autocomplete=mode==='login'?'current-password':'new-password';$('#auth-message').textContent='';}
async function logout(){if(state.busy){toast('Wait for the current request to finish.');return;}if(Object.entries(state.drafts).some(([qid,sql])=>sql && sql!==state.records[qid]?.sql_answer)&&!confirm('You have unsaved edits. Sign out and discard those edits?'))return;try{await api('logout',{});hydrate({user:null});location.hash='guide';render();toast('You have signed out.');}catch(e){toast(e.message,true);}}
async function perform(action){
  if(action==='close-tools'){$('#learning-tools')?.close();return;}
  if(action==='signin'){showAuth();return;}if(action==='logout'){await logout();return;}if(state.busy)return;if(!state.user){showAuth();return;}
  if(action==='use-generated'){
    const data=state.generationResults[state.page];if(!data?.sql)return;
    state.drafts[state.page]=data.sql;
    const editor=$('#sql-editor');editor.value=data.sql;updateEditor();
    if(compactWorkspace())$('#learning-tools').close();
    editor.focus({preventScroll:true});editor.scrollIntoView({block:'nearest',behavior:'smooth'});
    toast('Generated SQL added to your draft. Review it, then run when ready.');return;
  }
  if(action==='generate'){
    const qid=state.page, question=$('#knowledge-question').value;
    state.retrievalDrafts[qid]=question;
    if(!question.trim()){toast('Enter a natural-language question first.',true);return;}
    state.busy=true;state.generatingQuestion=qid;syncBusy();toast('Retrieving knowledge and generating SQL…');
    try{
      const data=await api('generate',{question,top_k:5});
      state.generationResults[qid]=data;state.retrievalResults[qid]=data.retrieval;
      if(state.page===qid){renderGeneration(qid);renderKnowledgeResults(qid);}
      toast('SQL generated. Review it before adding it to your editor.');
    }catch(e){
      if(state.user){state.generationResults[qid]={...state.generationResults[qid],error:e.message};if(state.page===qid)renderGeneration(qid);}
      toast(e.message,true);
    }finally{state.busy=false;state.generatingQuestion=null;syncBusy();}return;
  }
  if(action==='retrieve'){
    const qid=state.page, question=$('#knowledge-question').value;
    state.retrievalDrafts[qid]=question;
    if(!question.trim()){toast('Enter a natural-language question first.',true);return;}
    state.busy=true;syncBusy();toast('Searching the Chroma vector index…');
    try{const data=await api('retrieve',{question,top_k:5});state.retrievalResults[qid]=data;if(state.page===qid)renderKnowledgeResults(qid);toast(`Retrieved ${data.results.length} related knowledge documents.`);}
    catch(e){if(state.user){state.retrievalResults[qid]={error:e.message};if(state.page===qid)renderKnowledgeResults(qid);}toast(e.message,true);}
    finally{state.busy=false;syncBusy();}return;
  }
  if(action==='hint'){
    const qid=state.page;state.busy=true;syncBusy();toast('Loading reference SQL and result from Supabase…');
    try{const data=await api('hint',{question_id:qid});state.hints[qid]={...data,loadedAt:new Date().toLocaleTimeString()};if(state.page===qid)renderHint(qid);toast('Reference result loaded from the live database.');}
    catch(e){toast(e.message,true);}
    finally{state.busy=false;syncBusy();}return;
  }
  const qid=state.page;const sql=state.drafts[qid] || '';if(!sql.trim()){toast('Write a SQL query first.',true);$('#sql-editor')?.focus();return;}
  state.busy=true;syncBusy();toast(action==='save'?'Saving your answer…':action==='submit'?'Running and grading your query…':'Running your query…');
  try{
    const data=await api(action,{question_id:qid,sql});
    if(data.records)state.records=data.records;
    if(action!=='save')state.results[qid]={...data,sql};
    if(typeof state.page==='number')updateEditor();else render();
    toast(action==='save'?'Answer saved.':data.grade?`${data.grade.is_correct?'Correct!':'Not yet correct.'} ${data.grade.score} / 4 points.`:`Query complete. ${data.table.data.length} rows returned.`);
  }catch(e){if(state.user && action!=='save'){state.results[qid]={...e.payload,sql,error:e.message};if(state.page===qid)renderOutput();}toast(e.message,true);}
  finally{state.busy=false;syncBusy();}
}
document.addEventListener('click',e=>{
  const tab=e.target.closest('[data-tool-tab]');if(tab){selectTool(tab.dataset.toolTab);return;}
  const shortcut=e.target.closest('[data-open-tool]');if(shortcut){openTool(shortcut.dataset.openTool,shortcut.dataset.table);return;}
  const button=e.target.closest('[data-action]');if(button)perform(button.dataset.action);
});
document.addEventListener('keydown',e=>{
  const tab=e.target.closest('[data-tool-tab]');if(!tab)return;
  const keys=['hint','knowledge','schema'],current=keys.indexOf(tab.dataset.toolTab);let next;
  if(e.key==='ArrowRight')next=(current+1)%keys.length;
  else if(e.key==='ArrowLeft')next=(current+keys.length-1)%keys.length;
  else if(e.key==='Home')next=0;
  else if(e.key==='End')next=keys.length-1;
  else return;
  e.preventDefault();selectTool(keys[next],true);
});
window.matchMedia('(max-width: 1100px)').addEventListener('change',resizeTools);
$('#account-button').addEventListener('click',()=>state.user?logout():showAuth());$('#close-auth').addEventListener('click',()=>$('#auth-dialog').close());
$('#login-tab').addEventListener('click',()=>setMode('login'));$('#signup-tab').addEventListener('click',()=>setMode('signup'));
$('#auth-dialog').addEventListener('close',()=>{$('#password').value='';});
$('#auth-form').addEventListener('submit',async e=>{
  e.preventDefault();$('#auth-submit').disabled=true;$('#auth-message').textContent='Connecting…';
  try{const data=await api(state.mode==='login'?'login':'signup',{email:$('#email').value,password:$('#password').value});if(data.user){hydrate(data);$('#auth-dialog').close();render();toast(data.warning || 'Signed in. Your saved work is ready.', Boolean(data.warning));}else{$('#auth-message').textContent=data.message;$('#password').value='';}}
  catch(error){$('#auth-message').textContent=error.message;}finally{$('#auth-submit').disabled=false;}
});
window.addEventListener('hashchange',route);
window.addEventListener('beforeunload',e=>{if(state.user&&Object.entries(state.drafts).some(([qid,sql])=>sql && sql!==state.records[qid]?.sql_answer)){e.preventDefault();e.returnValue='';}});
async function init(){try{const data=await api('questions');state.questions=data.questions;state.total=data.total;state.database=data.database;
    tables=data.database.tables.map(t=>[t.name,t.description,t.columns.map(c=>c.name).join(', ')]);
    state.relationships=data.database.tables.flatMap(t=>Object.entries(t.foreign_keys).map(([col,target])=>`${t.name}.${col} = ${target}`));try{hydrate(await api('session'));}catch(e){toast(e.message,true);}route();}catch(e){$('#main').innerHTML='<div class="panel empty-page">Could not load the quiz. Check that the Python server is running, then refresh.</div>';toast(e.message,true);}}
init();
