'use strict';

function formatSelection(value, start, end, action, option='') {
  const selected=value.slice(start,end);
  const replace=(from,to,text,a=0,b=text.length)=>({value:value.slice(0,from)+text+value.slice(to),start:from+a,end:from+b,from,to,text});
  const marks={bold:'**',italic:'*',strike:'~~',code:'`'};
  if(marks[action]){
    const mark=marks[action];
    if(start>=mark.length&&value.slice(start-mark.length,start)===mark&&value.slice(end,end+mark.length)===mark)
      return replace(start-mark.length,end+mark.length,selected);
    if(selected.startsWith(mark)&&selected.endsWith(mark)&&selected.length>=mark.length*2)
      return replace(start,end,selected.slice(mark.length,-mark.length));
    const text=selected||'文字';return replace(start,end,mark+text+mark,mark.length,mark.length+text.length);
  }
  if(action==='link')return replace(start,end,'['+(selected||'链接文字')+']('+option+')',1,1+(selected||'链接文字').length);
  if(action==='rule')return replace(start,end,'\n\n---\n\n');
  if(action==='table')return replace(start,end,'\n\n| 列一 | 列二 |\n| --- | --- |\n| 内容 | 内容 |\n\n');
  if(action==='block'){
    const content=selected||'代码';const fence='`'.repeat(Math.max(3,...[...content.matchAll(/`+/g)].map(m=>m[0].length+1)));
    const prefix='\n\n'+fence+'\n';return replace(start,end,prefix+content+'\n'+fence+'\n\n',prefix.length,prefix.length+content.length);
  }
  const from=start===0?0:value.lastIndexOf('\n',start-1)+1;
  const last=end>start&&value[end-1]==='\n'?end-1:end;
  const next=value.indexOf('\n',last),to=next<0?value.length:next;
  const lines=value.slice(from,to).split('\n');
  if(action==='heading')return replace(from,to,lines.map(line=>line.replace(/^#{1,6}\s+/, '')).map(line=>option?'#'.repeat(Number(option))+' '+line:line).join('\n'));
  if(lines.length===1&&!lines[0].trim())return replace(from,to,action==='quote'?'> ':action==='ordered'?'1. ':'- ');
  const pattern=action==='quote'?/^> ?/:action==='ordered'?/^\d+\.\s+/:/^[-*+]\s+/;
  const remove=lines.filter(line=>line.trim()).every(line=>pattern.test(line));
  return replace(from,to,lines.map((line,i)=>!line.trim()?line:remove?line.replace(pattern,''):(action==='quote'?'> ':action==='ordered'?(i+1)+'. ':'- ')+line.replace(action==='quote'?/^> ?/:/^(?:[-*+]|\d+\.)\s+/, '')).join('\n'));
}

if(typeof module!=='undefined')module.exports={formatSelection};
