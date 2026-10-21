(function(root){
  function missing(value){return value===null||value===undefined||(typeof value==='string'&&value.trim()==='');}
  function displayValue(value){return missing(value)?'':String(value);}
  function visibleGroups(row,groups,labels){
    return groups.map(group=>{
      const fields=Array.from({length:group.end-group.start+1},(_,offset)=>{
        const index=group.start+offset;
        return {index,label:labels[index],value:displayValue(row[index]),missing:missing(row[index])};
      }).filter(field=>!field.missing);
      const rows=[];
      if(group.id==='materials'){
        for(let start=group.start;start<=group.end;start+=3){
          const component=fields.filter(field=>field.index>=start&&field.index<start+3);
          if(component.length)rows.push(component);
        }
      }
      return {...group,fields,rows};
    }).filter(group=>group.fields.length);
  }
  const api={missing,displayValue,visibleGroups};
  if(typeof module!=='undefined')module.exports=api;
  root.BlindfastenerDisplay=api;
})(globalThis);
