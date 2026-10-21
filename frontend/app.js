let data;
let requestVersion=0, compatibilityVersion=0;
async function api(path, params={}) {
  const response=await fetch(path+'?'+new URLSearchParams(params));
  const payload=await response.json();
  if(!response.ok)throw new Error(payload.message||'Request failed.');
  return payload;
}
const $=id=>document.getElementById(id);
let selected=null;
const {displayValue, visibleGroups}=BlindfastenerDisplay;
function options(id,values,label){
  const el=$(id);el.replaceChildren(new Option(label,''));
  [...new Set(values.filter(v=>v!==null&&v!==''))].sort((a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true})).forEach(v=>el.add(new Option(String(v),String(v))));
}
function clearResults(){requestVersion++;compatibilityVersion++;selected=null;$('details').hidden=true;$('matches').replaceChildren();$('search-status').textContent='';$('search-status').className='';$('galvanic-result').replaceChildren();$('pair-result').replaceChildren();$('pair-result').hidden=true;}
$('search-form').addEventListener('input',clearResults);
$('search-form').addEventListener('change',clearResults);
function renderGroups(row){
  const container=$('result-groups');container.replaceChildren();
  for(const group of visibleGroups(row,data.groups,data.labels)){
    const section=document.createElement('section');section.className='group '+group.theme;
    const head=document.createElement('div');head.className='grouphead';
    const title=document.createElement('h3');title.textContent=group.title;
    const pill=document.createElement('span');pill.className='pill';pill.textContent='Columns '+group.columns;
    head.append(title,pill);section.append(head);
    const fieldRows=group.id==='materials'?group.rows:[group.fields];
    for(const fields of fieldRows){
      const list=document.createElement('dl');
      list.className=group.layout==='rows'?'fields field-rows':'fields';
      if(group.id==='materials')list.classList.add('component-fields');
      for(const field of fields){
        const item=document.createElement('div');item.className='datum';
        const key=document.createElement('dt');key.textContent=field.label;
        const value=document.createElement('dd');value.textContent=field.value;
        item.append(key,value);list.append(item);
      }
      section.append(list);
    }
    container.append(section);
  }
}
function selectRecord(row){
  compatibilityVersion++;selected=row;$('details').hidden=false;$('detail-title').textContent=row[0];$('detail-meta').textContent=[displayValue(row[1]),displayValue(row[2])?'Revision: '+displayValue(row[2]):''].filter(Boolean).join(' · ');
  renderGroups(row);
  resetSubstrates();
  for(const b of $('matches').children)b.setAttribute('aria-pressed',String(b.dataset.part===String(row[0])));
}
$('search-form').onsubmit=async e=>{
  e.preventDefault();clearResults();
  const version=requestVersion;
  $('search-status').className='notice';$('search-status').textContent='Searching…';
  try {
  const {records:found}=await api('/api/fasteners',{part:$('part').value});
  if(version!==requestVersion)return;
  $('search-status').className='notice';$('search-status').textContent=found.length===0?'No matching fastener found. Check your inputs and try again.':found.length===1?'1 matching record found.':found.length+' matching records found. Select a fastener to view its details.';
  if(found.length===1)selectRecord(found[0]);
  else for(const row of found){const b=document.createElement('button');b.type='button';b.className='match';b.dataset.part=row[0];b.setAttribute('aria-pressed','false');const name=document.createElement('span');name.textContent=row[0];const desc=document.createElement('small');desc.textContent=[displayValue(row[1]),displayValue(row[2])?'Revision: '+displayValue(row[2]):''].filter(Boolean).join(' · ');b.append(name,desc);b.onclick=()=>selectRecord(row);$('matches').append(b);}
  }catch(error){if(version===requestVersion)$('search-status').textContent=error.message;}
};

function invalidateCompatibility(){compatibilityVersion++;$('galvanic-result').replaceChildren();$('pair-result').replaceChildren();$('pair-result').hidden=true;}
let substrateCounter=0;
function updateSubstrateCount(){
  const rows=[...$('substrate-rows').children];
  $('add-substrate').disabled=rows.length>=5;
  $('substrate-count').textContent=rows.length+' / 5 substrates';
  rows.forEach((row,index)=>{row.querySelector('legend').textContent='Substrate '+(index+1);row.querySelector('.remove-substrate').disabled=rows.length===1;});
}
function addSubstrate(){
  if($('substrate-rows').children.length>=5)return;
  invalidateCompatibility();
  const row=document.createElement('fieldset');row.className='substrate-row';
  const legend=document.createElement('legend');row.append(legend);
  const fields=document.createElement('div');fields.className='substrate-inputs';
  const id=++substrateCounter;
  for(const [key,label,values] of [['material','Substrate material',data.substrates],['finish','Substrate finish',data.substrateFinishes]]){
    const wrapper=document.createElement('div');wrapper.className='field';
    const text=document.createElement('label');text.htmlFor='substrate-'+id+'-'+key;text.textContent=label;
    const select=document.createElement('select');select.id=text.htmlFor;select.dataset.key=key;select.required=true;
    wrapper.append(text,select);fields.append(wrapper);row.append(fields);$('substrate-rows').append(row);
    options(select.id,values,'Select '+label.toLowerCase());
  }
  const checkLabel=document.createElement('label');checkLabel.className='side-check';
  const check=document.createElement('input');check.type='checkbox';check.dataset.key='nutSide';
  checkLabel.append(check,document.createTextNode('Nut or washer side'));fields.append(checkLabel);
  const remove=document.createElement('button');remove.type='button';remove.className='remove-substrate';remove.textContent='Remove';
  remove.onclick=()=>{if($('substrate-rows').children.length>1){row.remove();invalidateCompatibility();updateSubstrateCount();}};
  fields.append(remove);updateSubstrateCount();
}
function resetSubstrates(){
  $('substrate-rows').replaceChildren();$('compatibility-mode').value='no';
  $('mode-notice').textContent='';addSubstrate();
}
$('add-substrate').onclick=addSubstrate;
$('galvanic-form').addEventListener('change',()=>{
  invalidateCompatibility();$('mode-notice').textContent='';
});
$('galvanic-form').onsubmit=async e=>{
  e.preventDefault();if(!selected)return;
  invalidateCompatibility();
  const version=++compatibilityVersion,el=$('galvanic-result');el.className='notice compatibility-results';el.textContent='Checking…';
  const substrates=[...$('substrate-rows').children].map(row=>({
    material:row.querySelector('[data-key="material"]').value,
    finish:row.querySelector('[data-key="finish"]').value,
    nutSide:row.querySelector('[data-key="nutSide"]').checked
  }));
  try{
    const response=await fetch('/api/compatibility',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({part:selected[0],mode:$('compatibility-mode').value,substrates})});
    const result=await response.json();if(!response.ok)throw new Error(result.message||'Compatibility request failed.');
    if(version!==compatibilityVersion)return;el.replaceChildren();
    if(result.status!=='complete'){el.textContent=result.message;return;}
    const heading=document.createElement('h3');heading.textContent='Compatibility results';el.append(heading);
    const table=document.createElement('table'),head=document.createElement('thead'),header=document.createElement('tr');
    for(const label of ['Substrate','Component','Fastener material','Fastener finish','Substrate material','Substrate finish','Compatibility','Comments']){const cell=document.createElement('th');cell.scope='col';cell.textContent=label;header.append(cell);}
    head.append(header);table.append(head);const body=document.createElement('tbody');
    for(const item of result.results){
      const row=document.createElement('tr');
      const finish=item.substrateFinish+(item.substrateFinishUsed?'':' (not used in lookup)');
      for(const value of [item.substrateIndex,item.component,item.material,item.finish,item.substrate,finish,item.result,item.comments.join('; ')]){
        const cell=document.createElement('td');cell.textContent=value==null?'':String(value);row.append(cell);
      }
      body.append(row);
    }
    table.append(body);const scroll=document.createElement('div');scroll.className='compat-table-scroll';scroll.append(table);el.append(scroll);
    if(result.pairResult){
      const pair=result.pairResult,container=$('pair-result');container.hidden=false;
      const title=document.createElement('h3');title.textContent='Bolt–nut compatibility';container.append(title);
      const pairTable=document.createElement('table'),thead=document.createElement('thead'),tr=document.createElement('tr');
      for(const label of ['Bolt material','Bolt finish','Nut material','Nut finish','Compatibility','Comments']){
        const cell=document.createElement('th');cell.scope='col';cell.textContent=label;tr.append(cell);
      }
      thead.append(tr);pairTable.append(thead);const tbody=document.createElement('tbody'),values=document.createElement('tr');
      for(const value of [...pair.values,pair.result,pair.comments.join('; ')]){
        const cell=document.createElement('td');cell.textContent=value==null?'':String(value);values.append(cell);
      }
      tbody.append(values);pairTable.append(tbody);
      const wrapper=document.createElement('div');wrapper.className='compat-table-scroll';wrapper.append(pairTable);container.append(wrapper);
    }
  }catch(error){if(version===compatibilityVersion)el.textContent=error.message;}
};
async function initialize(){
  const buttons=document.querySelectorAll('button');
  buttons.forEach(b=>b.disabled=true);
  $('search-status').className='notice';$('search-status').textContent='Connecting to database…';
  try{
    data=await api('/api/metadata');
    $('record-count').textContent=data.count.toLocaleString()+' fasteners';
    options('part',data.partNumbers,'Select a part number');
    $('part').disabled=false;

    buttons.forEach(b=>b.disabled=false);clearResults();
  }catch(error){$('search-status').textContent='Could not connect to the backend. Start the server and reload this page. '+error.message;}
}
initialize();
