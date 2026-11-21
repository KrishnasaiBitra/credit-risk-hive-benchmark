/* Credit Risk Lab: vanilla JavaScript, saved research data, local model inference. */
'use strict';
const $ = (selector, parent=document) => parent.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (n, digits=0) => Number(n).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const pct = (n, digits=2) => `${fmt(n*100,digits)}%`;
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const names = {CSV:'CSV',Raw_ORC:'Raw ORC',Prepared_ORC:'Prepared ORC'};
const colors = {CSV:'#9babb6',Raw_ORC:'#6794b8',Prepared_ORC:'#24876e','Logistic Regression':'#7196b6',LightGBM:'#278b73',Dummy:'#b3bdc3'};
const pageNames={overview:'Overview',architecture:'Project architecture',pipelines:'Pipeline benchmark',models:'Model comparison',extensions:'New model experiments',fairness:'Fairness audit',literature:'Research comparison',demo:'Loan risk demo',reports:'Reports & method'};
let data, currentRoute, navigationVersion=0;

async function api(path, options={}) {
  const response=await fetch(path,{...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})}});
  const payload=await response.json().catch(()=>({detail:'The server returned an unreadable response.'}));
  if(!response.ok){
    let detail=payload.detail||`Request failed (${response.status}).`;
    if(Array.isArray(detail)) detail=detail.map(item=>{
      const field=item.loc?.slice(1).join(' ').replaceAll('_',' ');
      return `${field?field+': ':''}${item.msg.replace(/^Value error, /,'')}`;
    }).join('\n');
    throw new Error(detail);
  }
  return payload;
}

function heading(eyebrow,title,description,badge='Recorded experiment') {
  return `<div class="page-eyebrow">${esc(eyebrow)}</div><div class="page-heading"><div><h1>${esc(title)}</h1><p>${esc(description)}</p></div><span class="pill">${icon('file')}${esc(badge)}</span></div>`;
}
function metric(label,value,sub,emphasis=false,glyph='bars'){
  return `<div class="metric${emphasis?' emphasis':''}"><div class="metric-label">${esc(label)}</div><span class="metric-corner">${icon(glyph)}</span><div class="metric-value">${esc(value)}</div><div class="metric-sub">${esc(sub)}</div></div>`;
}
function panelHeader(title,description='',extra=''){
  return `<div class="panel-heading"><div><h2>${esc(title)}</h2>${description?`<p class="panel-desc">${esc(description)}</p>`:''}</div>${extra}</div>`;
}
function scope(text){return `<div class="scope-note">${icon('file')}<span>${esc(text)}</span></div>`;}
function table(headers,rows,classes=[]){
  return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map((row,i)=>`<tr class="${classes[i]||''}">${row.map((cell,j)=>`<td${j===0?' class="table-name"':''}>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function source(text){return `<div class="source-line">SOURCE <code>${esc(text)}</code></div>`;}
function legend(){return `<div class="legend"><span><i style="background:${colors['Logistic Regression']}"></i>Logistic Regression</span><span><i style="background:${colors.LightGBM}"></i>LightGBM</span></div>`;}
function definition(title,body){return `<details class="definition"><summary>${esc(title)}</summary><p>${esc(body)}</p></details>`;}
function chart(id, height=260){return `<div id="${id}" class="chart" style="height:${height}px" role="img" aria-label="${id.replaceAll('-',' ')}"></div>`;}
function plot(id,traces,layout={}){
  if(!window.Plotly){$(`#${id}`).innerHTML='<div class="plot-error">The local chart library did not load. Restart the application or use the result tables below.</div>';return;}
  const base={font:{family:'Segoe UI, Arial, sans-serif',size:10,color:'#70818b'},paper_bgcolor:'transparent',plot_bgcolor:'transparent',
    margin:{l:95,r:32,t:15,b:38},showlegend:false,hoverlabel:{bgcolor:'#fff',font:{family:'Segoe UI',size:12}},
    xaxis:{gridcolor:'#edf0ed',zeroline:false,fixedrange:true},yaxis:{showgrid:false,zeroline:false,fixedrange:true},
    ...layout};
  return Plotly.newPlot(id,traces,base,{responsive:true,displayModeBar:false,displaylogo:false});
}
function horizontalPipelines(id,key,units){
  const rows=data.pipelines.slice().reverse();
  const values=rows.map(row=>key==='storage'?row.logical_bytes/1e6:row.median_seconds);
  const trace={type:'bar',orientation:'h',y:rows.map(row=>names[row.pipeline]),x:values,
    marker:{color:rows.map(row=>colors[row.pipeline]),cornerradius:3},width:.43,
    text:values.map(value=>`${fmt(value,2)} ${units}`),textposition:'outside',cliponaxis:false,
    hovertemplate:`%{y}<br>%{x:.2f} ${units}<extra></extra>`};
  if(key!=='storage')trace.error_x={type:'data',symmetric:false,array:rows.map(r=>r.maximum_seconds-r.median_seconds),arrayminus:rows.map(r=>r.median_seconds-r.minimum_seconds),color:'#718c83',thickness:1,width:3};
  return plot(id,[trace],{xaxis:{gridcolor:'#edf0ed',zeroline:false,fixedrange:true,range:[0,Math.max(...values)*1.24],title:{text:units==='s'?'Full export time (seconds)':'Logical storage (decimal MB)',font:{size:10}}},margin:{l:100,r:15,t:5,b:38},bargap:.5});
}
function gapChart(id,key='false_positive_rate_gap'){
  const rows=['Logistic Regression','LightGBM'].map(name=>data.gaps.find(row=>row.model===name)).reverse();
  return plot(id,[{type:'bar',orientation:'h',y:rows.map(r=>r.model),x:rows.map(r=>r[key]*100),width:.45,
    marker:{color:rows.map(r=>colors[r.model]),cornerradius:3},text:rows.map(r=>`${fmt(r[key]*100,2)} pp`),textposition:'outside',cliponaxis:false,
    hovertemplate:'%{y}<br>%{x:.2f} percentage points<extra></extra>'}],{margin:{l:132,r:25,t:4,b:36},xaxis:{gridcolor:'#edf0ed',range:[0,40],title:{text:'Gap (percentage points)',font:{size:10}},fixedrange:true}});
}

function overview(){
  const lgb=data.models.find(row=>row.model==='LightGBM');
  const prepared=data.pipelines.find(row=>row.pipeline==='Prepared_ORC');
  return heading('A REPRODUCIBLE BENCHMARK','Credit risk research overview','Explore how Hive pipeline design affects processing, then examine prediction quality and group disparities.')+
    `<div class="metric-grid">${metric('LOANS IN COHORT',fmt(data.cohort.rows),'Resolved 36-month loans','', 'layers')}${metric('VERIFIED PIPELINES','03','Identical feature values',false,'check')}${metric('PREPARED ORC SPEEDUP',`${fmt(prepared.speedup,2)}×`,'Repeated export vs CSV',true)}${metric('LIGHTGBM TEST ROC-AUC',fmt(lgb.roc_auc,4),'Fixed model · 90,615 test loans',false,'loan')}</div>`+
    `<div class="grid-main"><section class="panel">${panelHeader('Full-feature export time','Median and observed range across five measured runs','<span class="panel-kicker">LOWER IS FASTER</span>')}${chart('overview-pipeline-chart',245)}<p class="chart-note">Reads from Hive through a complete CSV export to Python.</p></section>
    <section class="panel">${panelHeader('Predictive model comparison','Held-out test results at threshold 0.15')}${table(['Model','ROC-AUC','Recall'],data.models.filter(r=>r.model!=='Dummy').map(r=>[esc(r.model),fmt(r.roc_auc,4),pct(r.chargeoff_recall)]),['','winner-row'])}<div class="mini-stats"><div><small>TEST LOANS</small><strong>${fmt(data.cohort.splits.test)}</strong></div><div><small>CHARGE-OFF RATE</small><strong>${pct(data.cohort.test_positive/data.cohort.splits.test)}</strong></div></div><div class="inline-note">LightGBM improves modestly. Its false-positive rate remains ${pct(lgb.false_positive_rate)}.</div><a class="text-link" href="#models" style="margin-top:17px">Explore the models ${icon('arrow')}</a></section></div>`+
    `<div class="grid-main"><section class="panel">${panelHeader('Home-ownership group audit','False-positive-rate gap across MORTGAGE, RENT and OWN',`<a class="text-link" href="#fairness">View audit ${icon('arrow')}</a>`)}${chart('overview-gap-chart',205)}<p class="chart-note">Smaller gaps still represent substantial disparities.</p></section>
    <section class="panel">${panelHeader('The study at a glance','A controlled experiment with explicit boundaries')}<dl class="facts"><div><dt>Public dataset</dt><dd>Lending Club</dd></div><div><dt>Loan issue years</dt><dd>${data.cohort.years}</dd></div><div><dt>Model inputs</dt><dd>${data.cohort.features.length} features</dd></div><div><dt>Positive outcome label</dt><dd>Charged Off</dd></div><div><dt>Reproducibility check</dt><dd style="color:var(--teal)">Passed</dd></div></dl><a class="text-link" href="#reports" style="margin-top:16px">Read method & limitations ${icon('arrow')}</a></section></div>`+
    scope('These are recorded study results, not a live cluster monitor. The single-host benchmark and retrospective cohort limit how far the findings generalize.');
}

function pipelines(){
  return heading('HIVE / HDFS / TEZ','Pipeline benchmark','Compare three ways of preparing and exporting the same loan features. Every complete-row equivalence check passed.')+
  `<div class="metric-grid">${metric('CSV BASELINE',`${fmt(data.pipelines[0].median_seconds,2)} s`,'Median full-feature export')}${metric('PREPARED ORC',`${fmt(data.pipelines[2].median_seconds,2)} s`,'Median full-feature export',true)}${metric('RAW ORC STORAGE',`${fmt(data.pipelines[1].logical_bytes/1e6,2)} MB`,'88.1% smaller than raw CSV',false,'layers')}${metric('FEATURE PREPARATION',`${fmt(data.feature_preparation_seconds,2)} s`,'Excludes raw ORC conversion',false,'file')}</div>`+
  `<div class="grid-two"><section class="panel">${panelHeader('Export latency','Five measured runs per pipeline; error bars show min–max')}${chart('pipeline-latency',290)}</section><section class="panel">${panelHeader('Stored representation','HDFS logical bytes; replication factor 1')}${chart('pipeline-storage',290)}<p class="chart-note">Prepared ORC stores transformed features, while raw CSV and raw ORC store the same raw values.</p></section></div>`+
  `<section class="panel">${panelHeader('Why the pipelines differ','The feature definitions stay the same. The stored representation and timing of calculation change.')}<div class="pipeline-process"><div><span class="step-number">01 / CSV</span><h3>Calculate during export</h3><p>Read CSV text, parse values, calculate features and apply saved training statistics.</p></div><div><span class="step-number">02 / RAW ORC</span><h3>Read compressed columns</h3><p>Read the equivalent raw ORC data, then calculate the same features during export.</p></div><div><span class="step-number">03 / PREPARED ORC</span><h3>Reuse calculated features</h3><p>Read features already calculated and stored in ORC. Refresh them when data or rules change.</p></div></div></section>`+
  `<section class="panel">${panelHeader('Preparation cost & repeated use','Single preparation measurements; break-even estimates use the measured export medians.')}${table(['Pipeline','Median export','Observed range','Preparation','Estimated break-even'],data.pipelines.map(row=>[names[row.pipeline],`${fmt(row.median_seconds,2)} s`,`${fmt(row.minimum_seconds,2)}–${fmt(row.maximum_seconds,2)} s`,`${fmt(row.preparation_seconds,2)} s`,row.pipeline==='CSV'?'Baseline':`${row.estimated_break_even_exports} exports`]))}<div class="inline-note">Prepared ORC preparation totals ${fmt(data.pipelines[2].preparation_seconds,2)} s: ${fmt(data.conversion_seconds,2)} s raw conversion + ${fmt(data.feature_preparation_seconds,2)} s feature materialization. The stages were timed separately; the sum estimates an end-to-end preparation cost.</div>${definition('How is break-even estimated?','Additional preparation time divided by the saving per export, rounded up to a whole number of exports. This excludes cohort extraction, cluster startup and training. It is an arithmetic estimate, not a controlled cold-start measurement.')}</section>`+
  `<section class="panel">${panelHeader('Sampled container resources','Separate monitored runs; totals across seven project services, excluding the Python client.')}${table(['Pipeline','Median sampled CPU¹','Highest sampled memory','Snapshots / run'],data.resources.map(row=>[names[row.pipeline],pct(row.sampled_cpu_median/100),`${fmt(row.sampled_memory_max_mib,1)} MiB`,`${row.min_snapshots}–${row.max_snapshots}`]))}<p class="chart-note">¹ Median of per-run CPU medians. Docker CPU can exceed 100% across cores. Memory includes resident services and is not a true peak or incremental query cost. Prepared ORC has very few samples.</p></section>`+
  `<details class="panel"><summary>Inspect the original measured exports</summary>${table(['Round','Pipeline','Export time','Records'],data.runs.filter(row=>row.phase==='measured').map(row=>[esc(row.round),names[row.pipeline],`${fmt(row.total_export_seconds,2)} s`,fmt(row.row_count)]))}${source('results/pipeline_benchmark/exports_v2_20261108_124424/runs.csv')}</details>`+
  scope('Complete export timing includes Hive processing, transfer and CSV writing. Query-result caching was disabled; OS/JVM caches were not cleared. No cluster job is launched from this page.');
}

function fairness(){
  const lgb=data.gaps.find(r=>r.model==='LightGBM');
  return heading('DESCRIPTIVE GROUP AUDIT','Fairness audit','Inspect how prediction errors differ across home-ownership groups. These comparisons describe disparities, not their causes.')+
  `<div class="metric-grid">${metric('LIGHTGBM FPR GAP',`${fmt(lgb.false_positive_rate_gap*100,2)} pp`,'Largest minus smallest group FPR',true)}${metric('LIGHTGBM RECALL GAP',`${fmt(lgb.chargeoff_recall_gap*100,2)} pp`,'Largest minus smallest group recall')}${metric('AUDITED GROUPS','03','MORTGAGE · RENT · OWN',false,'scale')}${metric('BOOTSTRAP SAMPLES','1,000','Paired independent-loan resamples',false,'layers')}</div>`+
  `<div class="view-controls"><label for="audit-model">Display</label><select id="audit-model"><option value="both">Both models</option><option>LightGBM</option><option>Logistic Regression</option></select><span class="control-inline">Fixed threshold 0.15 · error bars show pointwise 95% intervals</span></div>`+
  `<div class="grid-two"><section class="panel">${panelHeader('False-positive rate','Fully paid loans incorrectly flagged as risky.')}${chart('audit-fpr',300)}</section><section class="panel">${panelHeader('Charge-off recall','Charged-off loans correctly flagged.')}${chart('audit-recall',300)}</section></div>`+
  `<section class="panel">${panelHeader('Group-level results','Sample and outcome counts are essential context for each rate.')}<div id="audit-table"></div><p class="chart-note">OTHER_UNKNOWN has one test loan. It remains in overall results but is excluded from group-gap comparisons and group-rate intervals.</p></section>`+
  `<div class="grid-two"><section class="panel">${panelHeader('False-positive-rate gap','Maximum minus minimum group rate.')}${chart('fairness-gap',215)}</section><section class="panel">${panelHeader('What the audit can tell us','Smaller observed gaps are useful, but do not settle fairness.')}<div class="glossary"><p><strong>Grouping:</strong> home ownership is a socioeconomic attribute and an input to the models.</p><p><strong>Observation:</strong> LightGBM has smaller measured gaps, while substantial differences remain.</p><p><strong>Equalized-odds difference:</strong> the larger of the recall gap and false-positive-rate gap across the three groups.</p><p><strong>Limits:</strong> no protected-demographic audit, causal discrimination study, mitigation or group-specific thresholds were implemented.</p></div></section></div>`+
  scope('A gap of 23.32 percentage points describes a difference between rates. It is not a 23.32% relative reduction, a proof of discrimination, or a guarantee of fairness.');
}
function drawAudit(){
  const selected=$('#audit-model').value;
  const models=selected==='both'?['Logistic Regression','LightGBM']:[selected];
  const groupOrder=['MORTGAGE','RENT','OWN'];
  for(const [id,key] of [['audit-fpr','false_positive_rate'],['audit-recall','chargeoff_recall']]){
    const traces=models.map(name=>{
      const rows=groupOrder.map(group=>data.groups.find(r=>r.model===name&&r.group===group));
      const cis=groupOrder.map(group=>data.intervals.find(r=>r.model===name&&r.metric===`${group}_${key}`));
      return {type:'bar',name,y:rows.map(r=>r[key]*100),x:groupOrder,marker:{color:colors[name],cornerradius:3},width:models.length===2?.27:.45,
        error_y:{type:'data',symmetric:false,array:rows.map((r,i)=>(cis[i].upper_95-r[key])*100),arrayminus:rows.map((r,i)=>(r[key]-cis[i].lower_95)*100),thickness:1,color:'#7d918a',width:3},
        hovertemplate:`${esc(name)}<br>%{x}<br>%{y:.2f}%<extra></extra>`};
    });
    plot(id,traces,{barmode:'group',showlegend:true,legend:{orientation:'h',y:1.15,font:{size:9}},margin:{l:42,r:8,t:34,b:38},yaxis:{range:[0,80],ticksuffix:'%',gridcolor:'#edf0ed',zeroline:false,fixedrange:true},xaxis:{fixedrange:true}});
  }
  $('#audit-table').innerHTML=table(['Model','Group','Loans','Charged off','Precision','Recall','FPR','Flag rate'],models.flatMap(name=>groupOrder.map(group=>data.groups.find(r=>r.model===name&&r.group===group))).map(r=>[esc(r.model),esc(r.group),fmt(r.loans),fmt(r.charged_off),pct(r.precision),pct(r.chargeoff_recall),pct(r.false_positive_rate),pct(r.flag_rate)]));
}

const demoFields={
  loan_amount:{label:'Loan amount',unit:'USD',min:1,step:'any',hint:'Training cohort: $1,000–$35,000.'},
  annual_income:{label:'Annual income',unit:'USD / year',min:1,step:'any'},
  dti:{label:'Debt-to-income ratio',unit:'%',min:0,step:'any',hint:'Use the dataset ratio, e.g. 14.92.'},
  employment_years:{label:'Employment length',unit:'years',min:0,max:80,step:'any',optional:true,hint:'10 represents 10+ years; blank means missing.'},
  fico_range_low:{label:'FICO range · lower',min:300,max:850,step:'any'},
  fico_range_high:{label:'FICO range · upper',min:300,max:850,step:'any',hint:'We calculate (lower + upper) / 2.'},
  revolving_utilization:{label:'Revolving utilization',unit:'%',min:0,step:'any',optional:true,hint:'Blank uses the frozen training fill. Values above 100 are retained.'},
  credit_history_months:{label:'Credit history',unit:'months',min:0,max:1500,step:1,hint:'Months from earliest credit line to loan issue date.'},
  revolving_balance:{label:'Revolving balance',unit:'USD',min:0,step:'any'},
  open_accounts:{label:'Open credit accounts',min:0,step:1},
  total_accounts:{label:'Total credit accounts',min:0,step:1},
  delinq_2yrs:{label:'Delinquencies · last 2 years',min:0,step:1},
  inq_last_6mths:{label:'Inquiries · last 6 months',min:0,step:1},
  public_records:{label:'Public records',min:0,step:1},
  bankruptcies:{label:'Recorded bankruptcies',min:0,step:1}
};
function field(key){
  const f=demoFields[key];
  return `<div class="field"><label for="${key}">${esc(f.label)}${f.unit?` <span style="font-weight:400;color:var(--muted)">(${esc(f.unit)})</span>`:''}</label><input id="${key}" name="${key}" type="number" min="${f.min??0}" ${f.max?`max="${f.max}"`:''} step="${f.step||1}" ${f.optional?'':'required'} ${f.hint?`aria-describedby="help-${key}"`:''}>${f.hint?`<small id="help-${key}">${esc(f.hint)}</small>`:''}</div>`;
}
function selectField(key,label,options){return `<div class="field"><label for="${key}">${esc(label)}</label><select id="${key}" name="${key}">${options.map(v=>`<option value="${esc(v)}">${esc(v.replaceAll('_',' '))}</option>`).join('')}</select></div>`;}
let demoExamples=[],activeExample=null,previousPrediction=null,demoRevision=0;
async function demoPage(version){
  const [schema,examples]=await Promise.all([api('/api/demo/schema'),api('/api/demo/examples')]);
  if(version!==navigationVersion)return;
  demoExamples=examples;
  $('#view').innerHTML=heading('SAVED MODELS / NEW INFERENCE','Loan risk demonstration','Review a historical example, change its inputs, and estimate charge-off risk using four fixed models.','Saved-model inference')+
    `<div class="demo-layout"><section class="panel">${panelHeader('Borrower & loan details','All amounts are in US dollars. Other credit inputs are available below.')}<div class="example-strip"><label for="example-select">Historical example</label><select id="example-select">${examples.map((item,i)=>`<option value="${i}">${esc(item.label)}</option>`).join('')}</select><button class="button button-secondary button-small" id="load-example" type="button">Load example</button></div>
    <form id="loan-form" novalidate><div class="form-grid">${['loan_amount','annual_income','dti','employment_years','fico_range_low','fico_range_high'].map(field).join('')}${selectField('home_ownership_group','Home ownership',schema.home_ownership_groups)}${selectField('purpose','Loan purpose',schema.purposes)}${selectField('verification_status','Income verification',schema.verification_statuses)}${field('revolving_utilization')}</div>
    <details class="advanced"><summary>Additional credit history · included in every prediction</summary><div class="form-grid">${['credit_history_months','revolving_balance','open_accounts','total_accounts','delinq_2yrs','inq_last_6mths','public_records','bankruptcies'].map(field).join('')}</div></details>
    <div id="form-error" class="validation-error" role="alert"></div><div class="submit-row"><button class="button" id="predict-button" type="submit">${icon('loan')}Estimate charge-off risk</button><small>Uses four saved models. No model retraining.</small></div></form></section>
    <div class="result-panel"><section class="panel">${panelHeader('Prediction results','Validation-selected thresholds: 15% / 12.5%')}<div id="demo-results"><div class="empty-result"><div class="empty-icon">${icon('loan')}</div><h3>Ready when you are</h3><p>Load an example and review its inputs.<br>Then run all four saved models.</p><small>Results are estimated probabilities,<br>not loan approval decisions.</small></div></div></section><div class="callout"><strong>Research scope</strong><br>Models were trained on resolved, 36-month Lending Club loans from 2012–2014. They have moderate predictive performance and are not established as calibrated for current borrowers.</div></div></div>`;
  $('#load-example').addEventListener('click',()=>fillExample(Number($('#example-select').value)));
  $('#loan-form').addEventListener('submit',predictDemo);
  $('#loan-form').addEventListener('input',()=>{
    demoRevision++;
    activeExample=null;
    if(previousPrediction){
      $('#demo-results').innerHTML='<div class="inline-note">Inputs changed. Run the models again to update these results.</div>';
      previousPrediction=null;
    }
  });
  fillExample(0);
}
function fillExample(index){
  demoRevision++;
  activeExample=demoExamples[index];
  for(const [key,value] of Object.entries(activeExample.inputs)){
    const input=$(`[name="${key}"]`,$('#loan-form'));
    if(input)input.value=value??'';
  }
  previousPrediction=null;
  $('#form-error').textContent='';
  $('#demo-results').innerHTML=`<div class="outcome-note">Loaded ${esc(activeExample.label)}. You can edit every model input.</div><div class="empty-result"><div class="empty-icon">${icon('loan')}</div><h3>Inputs are ready</h3><p>Run all four models to see their estimated charge-off probabilities.</p></div>`;
}
async function predictDemo(event){
  event.preventDefault();
  const form=event.currentTarget;
  $('#form-error').textContent='';
  const invalid=[...form.elements].find(input=>input.willValidate&&!input.validity.valid);
  if(invalid){
    const details=invalid.closest('details');if(details)details.open=true;
    invalid.reportValidity();return;
  }
  const payload={};
  for(const [key,value] of new FormData(form))payload[key]=demoFields[key]?(value===''?null:Number(value)):value;
  const button=$('#predict-button');
  button.disabled=true;button.innerHTML='<span class="spinner" style="width:14px;height:14px"></span>Running saved models…';
  const selectedExample=activeExample;
  const submittedRevision=demoRevision,submittedNavigation=navigationVersion;
  try{
    const result=await api('/api/predict',{method:'POST',body:JSON.stringify(payload)});
    if(currentRoute!=='demo'||submittedNavigation!==navigationVersion)return;
    if(submittedRevision!==demoRevision)throw new Error('Inputs changed while the models were running. Submit again to score the current inputs.');
    previousPrediction=result;
    $('#demo-results').innerHTML=(selectedExample?`<div class="outcome-note">Historical example · recorded outcome: <strong>${esc(selectedExample.recorded_outcome)}</strong></div>`:'')+
      result.results.map(row=>`<div class="risk-result"><div class="risk-heading"><span>${esc(row.model)}</span><span class="flag-badge${row.flagged?' above':''}">${row.flagged?'Meets flag threshold':'Below flag threshold'}</span></div><div class="risk-number${row.flagged?' flagged':''}">${pct(row.probability)}</div><div class="panel-desc">Estimated probability of charge-off</div><div class="risk-track"><div class="risk-fill${row.flagged?' flagged':''}" style="width:${Math.max(.5,row.probability*100)}%"></div><span class="threshold-marker" style="left:${row.threshold*100}%" title="${pct(row.threshold,1)} threshold"></span></div><div class="risk-caption"><span>0%</span><span>${pct(row.threshold,1)} threshold</span><span>100%</span></div></div>`).join('')+
      `<p class="result-explanation">${esc(result.scope)}</p>${result.warnings.length?`<div class="warnings"><strong>Input scope notes</strong><ul>${result.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul></div>`:''}<details class="definition"><summary>Review the exact 19 model inputs</summary><div class="input-review">${table(['Feature','Value'],Object.entries(result.features).map(([k,v])=>[esc(k.replaceAll('_',' ')),typeof v==='number'?fmt(v,Number.isInteger(v)?0:4):esc(v)]))}</div></details>`;
  }catch(error){if(currentRoute==='demo'&&submittedNavigation===navigationVersion)$('#form-error').textContent=error.message;}
  finally{if(currentRoute==='demo'&&submittedNavigation===navigationVersion){button.disabled=false;button.innerHTML=`${icon('loan')}Estimate charge-off risk`;}}
}

const downloadLabels={'model-reference-report':['Models & reference-paper comparison','Markdown · all models, reported paper scores and limits'],report:['Project report','PDF · full results and limitations'], 'model-results':['Model test results','CSV · fixed-model evaluation'], 'pipeline-results':['Pipeline benchmark','CSV · original five-run summary'], 'group-results':['Home-ownership audit','CSV · group counts and error rates'], 'confidence-intervals':['Confidence intervals','CSV · paired row-bootstrap analysis'],method:['Editable report source','Markdown · methodology and discussion'],references:['Research references','BibTeX · papers and dataset'], 'rerun-guide':['Reproduction guide','Markdown · commands and verification'],'paper-scores':['Paper & project scores','CSV · author-reported and recorded results'],'extension-models':['Extended model results','CSV · original models, CatBoost and ARF'],'extension-groups':['Extended group audit','CSV · original and new model group metrics'],'extension-method':['New-model method and findings','Markdown · exploratory experiment and limitations'],'study-comparison':['Research scope comparison','CSV · methods, outcomes and limitations']};

async function literaturePage(version){
  const comparison=await api('/api/literature');
  if(version!==navigationVersion)return;
  const ours=comparison.scores.find(r=>r.source==='Our project'&&r.model==='LightGBM');
  const published=comparison.scores.find(r=>r.source!=='Our project'&&r.model==='LightGBM');
  $('#view').innerHTML=heading('RELATED WORK / REPORTED OUTCOMES','Research comparison','What the reference papers report, what our project measured, and which comparisons the evidence supports.','Source-attributed comparison')+
    `<div class="callout"><strong>Reported scores are not a matched head-to-head experiment.</strong> The 2025 paper reports higher predictive scores than ours. Different cohorts, features, sampling and evaluation procedures prevent a controlled ranking.</div>`+
    `<div class="grid-two"><section class="panel">${panelHeader(esc(comparison.papers[0].title),'2017 · Paper ID / DOI: '+esc(comparison.papers[0].doi))}<div class="prose"><p><strong>What they obtained:</strong> historical summaries of loan issuance, purposes, grades and statuses.</p><ul>${comparison.papers[0].findings.map(text=>`<li>${esc(text)}</li>`).join('')}</ul><p><strong>What we add:</strong> fixed-model predictions, equivalent-feature CSV/ORC/materialization benchmarks, quantified group errors and reproducibility checks. Their paper provides no comparable classifier score or pipeline timing against which to calculate an improvement.</p></div><a class="text-link" href="https://doi.org/${comparison.papers[0].doi}" target="_blank" rel="noopener noreferrer">Paper ID / DOI: ${esc(comparison.papers[0].doi)} ${icon('arrow')}</a><p class="source-line">Evidence: ${esc(comparison.papers[0].evidence)}</p></section>`+
    `<section class="panel">${panelHeader(esc(comparison.papers[1].title),'2025 · Paper ID / DOI: '+esc(comparison.papers[1].doi))}<div class="prose"><p><strong>What they obtained:</strong> Table V reports XGBoost as their highest-scoring model, with ROC-AUC 0.8988.</p><p>Their LightGBM ROC-AUC is <strong>${fmt(published.roc_auc,4)}</strong>. Our LightGBM test ROC-AUC is <strong>${fmt(ours.roc_auc,4)}</strong>. We do not claim to beat their predictive results.</p><p><strong>What we add:</strong> a controlled Hive pipeline experiment and numeric home-ownership error-rate gaps. Our project does not implement their stated SHAP scope.</p><p>Their paper describes undersampling and a different feature set. The supplied details do not establish a matched evaluation protocol.</p></div><a class="text-link" href="https://doi.org/${comparison.papers[1].doi}" target="_blank" rel="noopener noreferrer">Paper ID / DOI: ${esc(comparison.papers[1].doi)} ${icon('arrow')}</a><p class="source-line">Evidence: ${esc(comparison.papers[1].evidence)}</p></section></div>`+
    `<section class="panel">${panelHeader('Published model scores alongside our results','Paper rows are transcribed from Table V, PDF p. 6. Our rows use the original experiment and the exploratory extension on the same 90,615-loan historical test set.')}<div class="literature-table">${table(['Study','Model','Accuracy','Recall','F1','ROC-AUC'],comparison.scores.map(r=>[esc(r.source),esc(r.model),pct(r.accuracy),pct(r.recall),fmt(r.f1,4),fmt(r.roc_auc,4)]))}</div><p class="chart-note">Thresholds: 0.15 for Logistic Regression, LightGBM and CatBoost; 0.125 for Adaptive Random Forest. Paper thresholds are not reported. This table documents reported numbers and does not establish which method wins on an identical task.</p><a class="text-link" style="margin-top:14px" href="/api/download/paper-scores">Download score comparison ${icon('download')}</a></section>`+
    `<section class="panel">${panelHeader('Study scope & implemented evidence','“Not reported” is not a measured value of zero.')}<div class="literature-table scope-table">${table(['Aspect',comparison.papers[0].title+' · DOI: '+comparison.papers[0].doi,comparison.papers[1].title+' · DOI: '+comparison.papers[1].doi,'Our project'],comparison.capabilities.map(r=>[esc(r.aspect),esc(r.paper_2017),esc(r.paper_2025),esc(r.ours)]))}</div><a class="text-link" style="margin-top:14px" href="/api/download/study-comparison">Download scope comparison ${icon('download')}</a></section>`+
    `<section class="panel">${panelHeader('How to interpret the differences','A transparent comparison includes strengths, omissions and uncertainty.')}<div class="prose"><ul>${comparison.cautions.map(text=>`<li>${esc(text)}</li>`).join('')}</ul></div><div class="inline-note"><strong>Our contribution:</strong> ${esc(comparison.contribution)}</div></section>`+
    scope(comparison.dataset_reference);
}
async function extensionPage(version){
  const extension=await api('/api/extensions');
  if(version!==navigationVersion)return;
  $('#view').innerHTML=heading('CATBOOST / ADAPTIVE RANDOM FOREST','New model experiments','A separate exploratory extension using the original 19 features and the same retrospective splits. Original experiment outputs remain unchanged.','Reused historical holdout')+
    `<div class="callout"><strong>No general performance breakthrough is established.</strong> CatBoost has a slightly higher test ROC-AUC point estimate than LightGBM, but slightly lower F1 and average precision. Adaptive Random Forest detects more charge-offs at its selected threshold while producing many more false positives.</div>`+
    `<section class="panel">${panelHeader('Test comparison: original models and new additions',`${fmt(extension.test_rows)} loans. Each threshold was selected on validation data; the test set was already used in the earlier study.`)}${table(['Model','Threshold','Accuracy','Precision','Recall','FPR','F1','ROC-AUC','Avg precision','Brier ↓'],extension.models.map(r=>[esc(r.model),fmt(r.threshold,3),pct(r.accuracy),pct(r.precision),pct(r.chargeoff_recall),pct(r.false_positive_rate),fmt(r.f1,4),fmt(r.roc_auc,4),fmt(r.average_precision,4),fmt(r.brier_score,4)]))}<a class="text-link" href="/api/download/extension-models">Download extended model results ${icon('download')}</a></section>`+
    `<div class="grid-two"><section class="panel">${panelHeader('CatBoost','Native handling of categorical inputs')}<div class="prose"><p>Trained with 1,500 maximum iterations, depth 6, learning rate 0.04 and seed 42. Validation early stopping retained <strong>605 trees</strong>. The selected threshold is <strong>0.15</strong>.</p><p>The website uses CatBoost’s official standalone Python export, checked against native validation predictions. It retains the fitted categorical transformations and does not retrain during inference.</p></div></section><section class="panel">${panelHeader('Adaptive Random Forest','River · ten online trees with ADWIN detectors')}<div class="prose"><p>Training rows are ordered by issue month and numeric loan ID. The model learns <strong>training rows only</strong> and remains frozen during validation, test evaluation and website inference. The selected threshold is <strong>0.125</strong>.</p><p>This is a retrospective holdout comparison. It does not demonstrate live drift adaptation or realistic delayed loan-label arrival.</p></div></section></div>`+
    `<section class="panel">${panelHeader('Validation selection and local timings','One preset configuration and seed per addition. Timings are single runs, not repeated pipeline benchmarks.')}${table(['Model','Validation ROC-AUC','Validation F1','Threshold'],extension.validation.map(r=>[esc(r.model),fmt(r.roc_auc,4),fmt(r.f1,4),fmt(r.threshold,3)]))}${table(['Model','Training time','Native test prediction time'],extension.settings.map(r=>[esc(r.model),`${fmt(r.fit_seconds,2)} s`,`${fmt(extension.prediction_seconds[r.model],2)} s`]))}</section>`+
    `<section class="panel">${panelHeader('Home-ownership group gaps','Maximum minus minimum across MORTGAGE, RENT and OWN. OTHER_UNKNOWN is reported separately.')}${table(['Model','FPR gap','Recall gap','Equalized-odds difference'],extension.gaps.map(r=>[esc(r.model),`${fmt(r.false_positive_rate_gap*100,2)} pp`,`${fmt(r.chargeoff_recall_gap*100,2)} pp`,fmt(r.equalized_odds_difference,4)]))}<a class="text-link" href="/api/download/extension-groups">Download group-level results ${icon('download')}</a></section>`+
    `<section class="panel">${panelHeader('What this experiment can and cannot establish','Adding established algorithms alone is not a novelty claim.')}<div class="prose"><ul>${extension.limitations.map(note=>`<li>${esc(note)}</li>`).join('')}</ul></div><a class="text-link" href="/api/download/extension-method">Download extension method and findings ${icon('download')}</a></section>`+
    `<section class="panel">${panelHeader('Try all four predictive models','The loan form uses the same inputs for every model.')}<a class="button" href="#demo">Open loan risk demo ${icon('arrow')}</a></section>`;
}

async function reportsPage(version){
  const downloads=await api('/api/downloads');
  if(version!==navigationVersion)return;
  $('#view').innerHTML=heading('METHOD / EVIDENCE / DOWNLOADS','Reports & research method','Follow the experiment from public loan records to equivalent Hive pipelines, saved predictions and an explicit group audit.')+
  `<div class="download-grid" style="margin-bottom:24px">${downloads.map(item=>{const [title,sub]=downloadLabels[item.id];return `<${item.available?'a':'div'} ${item.available?`href="/api/download/${item.id}"`:''} class="download-item${item.available?'':' unavailable'}"><span class="download-icon">${icon(item.id==='report'?'file':'download')}</span><span><strong>${esc(title)}</strong><small>${esc(sub)}${item.available?'':' · file unavailable'}</small></span>${icon('download')}</${item.available?'a':'div'}>`;}).join('')}</div>`+
  `<section class="panel">${panelHeader('What this project investigates','A Reproducible Benchmark of Credit Risk Pipelines: A Hive Study')}<div class="prose"><p>We compare how <strong>CSV, raw ORC and prepared ORC</strong> support repeated exports of identical credit-risk features. Separately, Logistic Regression and LightGBM estimate whether loans will be fully paid or charged off. We examine prediction errors across home-ownership groups.</p><p>The main Big Data Management contribution is the controlled pipeline comparison. Storage changes do not receive credit for improvements in model accuracy.</p></div><div class="pipeline-process"><div><span class="step-number">DATA PREPARATION</span><h3>Python audit & cohort</h3><p>Public accepted-loan records; 306,462 resolved, 36-month loans from 2012–2014.</p></div><div><span class="step-number">BIG DATA PROCESSING</span><h3>HDFS, Hive & YARN/Tez</h3><p>Shared SQL feature definitions, three stored representations and full-row equivalence checks.</p></div><div><span class="step-number">MODELLING & AUDIT</span><h3>Python model pipelines</h3><p>Fixed preprocessing and trained models, test evaluation and group-error comparisons.</p></div></div></section>`+
  `<div class="grid-two"><section class="panel">${panelHeader('Dataset & retrospective splits','Target 1 = Charged Off. Target 0 = Fully Paid.')}${table(['Split','Loan issue dates','Records'],[['Train','2012–2013',fmt(data.cohort.splits.train)],['Validation','Jan–Jun 2014',fmt(data.cohort.splits.validation)],['Test','Jul–Dec 2014',fmt(data.cohort.splits.test)]])}<p class="chart-note">The original accepted-loan file had 2,260,701 rows and 151 columns, including 33 summary/footer records. Rejected applications and unresolved loans are outside this modelling cohort.</p></section><section class="panel">${panelHeader('Verified reproducibility','The original experiment artifacts stay unchanged.')}<ul class="check-list">${['Frozen file fingerprints and split-ID checks','Three complete-row Hive equivalence checks','Recomputed training-only imputation statistics','Isolated feature replay matches original values','Original-order model replay matches test metrics exactly','Standalone benchmark and resource scripts checked'].map(text=>`<li>${icon('check')}<span>${esc(text)}</span></li>`).join('')}</ul></section></div>`+
  `<section class="panel">${panelHeader('Model input features','19 inputs. Tracking IDs, split labels and targets are excluded.')}<div class="feature-list">${data.cohort.features.map(f=>`<span>${esc(f.replaceAll('_',' '))}</span>`).join('')}</div>${definition('How are features prepared?','Hive converts numeric/date values, derives FICO midpoint and credit-history months, groups rare home-ownership values and uses training-only fills for missing employment/utilization. Missingness flags are retained. Each saved model includes its fitted scaling and categorical encoding.')}</section>`+
  `<section class="panel">${panelHeader('Limitations that matter','The findings apply to this experiment.')}<div class="prose"><ul><li><strong>Retrospective split:</strong> training loan outcomes would not all have been known at validation/test origination. This is not an established prospective lending simulation.</li><li><strong>Scale:</strong> one host and a roughly 50 MB cohort CSV, not a demonstration of large-cluster scalability.</li><li><strong>Scope:</strong> accepted, resolved 36-month loans from an older period; current borrowers can differ.</li><li><strong>Timing:</strong> complete export time, with no controlled OS/JVM cold-cache reset. Preparation costs were measured separately.</li><li><strong>Group audit:</strong> home ownership is an input and a socioeconomic grouping; no protected-demographic or causal fairness conclusion follows.</li><li><strong>Uncertainty:</strong> pointwise intervals assume independent loan rows and fixed models; repeated borrowers and time dependence are not modeled.</li><li><strong>Demonstration:</strong> no SHAP explanation, mitigation, live cluster execution, approval engine or monetary cloud-cost measurement is claimed.</li></ul></div></section>`+
  `<section class="panel">${panelHeader('Research references','Background and modelling context; paper scores are not directly comparable to this cohort.')}<div class="reference"><small>ARCHITECTURAL BACKGROUND · 2017</small><strong>Bank loan analysis using customer usage data: A big data approach using Hadoop</strong><a href="https://doi.org/10.1109/TEL-NET.2017.8343582" target="_blank" rel="noopener noreferrer">IEEE TEL-NET · Paper ID / DOI: 10.1109/TEL-NET.2017.8343582</a></div><div class="reference"><small>MODELLING & FAIRNESS CONTEXT · 2025</small><strong>Assessing Fairness and Transparency in Credit Scoring Using Explainable AI</strong><a href="https://doi.org/10.1109/CISCON66933.2025.11337606" target="_blank" rel="noopener noreferrer">IEEE CISCON · Paper ID / DOI: 10.1109/CISCON66933.2025.11337606</a></div><div class="reference"><small>PUBLIC DATA SOURCE</small><strong>Lending Club accepted-loan dataset</strong><a href="https://www.kaggle.com/datasets/wordsforthewise/lending-club" target="_blank" rel="noopener noreferrer">Kaggle · wordsforthewise/lending-club</a></div></section>`;
}

async function navigate(){
  const page=location.hash.slice(1)||'overview';
  const route=Object.hasOwn(pageNames,page)?page:'overview';
  currentRoute=route;
  const version=++navigationVersion;
  document.title=`${pageNames[route]} · Credit Risk Lab`;
  $('#crumb').textContent=pageNames[route];
  document.querySelectorAll('nav a').forEach(link=>{
    const selected=link.dataset.page===route;
    link.classList.toggle('active',selected);
    if(selected)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  });
  $('#sidebar').classList.remove('open');$('#menu-toggle').setAttribute('aria-expanded','false');
  document.querySelectorAll('.js-plotly-plot').forEach(node=>window.Plotly?.purge(node));
  $('#view').innerHTML='<div class="loading"><span class="spinner"></span>Loading research artifacts…</div>';
  window.scrollTo(0,0);
  try{
    data=data||await api('/api/research');
    if(version!==navigationVersion)return;
    if(route==='architecture'){
      $('#view').innerHTML=window.CreditArchitecture.render(data,{esc,icon,heading,panelHeader,scope});
      window.CreditArchitecture.mount();return;
    }
    if(route==='demo'){await demoPage(version);return;}
    if(route==='reports'){await reportsPage(version);return;}
    if(route==='literature'){await literaturePage(version);return;}
    if(route==='extensions'){await extensionPage(version);return;}
    if(route==='models'){await modelComparisonPage(version);return;}
    $('#view').innerHTML=({overview,pipelines,fairness}[route])();
    if(route==='overview'){horizontalPipelines('overview-pipeline-chart','time','s');gapChart('overview-gap-chart');}
    if(route==='pipelines'){horizontalPipelines('pipeline-latency','time','s');horizontalPipelines('pipeline-storage','storage','MB');}
    if(route==='fairness'){drawAudit();gapChart('fairness-gap');$('#audit-model').addEventListener('change',drawAudit);}

  }catch(error){
    if(version!==navigationVersion)return;
    $('#view').innerHTML=`<section class="error-state"><div class="page-eyebrow">LOCAL ARTIFACT CHECK</div><h2>We couldn’t load this view</h2><p>${esc(error.message)}</p><p>Keep the Python server running and restore any missing project files. This application does not substitute example metrics.</p><button class="button" id="retry-view">Retry this page</button></section>`;
    $('#retry-view').addEventListener('click',navigate);
  }
}
$('#menu-toggle').addEventListener('click',()=>{
  const open=$('#sidebar').classList.toggle('open');$('#menu-toggle').setAttribute('aria-expanded',String(open));
});
document.addEventListener('click',event=>{
  if(window.innerWidth<=650&&!event.target.closest('#sidebar')&&!event.target.closest('#menu-toggle')){
    $('#sidebar').classList.remove('open');$('#menu-toggle').setAttribute('aria-expanded','false');
  }
});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){$('#sidebar').classList.remove('open');$('#menu-toggle').setAttribute('aria-expanded','false');}});
window.addEventListener('hashchange',navigate);
$('.skip-link').addEventListener('click',event=>{event.preventDefault();$('#main').focus();});
navigate();
