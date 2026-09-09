'use strict';
const $ = id => document.getElementById(id);
const state = {token:'', records:[], drafts:[], doc:null, dirty:false, raw:false, group:'home', width:1440, previewURL:'', files:[], selected:new Set(), proof:null};
const groups = [['home','首页编排','⌂'],['topics','研究课题','◇'],['articles','原创文章','文'],['resources','精选资料','▤'],['tools','兵器谱','⚒'],['about','关于我们','人'],['global','导航与页脚','☷'],['pages','栏目页面','▣'],['media','素材库','▧'],['operations','资讯与留言','◎'],['release','发布中心','↗']];
const labels = {hero:'首页首屏',title:'标题',eyebrow:'栏目标识',purpose:'主张',description:'介绍',art:'侠客图片',alt:'图片描述',feather:'边缘羽化',height:'首屏高度',author:'作者',role:'身份',action_title:'入口文字',action_url:'入口链接',sections:'首页板块',key:'标识',visible:'显示',focus:'重点研究',topic:'关联课题',evidence:'研究方法',summary:'摘要',article:'文章链接',image:'图片',routes:'问题入口',label:'名称',question:'问题',url:'链接',featured_resources:'首页精选资料',brand:'站点名称',logo:'标志',tagline:'页脚介绍',copyright:'版权所有者',navigation:'导航与栏目',english:'英文标识',nav_title:'导航简称',footer_links:'页脚快捷入口',modal:'弹窗标识',paragraphs:'个人介绍',team_title:'团队名称',team_description:'团队介绍',research_links:'研究入口',contacts:'联系方式',glyph:'标记',categories:'分类',items:'工具条目',name:'名称',sub:'一句话介绍',cat:'所属门类',rank:'分级',access:'访问门槛',tags:'标签',desc:'说明',subtitle:'副标题',abstract:'导语摘要',keyword:'公众号关键词',cover:'封面',published:'公开状态 / 发布日期',date:'首次日期',updated:'修订日期',status:'研究状态',layout:'页面模板',permalink:'页面地址',body_class:'页面样式',source:'来源',type:'类型',topics:'关联课题',external_url:'原文链接',reason:'推荐理由',dao:'道 · 原理',fa:'法 · 方法',shu:'术 · 实践',qi:'器 · 资料与工具',dao_summary:'道 · 概述',fa_summary:'法 · 概述',shu_summary:'术 · 概述',qi_summary:'器 · 概述',text:'正文说明',platform:'平台',form:'内容形态',publication:'文章或工具成果发布',stars:'推荐级别',links:'成果入口',changelog:'维护记录',action:'维护动作',findings:'研究结论',reading_paths:'阅读路径',assets:'附件',reading_time:'阅读分钟',toc:'目录',id:'锚点',children:'子条目',anchor:'锚点',kind:'类别',note:'备注',highlight:'重点',owner:'负责人',version:'版本'};
const templates = {sections:{key:'',title:'',visible:true},routes:{label:'',question:'',description:'',url:''},footer_links:{title:'',url:'',modal:''},contacts:{title:'',description:'',url:'',modal:'',glyph:''},research_links:{title:'',url:''},items:{name:'',sub:'',url:'',cat:'cyberspace',rank:'b',access:'',tags:[],desc:''},links:{title:'',platform:'官网',form:'',url:'',note:''},changelog:{date:new Date().toISOString().slice(0,10),action:''},dao:{title:'',text:'',url:'',publication:false,type:'原创',platform:''},fa:{title:'',text:'',url:'',publication:false,type:'原创',platform:''},shu:{title:'',text:'',url:'',publication:false,type:'原创',platform:''},qi:{title:'',text:'',url:'',publication:false,type:'转载',platform:''},findings:{title:'',text:''},assets:{title:'',url:'',desc:''}};
function el(tag, props={}, ...children){const node=document.createElement(tag);for(const [k,v] of Object.entries(props)){if(k==='class')node.className=v;else if(k.startsWith('on'))node.addEventListener(k.slice(2),v);else if(k==='text')node.textContent=v;else node.setAttribute(k,v);}for(const c of children)if(c!=null)node.append(c instanceof Node?c:document.createTextNode(c));return node;}
function button(text,fn,cls=''){return el('button',{type:'button',class:cls,onclick:fn},text);}
function toast(message,error=false){$('toast').textContent=message;$('toast').className=error?'error':'';$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,error?9000:4500);}
async function api(path,data){const response=await fetch('/api/admin/'+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':state.token},body:JSON.stringify(data)});const result=await response.json();if(!response.ok||result.error)throw Error(result.error||'请求失败');return result;}
async function job(path,data){const {job:id}=await api(path,data);for(;;){await new Promise(r=>setTimeout(r,700));const j=await api('job/'+id);if(j.status==='failed')throw Error(j.error);if(j.status==='complete'){if(j.result?.ok===false)throw Error(j.result.error||'操作未完成');return j.result;}}}
async function busy(fn){if(state.busy)return;state.busy=true;document.querySelectorAll('#doc-actions button').forEach(b=>b.disabled=true);for(const id of ['navigation','workspace'])$(id).inert=true;try{return await fn();}catch(error){toast(error.message,true);}finally{state.busy=false;for(const id of ['navigation','workspace'])$(id).inert=false;document.querySelectorAll('#doc-actions button').forEach(b=>b.disabled=false);}}
function dirty(){state.dirty=true;$('save-state').textContent='有未保存修改';$('draft-badge').textContent='编辑中';scheduleLivePreview();}
let previewTimer, previewRunning=false, previewGeneration=0;
function scheduleLivePreview(){clearTimeout(previewTimer);previewGeneration++;if(state.group==='articles'&&state.doc?.record.group==='articles')previewTimer=setTimeout(livePreview,600);}
async function livePreview(){
  if(previewRunning){previewTimer=setTimeout(livePreview,300);return;}
  if(state.group!=='articles'||!state.doc)return;
  const doc=state.doc,generation=previewGeneration;
  try{
    syncRaw();previewRunning=true;
    const result=await job('live-preview',structuredClone({id:doc.id,meta:doc.meta,body:doc.body}));
    if(state.doc!==doc||state.group!=='articles'||generation!==previewGeneration)return;
    const url=result.url+doc.record.url+'?v='+Date.now();
    $('preview-frame').src=url;$('open-preview').href=url;$('preview-empty').hidden=true;$('preview-viewport').hidden=false;resizePreview();
  }catch(e){if(state.doc===doc&&generation===previewGeneration)toast('预览未更新：'+e.message,true);}
  finally{previewRunning=false;}
}
async function uploadImage(file){
  const response=await fetch('/api/admin/upload',{method:'POST',headers:{'X-Admin-Token':state.token,'Content-Type':'application/octet-stream'},body:file});
  const data=await response.json();if(!response.ok)throw Error(data.error||'图片上传失败');return data.url;
}
document.addEventListener('paste',async event=>{
  const body=event.target;if(!body.matches('.body-editor'))return;
  const files=[...(event.clipboardData?.items||[])].filter(item=>item.kind==='file'&&item.type.startsWith('image/')).map(item=>item.getAsFile()).filter(Boolean);
  if(!files.length)return;event.preventDefault();
  const doc=state.doc;
  for(const file of files){
    const marker='<!-- image-upload-'+crypto.randomUUID()+' -->';
    body.setRangeText('\n'+marker+'\n',body.selectionStart,body.selectionEnd,'end');doc.body=body.value;dirty();
    try{
      const url=await uploadImage(file);
      // Resolve the placeholder in the latest text so typing during upload is preserved.
      if(!body.isConnected||state.doc!==doc){toast('图片已上传到素材库，原编辑窗口已切换');continue;}
      body.value=body.value.replace(marker,'![图片]('+url+')');doc.body=body.value;dirty();
    }catch(e){if(body.isConnected&&state.doc===doc){body.value=body.value.replace(marker,'');doc.body=body.value;dirty();}toast(e.message,true);}
  }
});
function modal(title,content){$('modal-title').textContent=title;$('modal-body').replaceChildren(content);$('modal').showModal();}
function confirmAction(title,description,action){const box=el('div',{},el('p',{class:'muted'},description));const yes=button('确认',async()=>{yes.disabled=true;try{await action();$('modal').close();}catch(e){toast(e.message,true);yes.disabled=false;}},'primary');box.append(el('div',{class:'release-actions'},button('取消',()=>$('modal').close()),yes));modal(title,box);}
async function refresh(){const b=await api('bootstrap');Object.assign(state,{token:b.token,records:b.records,drafts:b.drafts,previewURL:b.preview_url});}
function nav(){const root=$('navigation');root.replaceChildren();for(const [key,title,icon]of groups)root.append(el('a',{href:'#'+key,class:state.group===key?'active':''},el('span',{class:'nav-icon'},icon),title));}
function renderRecords(){const query=$('search').value.toLowerCase();const records=state.records.filter(r=>r.group===state.group&&(r.title+' '+r.id).toLowerCase().includes(query));$('records').replaceChildren(...records.map(r=>{const b=button('',()=>select(r.id),'record'+(state.doc?.id===r.id?' active':''));b.append(el('span',{},r.title),el('small',{},r.id+(state.drafts.includes(r.id)?' · 草稿':'')));return b;}));$('new').hidden=!['topics','articles','resources'].includes(state.group);}
async function select(id){if(state.dirty){confirmAction('切换内容','当前修改尚未保存。确认后放弃编辑器内的修改。',async()=>{state.dirty=false;await load(id);});return;}await load(id);}
let documentLoadGeneration=0;
async function load(id){const generation=++documentLoadGeneration;clearTimeout(previewTimer);previewGeneration++;try{const doc=await api('document/'+id);if(generation!==documentLoadGeneration)return;state.doc=doc;$('delete-draft').hidden=!doc.deletable;try{localStorage.setItem('eastsword-admin-selected-'+state.group,id);}catch{}history.replaceState(null,'','#'+state.group+'?doc='+encodeURIComponent(id));state.dirty=false;state.raw=false;$('page-title').textContent=state.doc.meta.title||state.doc.record.title;$('save-state').textContent=state.doc.conflict?'磁盘已更新，存在冲突':state.doc.draft?'草稿已保存':'与磁盘一致';$('draft-badge').textContent=state.doc.draft?'草稿':'';$('preview-frame').src='about:blank';$('preview-viewport').hidden=true;$('preview-empty').hidden=false;$('open-preview').removeAttribute('href');$('full-preview').hidden=true;renderRecords();renderForm();scheduleLivePreview();}catch(e){toast(e.message,true);}}
function options(key,parent){if(key==='status')return ['研讨中','已结题','待研究'];if(key==='rank')return [['s','天 · 必备主力'],['a','地 · 场景利器'],['b','玄 · 备选兵器']];if(key==='topic')return [['','未关联'],...state.records.filter(r=>r.group==='topics').map(r=>[r.id.split('/')[1],r.title])];if(key==='type'&&'publication'in parent)return ['原创','转载'];if(key==='modal')return [['','无弹窗'],['modal-wechat','团队微信'],['modal-sph','视频号'],['modal-gzh','公众号']];return null;}
function field(key,value,parent,path){const name=labels[key]||key;const box=el('div',{class:'field'});if(typeof value==='object'&&value!==null){const detail=el('details',{class:'group',open:''},el('summary',{},name));const inner=el('div',{class:'group-content'});if(Array.isArray(value)){
    value.forEach((item,index)=>{const entry=el('details',{class:'array-item'});const summary=el('summary',{},el('span',{class:'array-title'},String(index+1).padStart(2,'0')+' · '+(typeof item==='object'?(item.title||item.name||item.label||item.action||'条目'):String(item).slice(0,45))));
    const move=(delta,event)=>{event.preventDefault();if(index+delta<0||index+delta>=value.length)return;[value[index],value[index+delta]]=[value[index+delta],value[index]];dirty();renderForm();};
    const up=button('↑',e=>move(-1,e),'icon');up.title='上移';up.disabled=index===0;const down=button('↓',e=>move(1,e),'icon');down.title='下移';down.disabled=index===value.length-1;
    const remove=button('×',e=>{e.preventDefault();value.splice(index,1);dirty();renderForm();},'icon');remove.title='移除此条目';summary.append(up,down,remove);entry.append(summary);
    const content=el('div',{class:'group-content'});if(item&&typeof item==='object')objectFields(item,content,path+'.'+index);else{const input=el('textarea',{rows:'2','aria-label':name+' '+(index+1)});input.value=String(item);input.oninput=()=>{value[index]=input.value;dirty();};content.append(input);}entry.append(content);inner.append(entry);});
    if(key!=='navigation'&&key!=='sections')inner.append(button('＋ 添加',()=>{let item=templates[key];if(!item&&value.length&&typeof value[0]==='object')item=Object.fromEntries(Object.entries(value[0]).map(([k,v])=>[k,typeof v==='boolean'?false:Array.isArray(v)?[]:typeof v==='number'?0:'']));value.push(item?structuredClone(item):'');dirty();renderForm();},'array-add'));
  }else{objectFields(value,inner,path);if(key==='categories'&&state.group==='tools')inner.append(button('＋ 新增门类',()=>{const input=el('input',{'aria-label':'门类标识',placeholder:'英文标识'});const text=el('input',{'aria-label':'门类名称',placeholder:'门类名称'});modal('新增门类',el('div',{},input,text,button('添加',()=>{if(!/^[a-z][a-z0-9_]*$/.test(input.value)||!text.value)return toast('请填写有效标识和名称',true);value[input.value]=text.value;dirty();renderForm();$('modal').close();},'primary')));}));}detail.append(inner);return detail;}
  box.append(el('span',{},name));
  if(typeof value==='boolean'){const input=el('input',{type:'checkbox','aria-label':name});input.checked=value;input.onchange=()=>{parent[key]=input.checked;dirty();if(key==='publication')renderForm();};box.append(el('label',{},input,value?'已开启':'未开启'));return box;}
  if(key==='feather'||key==='height'){const [min,max]=key==='feather'?[0,100]:[280,500];const input=el('input',{type:'range',min,max,step:'1','aria-label':name});input.value=value;const output=el('output',{},String(value));input.oninput=()=>{parent[key]=Number(input.value);output.textContent=input.value;dirty();};box.append(el('div',{class:'range-row'},input,output));return box;}
  const choices=options(key,parent);let input;if(choices){input=el('select',{'aria-label':name});for(const c of choices){const [val,label]=Array.isArray(c)?c:[c,c];input.append(el('option',{value:val},label));}if(value&&!choices.some(c=>(Array.isArray(c)?c[0]:c)===value))input.append(el('option',{value},value));input.value=value??'';}else if(typeof value==='number'){input=el('input',{type:'number','aria-label':name});input.value=value;}else if(String(value??'').length>90||/summary|description|abstract|reason|paragraph|^text$|^desc$|^action$/.test(key)){input=el('textarea',{rows:'3','aria-label':name});input.value=value??'';}else{input=el('input',{type:/^(date|updated)$/.test(key)?'date':'text','aria-label':name});input.value=value??'';}
  input.addEventListener('input',()=>{parent[key]=typeof value==='number'?Number(input.value):input.value;dirty();});
  if(['art','image','cover','logo'].includes(key)){const pick=button('选图',()=>pickMedia(url=>{parent[key]=url;dirty();renderForm();}));box.append(el('div',{class:'image-field'},input,pick));if(value)box.append(el('img',{src:value,class:'image-thumb',alt:''}));}else box.append(input);
  return box;
}
function objectFields(value,container,path){const layer=/^meta\.(dao|fa|shu|qi)\.\d+$/.test(path);if(layer&&!('publication'in value))container.append(field('publication',false,value,path+'.publication'));for(const [key,v]of Object.entries(value)){if(key==='type'&&(layer||'publication'in value)&&!value.publication)continue;container.append(field(key,v,value,path+'.'+key));}}
function renderForm(){const doc=state.doc;$('form').hidden=false;$('raw').hidden=true;$('form-tab').classList.add('active');$('raw-tab').classList.remove('active');const root=$('form');root.replaceChildren();if(doc.conflict)root.append(el('p',{class:'doc-warning'},'磁盘文件已修改。写入前请恢复磁盘版本并重新合并内容。'));objectFields(doc.meta,root,'meta');if(doc.body!==null){const label=el('div',{class:'field'},el('span',{},doc.record.group==='pages'?'页面源码':'正文'));const body=el('textarea',{class:'body-editor','aria-label':'正文',spellcheck:'false'});body.value=doc.body;body.oninput=()=>{doc.body=body.value;dirty();};const row=el('div',{class:'release-actions'},button('插入图片',()=>pickMedia(url=>{const start=body.selectionStart;body.setRangeText('\n![]('+url+')\n',start,body.selectionEnd,'end');doc.body=body.value;dirty();})));if(doc.record.group!=='pages')label.append(formattingToolbar(body));label.append(body,row);root.append(label);}}
function formattingToolbar(body){
  const bar=el('div',{class:'format-toolbar',role:'toolbar','aria-label':'正文格式'});
  function apply(action,option='',selection){
    const [start,end]=selection||[body.selectionStart,body.selectionEnd];
    const edit=formatSelection(body.value,start,end,action,option);const scroll=body.scrollTop;
    body.focus();body.setSelectionRange(edit.from,edit.to);
    if(!document.execCommand('insertText',false,edit.text))body.setRangeText(edit.text,edit.from,edit.to,'end');
    body.setSelectionRange(edit.start,edit.end);body.scrollTop=scroll;body.dispatchEvent(new Event('input',{bubbles:true}));
  }
  const heading=el('select',{'aria-label':'段落格式',title:'段落格式'});
  for(const [value,text]of [['','正文'],['2','二级标题'],['3','三级标题'],['4','四级标题']])heading.append(el('option',{value},text));
  heading.onchange=()=>apply('heading',heading.value);bar.append(heading);
  for(const [action,symbol,label]of [['bold','B','加粗'],['italic','I','斜体'],['strike','S','删除线'],['quote','❞','引用'],['unordered','≡','无序列表'],['ordered','1.','有序列表'],['code','<>','行内代码'],['block','{ }','代码块'],['link','↗','插入链接'],['table','▦','插入表格'],['rule','―','分隔线']]){
    const control=button(symbol,()=>{
      if(action!=='link')return apply(action);
      const selection=[body.selectionStart,body.selectionEnd],original=body.value;
      const input=el('input',{type:'url','aria-label':'链接地址',placeholder:'https://'});
      modal('插入链接',el('div',{},el('label',{class:'field'},el('span',{},'链接地址'),input),button('插入',()=>{
        const url=input.value.trim();if(!/^(https?:\/\/|mailto:|\/(?!\/)|#)/i.test(url)||/[\s<>]/.test(url))return toast('请输入 HTTP(S)、邮箱或站内链接',true);
        if(body.value!==original)return toast('正文已修改，请关闭窗口后重新选择文字',true);
        $('modal').close();apply('link',url.replace(/\(/g,'%28').replace(/\)/g,'%29'),selection);
      },'primary')));input.focus();
    },'format-button format-'+action);
    control.title=label;control.setAttribute('aria-label',label);control.onmousedown=e=>e.preventDefault();bar.append(control);
  }
  body.addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&!event.altKey&&['b','i','k'].includes(event.key.toLowerCase())){event.preventDefault();const action={b:'bold',i:'italic',k:'link'}[event.key.toLowerCase()];bar.querySelector('.format-'+action).click();}});
  return bar;
}
function syncRaw(){if(state.raw){const data=JSON.parse($('raw').value);if(!data.meta||typeof data.meta!=='object')throw Error('源数据需要包含 meta 和 body');state.doc.meta=data.meta;state.doc.body=data.body;}}
async function save(){syncRaw();const saved=await api('save',state.doc);for(const [key,value]of Object.entries(saved))if(key!=='meta'&&key!=='body')state.doc[key]=value;state.dirty=false;if(!state.drafts.includes(state.doc.id))state.drafts.push(state.doc.id);$('save-state').textContent='草稿已保存';$('draft-badge').textContent='草稿';renderRecords();}
async function buildPreview(){if(state.dirty)await save();$('save-state').textContent='正在构建预览…';const result=await job('preview',{ids:state.doc.draft?[state.doc.id]:[]});state.previewURL=result.url;const url=result.url+state.doc.record.url+'?v='+Date.now();$('preview-frame').src=url;$('open-preview').href=url;$('preview-empty').hidden=true;$('preview-viewport').hidden=false;resizePreview();$('save-state').textContent='预览已更新';if(innerWidth<1050)window.open(url,'_blank');}
function resizePreview(){const width=$('preview-viewport').clientWidth;if(!width)return;const scale=state.actualSize?1:Math.min(1,width/state.width);const frame=$('preview-frame');frame.style.width=state.width+'px';frame.style.height=Math.max(900,$('preview-viewport').clientHeight/scale)+'px';frame.style.transform='scale('+scale+')';$('preview-viewport').style.overflow=state.actualSize?'auto':'hidden';$('preview-scale').textContent=Math.round(scale*100)+'%';}
async function pickMedia(callback){const box=el('div');const search=el('input',{type:'search',placeholder:'搜索图片','aria-label':'搜索图片'});const grid=el('div',{class:'media-grid'});const upload=button('上传图片',()=>uploadMedia(async url=>{callback(url);$('modal').close();}));box.append(el('div',{class:'special-head'},search,upload),grid);modal('选择图片',box);const items=await api('media');const render=()=>grid.replaceChildren(...items.filter(i=>i.name.toLowerCase().includes(search.value.toLowerCase())).map(i=>mediaCard(i,()=>{callback(i.url);$('modal').close();})));search.oninput=render;render();}
function mediaCard(item,fn){const node=button('',fn,'media-item');node.append(el('img',{src:item.url,alt:'',loading:'lazy'}),el('span',{},item.name,el('small',{},Math.round(item.size/1024)+' KB')));return node;}
function uploadMedia(callback){const input=el('input',{type:'file',accept:'image/png,image/jpeg,image/webp,image/gif'});input.onchange=async()=>{const file=input.files[0];if(!file)return;try{const r=await fetch('/api/admin/upload',{method:'POST',headers:{'X-Admin-Token':state.token,'Content-Type':'application/octet-stream'},body:file});const data=await r.json();if(!r.ok)throw Error(data.error);await callback(data.url);toast('图片已上传');}catch(e){toast(e.message,true);}};input.click();}
async function mediaPage(){const root=$('special');root.replaceChildren();const search=el('input',{type:'search',placeholder:'搜索素材','aria-label':'搜索素材'});search.style.maxWidth='300px';const grid=el('div',{class:'media-grid'});root.append(el('div',{class:'special-head'},el('h2',{},'图片素材'),search,button('上传图片',()=>uploadMedia(()=>mediaPage()),'primary')),grid);const items=await api('media');const render=()=>grid.replaceChildren(...items.filter(i=>i.name.includes(search.value)).map(i=>mediaCard(i,()=>{modal(i.name,el('div',{},el('img',{src:i.url,alt:i.name,style:'max-width:100%;max-height:48vh;object-fit:contain'}),el('p',{class:'muted'},i.url),button('复制路径',()=>navigator.clipboard.writeText(i.url).then(()=>toast('路径已复制')))));})));search.oninput=render;render();}
async function releasePage(){const root=$('special');root.replaceChildren(el('p',{class:'muted'},'正在读取工作区…'));const result=await api('changes');state.files=result.files;state.selected=new Set();state.proof=null;root.replaceChildren(el('div',{class:'special-head'},el('h2',{},'待发布修改'),el('span',{class:'pill'},result.branch),button('刷新',()=>releasePage())));
  const pendingArticles=state.files.filter(f=>f.path.startsWith('_articles/'));
  if(pendingArticles.length)root.append(el('div',{class:'notice',role:'status'},el('strong',{},'文章尚未发布'),el('p',{},'以下文章目前只保存在本机。请点击“发布到官网”，核对清单后“确认发布”；完成提交、推送和 GitHub Pages 部署后才会上线。'),el('pre',{},pendingArticles.map(f=>f.path).join('\n'))));
  if(result.last_release){const last=result.last_release,r=last.result||{};const failed=last.status==='failed'||r.ok===false;const text=failed?'上次操作未完成':last.status==='running'?'发布任务正在执行':last.stage==='release_check'?'构建检查通过，尚未执行推送':'已推送，仍需确认 GitHub Pages 部署结果';const box=el('div',{class:'notice',role:'status'},el('strong',{},text),el('small',{},last.updated_at));if(last.error||r.error)box.append(el('pre',{},last.error||r.error));if(r.commit)box.append(el('p',{},'提交：'+r.commit));if(r.actions_url)box.append(el('a',{href:r.actions_url,target:'_blank',rel:'noopener'},'查看部署结果 ↗'));root.append(box);}
  if(state.drafts.length){const section=el('div',{class:'notice'},el('strong',{},state.drafts.length+' 份草稿尚未准备发布'));const ids=new Set();for(const id of state.drafts){const cb=el('input',{type:'checkbox'});cb.onchange=()=>cb.checked?ids.add(id):ids.delete(id);section.append(el('label',{class:'file-row'},cb,state.records.find(r=>r.id===id)?.title||id));}section.append(button('准备所选草稿',()=>busy(async()=>{if(!ids.size)throw Error('请选择草稿');await job('apply',{ids:[...ids]});await refresh();await releasePage();toast('本地准备完成，请继续点击发布到官网');})));root.append(section);}
  if(result.ahead){root.append(el('div',{class:'notice'},'本地已有尚未推送的提交：',el('pre',{},result.ahead),button('重试推送已有提交',()=>confirmAction('推送已有提交',result.ahead,async()=>{await job('retry-push',{});toast('推送完成');await releasePage();}))));}
  const all=el('input',{type:'checkbox','aria-label':'全选待发布文件'});root.append(el('label',{class:'file-row'},all,'全选',el('span',{class:'muted'},state.files.length+' 个文件')));const list=el('div');const boxes=[];
  for(const file of state.files){const check=el('input',{type:'checkbox','aria-label':file.path});boxes.push(check);check.onchange=()=>{check.checked?state.selected.add(file.path):state.selected.delete(file.path);invalidate();};list.append(el('div',{class:'file-row'},check,el('small',{},file.status),el('span',{class:'path'},file.path),button('差异',async()=>{try{const d=await api('diff',{file});modal(file.path,el('pre',{},d.diff));}catch(e){toast(e.message,true);}})));}
  all.onchange=()=>{boxes.forEach((box,i)=>{box.checked=all.checked;box.checked?state.selected.add(state.files[i].path):state.selected.delete(state.files[i].path);});invalidate();};root.append(list);if(!state.files.length)root.append(el('p',{class:'empty'},'工作区没有待发布修改'));
  const count=el('span',{class:'muted'});
  const publishButton=button('发布到官网',()=>{
    const files=chosen();
    const box=el('div',{},el('p',{},'本次发布 '+files.length+' 个文件：'),el('pre',{},files.map(f=>f.path).join('\n')));
    if(result.ahead)box.append(el('p',{},'同时推送已有提交：'),el('pre',{},result.ahead));
    if(state.drafts.length)box.append(el('p',{class:'notice'},state.drafts.length+' 份未写入草稿不包含在本次发布中。'));
    const message=el('input',{value:'更新官网内容','aria-label':'提交说明'});
    const progress=el('p',{role:'status'});
    const cancel=button('取消',()=>$('modal').close());
    const go=button('确认发布',async()=>{
      go.disabled=true;cancel.disabled=true;$('close-modal').disabled=true;
      const preventClose=e=>e.preventDefault();$('modal').addEventListener('cancel',preventClose);
      try{
        progress.textContent='正在检查并构建…';
        const checked=await job('check',{files});
        progress.textContent='检查通过，正在提交并推送…';
        const r=await job('publish',{files,proof:checked.proof,message:message.value});
        $('modal').close();await releasePage();
        toast('已推送：'+r.commit.slice(0,7)+'，等待 GitHub Pages 部署');
      }catch(e){progress.textContent=e.message;toast(e.message,true);}
      finally{go.disabled=false;cancel.disabled=false;$('close-modal').disabled=false;$('modal').removeEventListener('cancel',preventClose);}
    },'primary');
    box.append(message,progress,el('div',{class:'release-actions'},cancel,go));modal('发布确认',box);
  },'primary');
  function chosen(){return state.files.filter(f=>state.selected.has(f.path));}
  function invalidate(){state.proof=null;publishButton.disabled=!state.selected.size;count.textContent=state.files.length?'已选择 '+state.selected.size+' / '+state.files.length+' 个文件':'没有待发布修改';all.checked=state.files.length>0&&state.selected.size===state.files.length;all.indeterminate=state.selected.size>0&&!all.checked;}
  state.selected=new Set(state.files.map(f=>f.path));boxes.forEach(box=>box.checked=true);invalidate();
  root.prepend(el('div',{class:'release-actions'},count,publishButton));
  root.append(button('查看部署状态',async()=>{try{const runs=await api('deployments');modal('GitHub Pages 部署',el('div',{},...runs.map(r=>el('p',{},el('a',{href:r.url,target:'_blank',rel:'noopener'},r.displayTitle),' · '+r.status+' / '+(r.conclusion||'进行中')))));}catch(e){toast(e.message,true);}}));
}
function operationsPage(){const root=$('special');root.replaceChildren(el('div',{class:'special-head'},el('h2',{},'资讯与留言')),el('div',{class:'notice'},'资讯由独立归档仓库同步，留言保存在 GitHub Discussions。'),el('div',{class:'release-actions'},el('a',{href:'https://github.com/EastSword/EastSword.github.io/discussions/1',target:'_blank',rel:'noopener'},'管理江湖留名 ↗'),el('a',{href:'http://127.0.0.1:4018/news/',target:'_blank',rel:'noopener'},'查看资讯归档 ↗')),button('编辑资讯页面',()=>{location.hash='pages';setTimeout(()=>select('pages/news'),100);}));}
function newDocument(){const slug=el('input',{'aria-label':'路径标识',placeholder:'例如 agent-runtime-security'});const title=el('input',{'aria-label':'新内容标题',placeholder:'内容标题'});const createButton=button('创建草稿',async()=>{createButton.disabled=true;try{const d=await api('new',{group:state.group,slug:slug.value,title:title.value});$('modal').close();await refresh();await load(d.id);}catch(e){toast(e.message,true);createButton.disabled=false;}},'primary');modal('新建'+(groups.find(g=>g[0]===state.group)?.[1]||'内容'),el('div',{},el('label',{class:'field'},el('span',{},'标题'),title),el('label',{class:'field'},el('span',{},'路径标识'),slug),createButton));}
async function route(){const [routeGroup,query='']=location.hash.slice(1).split('?');let group=routeGroup||'home';const requestedId=new URLSearchParams(query).get('doc');if(!groups.some(g=>g[0]===group))group='home';if(state.dirty){const previous=state.group;confirmAction('切换栏目','当前修改尚未保存，确认后放弃编辑器内修改。',async()=>{state.dirty=false;await showGroup(group,requestedId);});history.replaceState(null,'','#'+previous+(state.doc?'?doc='+encodeURIComponent(state.doc.id):''));return;}await showGroup(group,requestedId);}
async function showGroup(group,requestedId=null){documentLoadGeneration++;state.group=group;history.replaceState(null,'','#'+group);nav();$('page-title').textContent=groups.find(g=>g[0]===group)[1];const special=['media','release','operations'].includes(group);$('workspace').hidden=special;$('special').hidden=!special;$('doc-actions').hidden=special;$('record-panel').hidden=['home','global','about','tools'].includes(group);$('search').value='';try{if(group==='media')await mediaPage();else if(group==='release')await releasePage();else if(group==='operations')operationsPage();else{renderRecords();let rememberedId;try{rememberedId=localStorage.getItem('eastsword-admin-selected-'+group);}catch{}const candidates=state.records.filter(r=>r.group===group);const first=candidates.find(r=>r.id===requestedId)||candidates.find(r=>r.id===rememberedId)||candidates[0];if(first)await load(first.id);else{state.doc=null;$('form').replaceChildren();$('doc-actions').hidden=true;$('preview-frame').src='about:blank';$('preview-viewport').hidden=true;$('preview-empty').hidden=false;}}}catch(e){toast(e.message,true);}}
$('save').onclick=()=>busy(async()=>{await save();toast('草稿已保存');});$('preview').onclick=()=>busy(buildPreview);$('apply').textContent='准备发布';$('apply').title='保存到本地官网文件，随后进入发布中心确认发布';$('apply').onclick=()=>busy(async()=>{if(state.dirty)await save();if(state.doc.draft){$('save-state').textContent='正在检查并准备…';await job('apply',{ids:[state.doc.id]});}await refresh();state.dirty=false;await showGroup('release');toast('请在发布中心核对清单并确认发布');});
$('delete-draft').onclick=()=>{const doc=state.doc;confirmAction('删除草稿',`确定删除《${doc.meta.title||doc.record.title}》？草稿将从列表移除，未保存的修改也会丢弃。后台会保留删除前的已保存副本。`,()=>busy(async()=>{await api('delete',{id:doc.id,revision:doc.revision});state.dirty=false;state.doc=null;await refresh();await showGroup(state.group);toast('草稿已删除');}));};
$('discard').onclick=()=>confirmAction('恢复磁盘版本','放弃当前内容的草稿和未保存修改。',async()=>{const id=state.doc.id;await api('discard',{id});state.dirty=false;await refresh();const next=state.records.find(r=>r.id===id)||state.records.find(r=>r.group===state.group);if(next)await load(next.id);else{state.doc=null;$('form').replaceChildren();renderRecords();}});
$('search').oninput=renderRecords;$('new').onclick=newDocument;$('close-modal').onclick=()=>$('modal').close();
$('form-tab').onclick=()=>{try{syncRaw();state.raw=false;renderForm();}catch(e){toast(e.message,true);}};$('raw-tab').onclick=()=>{state.raw=true;$('raw').value=JSON.stringify({meta:state.doc.meta,body:state.doc.body},null,2);$('raw').hidden=false;$('form').hidden=true;$('raw-tab').classList.add('active');$('form-tab').classList.remove('active');};$('raw').oninput=dirty;
$('devices').onclick=e=>{const b=e.target.closest('[data-width]');if(!b)return;state.width=Number(b.dataset.width);$('devices').querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));resizePreview();};
window.addEventListener('resize',resizePreview);window.addEventListener('hashchange',route);window.addEventListener('beforeunload',e=>{if(state.dirty){e.preventDefault();e.returnValue='';}});window.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='s'){e.preventDefault();if(state.doc)busy(save);}});
const scaleButton=button('100%',()=>{state.actualSize=!state.actualSize;scaleButton.classList.toggle('active',state.actualSize);scaleButton.title=state.actualSize?'缩放以适应预览栏':'按实际尺寸查看';resizePreview();},'icon');scaleButton.id='preview-scale';scaleButton.title='按实际尺寸查看';$('devices').after(scaleButton);
const fullPreview=el('a',{id:'full-preview',target:'_blank',rel:'noopener',hidden:''},'打开完整页面 ↗');$('doc-actions').append(fullPreview);
const previewObserver=new MutationObserver(()=>{const href=$('open-preview').getAttribute('href');if(href){fullPreview.href=href;fullPreview.hidden=false;}});previewObserver.observe($('open-preview'),{attributes:true,attributeFilter:['href']});
document.querySelectorAll('#doc-actions button').forEach(b=>b.disabled=true);
function setPanelCollapsed(panel,collapsed){
  document.body.classList.toggle(panel+'-collapsed',collapsed);
  const control=$('toggle-'+panel),label=panel==='navigation'?'导航栏':state.group==='articles'?'文章列表':'内容列表';
  control.setAttribute('aria-expanded',String(!collapsed));control.title=control.getAttribute('aria-label')||'';
  control.title=(collapsed?'展开':'收起')+label;control.setAttribute('aria-label',control.title);
  if(panel==='records')control.textContent=collapsed?'›':'‹';
  try{localStorage.setItem('eastsword-admin-'+panel+'-collapsed',String(collapsed));}catch{}
  requestAnimationFrame(resizePreview);
}
for(const panel of ['navigation','records']){
  let collapsed=false;try{collapsed=localStorage.getItem('eastsword-admin-'+panel+'-collapsed')==='true';}catch{}
  setPanelCollapsed(panel,collapsed);
  $('toggle-'+panel).onclick=()=>setPanelCollapsed(panel,!document.body.classList.contains(panel+'-collapsed'));
}
new MutationObserver(()=>{
  $('toggle-records').hidden=$('record-panel').hidden||$('workspace').hidden;
  setPanelCollapsed('records',document.body.classList.contains('records-collapsed'));
}).observe($('workspace'),{attributes:true,attributeFilter:['hidden'],subtree:true});
refresh().then(route).catch(e=>toast(e.message,true)).finally(()=>document.querySelectorAll('#doc-actions button').forEach(b=>b.disabled=false));
