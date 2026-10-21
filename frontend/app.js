const $ = (selector) => document.querySelector(selector);
const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = {questions:[], total:20, user:null, records:{}, drafts:{}, results:{}, hints:{}, relationships:[], page:'guide', busy:false, storageWarning:null, mode:'login'};
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
  return `<section class="question-hint" aria-labelledby="hint-title-${qid}"><div class="hint-heading"><span class="hint-icon" aria-hidden="true">?</span><h3 id="hint-title-${qid}">Hint</h3></div><dl><div><dt>Tables & connections</dt><dd>${escapeHTML(q.hint.connections)}</dd></div><div><dt>How to approach it</dt><dd>${escapeHTML(q.hint.approach)}</dd></div></dl><button class="button" data-action="hint">${live?'Refresh':'Show'} expected SQL & live result</button><p class="table-description">${state.user?'The reference query runs against the uploaded Supabase tables each time you request it.':'Sign in to run the reference query and view its live result.'}</p>${live?`<details open><summary>Reference SQL and expected result · live database</summary><pre class="reference-sql"><code>${escapeHTML(live.expected_sql)}</code></pre><p>${live.rows.length} rows from the public schema · refreshed ${escapeHTML(live.loadedAt)}</p>${resultTable(live.columns,live.rows)}</details>`:''}</section>`;
}
let toastTimer;
function toast(message, error=false){ $('#toast').textContent=message; $('#toast').dataset.error=String(error); $('#toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').hidden=true,6000); }
async function api(path, data){
  const response=await fetch(`/api/${path}`,data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await response.json();
  if(!response.ok){
    if(response.status===401){state.user=null; state.records={}; state.drafts={}; state.results={}; state.hints={}; render(); if(!$('#auth-dialog').open) showAuth();}
    const error=new Error(result.error || 'Request failed. Please retry.'); error.payload=result; throw error;
  }
  return result;
}
function gradeFor(qid){ const record=state.records[qid]; return record && record.score !== null && record.score !== undefined && record.sql_answer === (state.drafts[qid] || '') ? record : null; }
function progress(){const grades=state.questions.map(q=>gradeFor(q.id)).filter(Boolean);return {count:grades.length,score:grades.reduce((sum,r)=>sum+Number(r.score),0)};}
function hydrate(data){state.user=data.user;state.storageWarning=data.warning || null;state.records=data.records || {};state.drafts={};state.results={};state.hints={};for(const [qid,record] of Object.entries(state.records))state.drafts[qid]=record.sql_answer || '';}
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
function reference(qid){const relevant=state.questions.find(q=>q.id===qid).tables;return `<aside class="panel reference"><div class="panel-head"><h3>Database reference</h3></div><div class="panel-body">Use <code>public.</code> before table names. Relevant tables are expanded below.</div>${tables.map(t=>`<details ${relevant.includes(t[0])?'open':''}><summary>public.${t[0]}</summary><p>${escapeHTML(t[1])}<br>${t[2].split(', ').map(escapeHTML).join('<br>')}</p></details>`).join('')}<details><summary>Table relationships</summary><pre>${escapeHTML(state.relationships.join('\n'))}</pre></details><div class="panel-body">Duration is stored in milliseconds.<br>invoice.total is the purchase amount.<br>invoice_line.quantity counts units sold.</div></aside>`;}
function question(qid){const q=state.questions.find(q=>q.id===qid);return `<div class="page-heading"><div><div class="eyebrow">THE SQL CHALLENGES</div><h1>Think it. Query it.</h1><p class="description">Work through the question, inspect your output, and submit when ready.</p></div><span class="pill">Question 0${qid} of 05</span></div>${authCallout()}<div class="question-layout"><div><section class="panel question-intro"><div class="section-header"><div class="eyebrow">QUESTION 0${qid}</div><span class="pill">${q.points} points</span></div><h2>${escapeHTML(q.title)}</h2><p class="scenario">${escapeHTML(scenarios[qid][0])}</p><p>${escapeHTML(q.description)}</p></section>${questionHint(qid)}<section class="panel editor-panel"><div class="panel-head"><label for="sql-editor" class="editor-label">SQL EDITOR</label><span id="save-status" class="muted table-description"></span></div><div class="editor-wrap"><div id="line-numbers" class="line-numbers" aria-hidden="true">1</div><textarea id="sql-editor" spellcheck="false" autocapitalize="off" autocomplete="off" aria-label="SQL query for ${escapeHTML(q.title)}" placeholder="-- Write your query here\nSELECT ...">${escapeHTML(state.drafts[qid] || '')}</textarea></div><div class="editor-actions"><button class="button" data-action="save">Save answer</button><div class="action-group"><button class="button" data-action="run">▷ Run query</button><button class="button primary" data-action="submit">Submit for grading →</button></div></div><div class="editor-note">Read-only SQL · 500-row limit · 10-second timeout · Ctrl / ⌘ + Enter to run</div></section><section id="query-output" class="panel result-panel" aria-label="Query results" aria-live="polite"></section><div class="page-navigation"><a class="button" href="${qid===1?'#guide':`#question-${qid-1}`}">← ${qid===1?'Dataset guide':'Previous question'}</a><a class="button" href="${qid===5?'#results':`#question-${qid+1}`}">${qid===5?'View results':'Next question'} →</a></div></div>${reference(qid)}</div>`;}
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
  $('#main').innerHTML=state.page==='guide'?guide():state.page==='results'?results():question(state.page);
  if(typeof state.page==='number'){
    updateEditor();const editor=$('#sql-editor');editor.addEventListener('input',()=>{state.drafts[state.page]=editor.value;updateEditor();});
    editor.addEventListener('scroll',()=>$('#line-numbers').scrollTop=editor.scrollTop);
    editor.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();perform('run');}if(e.key==='Tab'){e.preventDefault();editor.setRangeText('  ',editor.selectionStart,editor.selectionEnd,'end');editor.dispatchEvent(new Event('input'));}});
  }
  syncBusy();
}
function syncBusy(){document.querySelectorAll('[data-action="save"],[data-action="run"],[data-action="submit"],[data-action="hint"]').forEach(b=>{b.disabled=state.busy;});}
function route(){const hash=location.hash;const match=hash.match(/^#question-([1-5])$/);state.page=match?Number(match[1]):hash==='#results'?'results':'guide';render();}
function showAuth(){setMode('login');$('#auth-dialog').showModal();$('#email').focus();}
function setMode(mode){state.mode=mode;$('#auth-title').textContent=mode==='login'?'Welcome back.':'Make room for progress.';$('#auth-submit').textContent=mode==='login'?'Sign in →':'Create account →';$('#login-tab').classList.toggle('selected',mode==='login');$('#signup-tab').classList.toggle('selected',mode==='signup');$('#password').autocomplete=mode==='login'?'current-password':'new-password';$('#auth-message').textContent='';}
async function logout(){if(state.busy){toast('Wait for the current request to finish.');return;}if(Object.entries(state.drafts).some(([qid,sql])=>sql && sql!==state.records[qid]?.sql_answer)&&!confirm('You have unsaved edits. Sign out and discard those edits?'))return;try{await api('logout',{});hydrate({user:null});location.hash='guide';render();toast('You have signed out.');}catch(e){toast(e.message,true);}}
async function perform(action){
  if(action==='signin'){showAuth();return;}if(action==='logout'){await logout();return;}if(state.busy)return;if(!state.user){showAuth();return;}
  if(action==='hint'){
    const qid=state.page;state.busy=true;syncBusy();toast('Loading reference SQL and result from Supabase…');
    try{const data=await api('hint',{question_id:qid});state.hints[qid]={...data,loadedAt:new Date().toLocaleTimeString()};if(state.page===qid)render();toast('Reference result loaded from the live database.');}
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
document.addEventListener('click',e=>{const button=e.target.closest('[data-action]');if(button)perform(button.dataset.action);});
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
async function init(){try{const data=await api('questions');state.questions=data.questions;state.total=data.total;
    tables=data.database.tables.map(t=>[t.name,t.description,t.columns.map(c=>c.name).join(', ')]);
    state.relationships=data.database.tables.flatMap(t=>Object.entries(t.foreign_keys).map(([col,target])=>`${t.name}.${col} = ${target}`));try{hydrate(await api('session'));}catch(e){toast(e.message,true);}route();}catch(e){$('#main').innerHTML='<div class="panel empty-page">Could not load the quiz. Check that the Python server is running, then refresh.</div>';toast(e.message,true);}}
init();
