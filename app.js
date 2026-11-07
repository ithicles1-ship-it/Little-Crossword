 'use strict';
const $=id=>document.getElementById(id);
const grid=$('grid'), clue=$('clue'), nativeInput=$('nativeInput');
const KEY='little-crossword-daily-v8'; // preserves existing progress on the same domain
const SENTINEL='\u200B';
let number=1, data=null, entries=[], entry=0, cell=0, filled={}, clueHints={}, solved=false, keyboardVisible=false;
let edition={mode:'classic',key:'',number:1,title:'Classic daily',description:'',date:londonDay(),source:'offline'};
const inflightEditions=new Map();let pendingNotice=null;
let tiles=[], lastChanged=-1, touchingClueStart=null, checkHighlightTimer=null;
const keyboardTapState=new WeakMap();
function rememberKeyboard(el){el.addEventListener('pointerdown',()=>keyboardTapState.set(el,keyboardVisible),{passive:true})}
function keyboardBeforeTap(el){const old=keyboardTapState.get(el);keyboardTapState.delete(el);return old===undefined?keyboardVisible:old}
function stored(){try{
 const v=JSON.parse(localStorage.getItem(KEY));if(v)return v;
 // Bring across existing v7 progress into the practice archive.
 const prior=JSON.parse(localStorage.getItem('little-crossword-fair-v7'));
 if(prior){
   const practice=Object.fromEntries(Object.entries(prior.puzzles||{}).map(([k,v])=>['practice:'+k,v]));
   return {completed:(prior.completed||[]).map(n=>'practice:'+n),puzzles:practice,news:{}};
 }
 return {};
}catch{return {}}}
function canonicalNumber(n){const v=Math.floor(Number(n));return Number.isFinite(v)&&v>=1&&v<=PUZZLE_LIMIT?v:todayIndex()}
const initial=stored(), completed=new Set(initial.completed||[]);
function save(){try{
 const all=stored();all.lastEdition=edition.key;all.completed=[...completed];all.puzzles=all.puzzles||{};
 if(solved)delete all.puzzles[edition.key];else all.puzzles[edition.key]={filled,clueHints};
 localStorage.setItem(KEY,JSON.stringify(all));
}catch(e){console.warn('Could not save puzzle progress',e)}}
function todayIndex(){return dailyChoice('classic').number}
function resetNative(){nativeInput.value=SENTINEL;try{nativeInput.setSelectionRange(SENTINEL.length,SENTINEL.length)}catch{}}
function updateViewport(){document.documentElement.style.setProperty('--visible-height',`${Math.round(window.visualViewport?.height||window.innerHeight)}px`)}
window.visualViewport?.addEventListener('resize',updateViewport);window.addEventListener('resize',updateViewport);updateViewport();
function focusNative(){if(solved)return;resetNative();try{nativeInput.focus({preventScroll:true})}catch{nativeInput.focus()}}
function dismissKeyboard(){nativeInput.blur();keyboardVisible=false;document.body.classList.remove('keyboard-open');refreshKeyboardBar()}
function refreshKeyboardBar(){ $('keyboardToggle').textContent=keyboardVisible?'✓ Done':'⌨ Keyboard';$('keyboardToggle').setAttribute('aria-label',keyboardVisible?'Hide keyboard':'Show iPhone keyboard');$('keyboardHelp').textContent=keyboardVisible?'Backspace moves through the current word':'Tap a square to use your iPhone keyboard' }
function active(){return entries[entry]}
function setEditionTabs(){
 document.querySelectorAll('.edition-tab').forEach(b=>{
   const active=b.dataset.edition===edition.mode;
   b.classList.toggle('is-active',active);b.setAttribute('aria-current',active?'true':'false');
 });
}
function updateSourceLinks(){
 const box=$('sourceLinks');box.replaceChildren();box.hidden=true;
 if(edition.mode!=='news'||!edition.sources?.length)return;
 const label=document.createElement('span');label.textContent='Recent stories behind today’s clues:';box.append(label);
 edition.sources.slice(0,3).forEach((s,i)=>{
  if(!/^https:\/\//.test(s.url))return;
  const b=document.createElement('button');b.textContent=(s.source?s.source+' · ':'')+(s.title?.length>55?s.title.slice(0,52)+'…':(s.title||`Story ${i+1}`));
  b.title=s.title||'Read original story';b.onclick=()=>window.open(s.url,'_blank','noopener,noreferrer');box.append(b);
 });
 box.hidden=false;
}
function activateEdition(which){
 dismissKeyboard();edition=which;number=which.number||1;
 if(which.spec){
   data=parseMini(which.spec);
 }else{
   data=createCrossword(number);
   if(which.mode==='theme' && THEME_EDITS[number]){
     for(const e of data.entries){const t=THEME_EDITS[number][e.answer];if(t){e.clue=t[0];e.hint=t[1]}}
   }
 }
 entries=[...data.entries].sort((a,b)=>(a.direction==='Across'?0:1)-(b.direction==='Across'?0:1)||a.number-b.number);
 const record=(stored().puzzles||{})[edition.key]||{};
 filled={...record.filled};clueHints={...record.clueHints};solved=completed.has(edition.key);
 if(solved)data.cells.forEach((v,i)=>{if(v!==null)filled[i]=v});
 entry=0;cell=active().cells[0];lastChanged=-1;
 $('puzzleLabel').textContent=which.mode==='archive'?'#'+number:prettyDay(which.date).slice(0,6);
 $('panelTitle').textContent=which.title;
 $('editionSubtitle').textContent=which.mode==='archive'?'Practice mini #'+number:prettyDay(which.date)+' · '+which.description;
 $('puzzleCount').textContent=which.mode==='archive'?'24 hand-checked practice minis · 5 Across · 5 Down':which.source==='rss'?'Updated news edition · 5 Across / 5 Down':'Daily minis · 5 Across / 5 Down';
 $('onlineNotice').hidden=true;
 setEditionTabs();updateSourceLinks();closeModal();buildGrid();render(true);save();
}
function load(n){
 const id=canonicalNumber(n);
 activateEdition({mode:'archive',source:'offline',key:`practice:${id}`,number:id,title:'Practice mini',description:'An extra crossword whenever you like.',date:londonDay()});
}
function todayLiveKey(mode,date){return `published:${mode}:${date}`}
function todayCacheKey(mode,date){return `${mode}:${date}`}
function activateOffline(mode,date){
 if(mode==='news'){
   const a=dailyChoice('classic',date);
   let number=(a.number+10)%PUZZLE_LIMIT+1;
   if(number===dailyChoice('theme',date).number)number=number%PUZZLE_LIMIT+1;
   activateEdition({mode:'news',source:'offline',date,key:`offline:news:${date}`,number,
     title:'The Newsroom',description:'Offline news-and-media mini · not based on today’s headlines'});
   setNotice('Offline Newsroom mini. Real headlines appear here only when a daily news update is published.');
   return;
 }
 const d=dailyChoice(mode,date);
 activateEdition({...d,source:'offline',key:mode==='theme'?`offline:theme:v2:${date}`:`offline:${mode}:${date}`});
}
function setNotice(message,linkMode,linkDate){
 const box=$('onlineNotice');box.replaceChildren();
 const label=document.createElement('span');label.textContent=message;box.append(label);
 if(linkMode&&getCachedOnline(linkMode,linkDate)){
   const btn=document.createElement('button');btn.type='button';btn.textContent='Open headlines edition';
   btn.onclick=()=>activateEdition(getCachedOnline(linkMode,linkDate));box.append(btn);
 }
 box.hidden=false;
}
function getCachedOnline(mode,date){return (stored().editions||{})[todayCacheKey(mode,date)]||null}
function cacheOnline(mode,date,which){try{
 const all=stored();all.editions=all.editions||{};all.editions[todayCacheKey(mode,date)]=which;
 const keys=Object.keys(all.editions).sort();if(keys.length>90)keys.slice(0,keys.length-90).forEach(k=>delete all.editions[k]);
 localStorage.setItem(KEY,JSON.stringify(all));
}catch(e){console.warn('Could not cache edition',e)}}
function onlineEditionFromPayload(payload,mode,date){
 if(payload?.date!==date || !payload?.puzzle)throw Error('Not a puzzle for today');
 const p=payload.puzzle;
 if(!Array.isArray(p.shape)||!Array.isArray(p.answers)||!Array.isArray(p.clues)||!Array.isArray(p.hints))throw Error('Invalid crossword');
 parseMini(p);
 if(!Array.isArray(p.sources)||!p.sources.length)throw Error('Missing source headlines');
 return {mode,source:'rss',date,key:todayLiveKey(mode,date),number:1,spec:p,
 title:'In the News',description:p.description||'Clues inspired by recent verified headlines',sources:p.sources};
}
async function fetchNewsEdition(date){
 const response=await fetch('./data/news.json?date='+encodeURIComponent(date),{cache:'no-store'});
 if(!response.ok)throw Error('No fresh edition');
 const payload=await response.json();
 const which=onlineEditionFromPayload(payload,'news',date);
 cacheOnline('news',date,which);
 return which;
}
function loadDaily(mode){
 const date=londonDay();
 if(mode!=='news'){activateOffline(mode,date);return}
 const cached=getCachedOnline('news',date);
 if(cached){try{activateEdition(cached);return}catch(e){console.warn('Cached news is invalid',e)}}
 activateOffline('news',date);
 if(!navigator.onLine){setNotice('Offline Newsroom mini · today’s headlines have not been loaded.');return}
 const checking=edition.key;
 fetchNewsEdition(date).then(which=>{
   // Never discard a crossword that the player has started filling.
   if(edition.key===checking&&!solved&&Object.keys(filled).length===0){activateEdition(which)}
   else if(edition.mode==='news'&&edition.date===date)setNotice('Today’s headline-linked crossword is ready.', 'news',date);
 }).catch(()=>{
   if(edition.key===checking)setNotice('Today’s news edition hasn’t been published yet. The offline Newsroom mini is ready; check again after the morning refresh.');
 });
}
function buildGrid(){
 grid.classList.toggle('large-mini',Math.max(data.rows,data.cols)>6);
 grid.style.setProperty('--rows',data.rows);grid.style.setProperty('--cols',data.cols);grid.replaceChildren();tiles=[];
 for(let i=0;i<data.cells.length;i++){
  const b=document.createElement('button');b.type='button'; b.className='tile';
  if(data.cells[i]===null){b.classList.add('empty');b.disabled=true;b.setAttribute('aria-hidden','true');b.tabIndex=-1;}
  else{
    const no=data.entries.find(e=>e.cells[0]===i)?.number||'';
    const num=document.createElement('span');num.className='number';num.textContent=no;
    const letter=document.createElement('span');letter.className='letter';
    b.append(num,letter);
    b.setAttribute('aria-label',`Row ${Math.floor(i/data.cols)+1}, column ${i%data.cols+1}`);
    b.addEventListener('click',()=>tapCell(i));
  }
  b.style.setProperty('--delay',`${Math.min(i,30)*8}ms`);
  tiles.push(b);grid.append(b);
 }
}
function tapCell(i){
 if(data.cells[i]===null)return;
 const here=entries.map((e,ix)=>e.cells.includes(i)?ix:-1).filter(ix=>ix>=0);
 if(!here.length)return;
 let target;
 if(i===cell && here.length>1 && keyboardVisible){target=here.find(ix=>ix!==entry)??entry}
 else target=here.find(ix=>entries[ix].direction===active().direction)??here[0];
 entry=target;cell=i;render();if(!solved)focusNative();
}
function render(animateClue=false){
 const current=active();const currentSet=new Set(current.cells);
 for(let i=0;i<tiles.length;i++){
   if(data.cells[i]===null)continue;
   const b=tiles[i];b.classList.toggle('in-word',currentSet.has(i));
   b.classList.toggle('selected',i===cell);b.classList.toggle('correct',solved);
   const letter=b.querySelector('.letter');const next=filled[i]||'';
   if(letter.textContent!==next){letter.textContent=next;if(lastChanged===i){b.classList.remove('just-typed');void b.offsetWidth;b.classList.add('just-typed');setTimeout(()=>b.classList.remove('just-typed'),220)}}
   b.setAttribute('aria-label',`Row ${Math.floor(i/data.cols)+1}, column ${i%data.cols+1}, ${next||'empty'}`);
 }
 clue.innerHTML='';
 const meta=document.createElement('div');meta.className='clue-meta';meta.textContent=`${current.number} ${current.direction} · ${current.answer.length} letters`;
 const text=document.createElement('div');text.className='clue-text';text.textContent=current.clue;
 clue.append(meta,text);
 const clueKey=`${current.direction}-${current.number}`;
 const isHintShown=!!clueHints[clueKey];
 if(isHintShown){
   const help=document.createElement('div');help.className='clue-hint';help.setAttribute('role','note');
   const icon=document.createElement('span');icon.className='clue-hint-icon';icon.textContent='✧';
   const words=document.createElement('span');words.textContent=current.hint;
   help.append(icon,words);clue.append(help);
 }
 $('hint').textContent=isHintShown?'✧ Hide hint':'✧ Hint';
 $('hint').setAttribute('aria-pressed',String(isHintShown));
 if(animateClue){clue.classList.remove('slide-in');void clue.offsetWidth;clue.classList.add('slide-in')}
 const count=data.cells.filter((v,i)=>v!==null&&!!filled[i]).length;
 const total=data.cells.filter(v=>v!==null).length;
 $('progressText').textContent=solved?'Completed — beautiful work!':`${count} of ${total} squares filled`;
 $('bar').style.width=`${count/total*100}%`;
 $('completed').textContent=`${completed.size} completed`;
 $('direction').textContent=current.direction==='Across'?'↕ Down':'↔ Across';
 $('check').disabled=solved;
 $('hint').disabled=solved;
}
function chooseEntry(ix, focus=false){
 entry=(ix+entries.length)%entries.length;
 cell=active().cells.find(k=>!filled[k])??active().cells[0];
 lastChanged=-1;render(true);
 if(focus && !solved)focusNative();
}
function change(delta,keepKeyboard=keyboardVisible){chooseEntry(entry+delta,keepKeyboard)}
function toggle(keepKeyboard=keyboardVisible){
 const cross=entries.findIndex((e,i)=>i!==entry && e.direction!==active().direction && e.cells.includes(cell));
 if(cross>=0){entry=cross;render(true);if(keepKeyboard)focusNative();return}
 const other=entries.findIndex(e=>e.direction!==active().direction);
 if(other>=0)chooseEntry(other,keepKeyboard);
}
function moveTo(index){const e=active();const next=Math.max(0,Math.min(e.cells.length-1,index));cell=e.cells[next];render()}
function insert(ch){
 if(solved)return;
 const e=active();let i=e.cells.indexOf(cell);if(i<0)i=0;
 const key=e.cells[i];filled[key]=ch;lastChanged=key;
 // Stay at the last letter so Backspace works naturally.
 if(i<e.cells.length-1){
   let target=i+1;
   while(target<e.cells.length-1 && filled[e.cells[target]])target++;
   cell=e.cells[target];
 }
 save();render();checkWin();
}
function insertString(raw){for(const ch of String(raw||'').toUpperCase()){if(ch>='A'&&ch<='Z')insert(ch)}}
function backspace(){
 if(solved)return;
 const e=active();let at=e.cells.indexOf(cell);if(at<0)return;
 // First delete the current letter, then move backwards through only this answer.
 let i=at;
 if(!filled[e.cells[i]])i=Math.max(0,i-1);
 const k=e.cells[i];delete filled[k];cell=k;lastChanged=-1;
 save();render();
}
function checkWin(){if(solved)return;if(data.cells.every((v,i)=>v===null||filled[i]===v)){
 solved=true;completed.add(edition.key);save();dismissKeyboard();render();celebrate();
 setTimeout(()=>showModal('Crossword complete!','You solved all five Across and five Down clues.',[['Close',closeModal],['More editions',()=>showDailyMenu()]]),420);
}}
function hint(keepKeyboard=keyboardVisible){
 if(solved)return;
 const current=active(), clueKey=`${current.direction}-${current.number}`;
 clueHints[clueKey]=!clueHints[clueKey];
 save();render(true);
 if(keepKeyboard)focusNative();
}
function check(){
 if(solved)return;
 const wrong=Object.keys(filled).map(Number).filter(i=>filled[i]!==data.cells[i]);
 if(!wrong.length){showModal('So far, so good','Everything you have entered is correct. Keep going!',[['Keep playing',closeModal]]);return}
 wrong.forEach(i=>tiles[i]?.classList.add('wrong'));
 if(checkHighlightTimer)clearTimeout(checkHighlightTimer);
 checkHighlightTimer=setTimeout(()=>wrong.forEach(i=>tiles[i]?.classList.remove('wrong')),1200);
 showModal('A few to revisit',`${wrong.length} ${wrong.length===1?'letter needs':'letters need'} another look.`,[['Keep playing',closeModal],['Clear mistakes',()=>{wrong.forEach(i=>{delete filled[i]});closeModal();save();render()}]]);
}
function celebrate(){if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 for(let i=0;i<22;i++){const c=document.createElement('div');c.className='confetti';c.style.left=Math.random()*100+'vw';c.style.background=['#b6a7ff','#b4e6d6','#f7cbd8','#ffe4ad'][i%4];c.style.animationDelay=Math.random()*.45+'s';document.body.append(c);setTimeout(()=>c.remove(),2100)}
}
function showModal(title,body,buttons,extra){
 dismissKeyboard();$('modalTitle').textContent=title;$('modalBody').textContent=body;
 const ex=$('modalExtra');ex.replaceChildren();if(extra)extra(ex);
 $('modalButtons').replaceChildren();
 buttons.forEach(([label,cb],i)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.className=i===buttons.length-1?'accent':'';b.onclick=cb;$('modalButtons').append(b)});
 $('modal').classList.add('open');$('modal').setAttribute('aria-hidden','false');
}
function closeModal(){$('modal').classList.remove('open');$('modal').setAttribute('aria-hidden','true')}
function showClues(){
 showModal('All clues','Choose any clue to jump straight to its answer.',[['Close',closeModal]],extra=>{
  const list=document.createElement('div');list.className='clue-list';
  for(const direction of ['Across','Down']){
   const heading=document.createElement('h3');heading.textContent=direction;list.append(heading);
   entries.forEach((e,i)=>{if(e.direction!==direction)return;
    const b=document.createElement('button');b.className='clue-choice'+(i===entry?' active':'');
    const n=document.createElement('strong');n.textContent=e.number;
    const label=document.createElement('span');label.textContent=`${e.clue} (${e.answer.length})`;
    b.append(n,label);b.onclick=()=>{closeModal();chooseEntry(i,true)};list.append(b);
   });
  }
  extra.append(list);
 });
}
function showDailyMenu(){
 showModal('Today’s three editions','Choose a daily crossword. Each edition has separate progress.',[['Close',closeModal]],extra=>{
  const list=document.createElement('div');list.className='clue-list';
  for(const mode of ['classic','news','theme']){
   const spec=mode==='news'?{title:'In the News',description:'Fresh headlines when available · offline backup'}:dailyChoice(mode);
   const btn=document.createElement('button');btn.className='puzzle-choice';
   const left=document.createElement('span');left.textContent=spec.title;
   const right=document.createElement('small');right.textContent=completed.has(mode==='news'&&getCachedOnline('news',londonDay())?todayLiveKey(mode,londonDay()):`offline:${mode}:${londonDay()}`)?'✓ Complete':mode==='news'?(getCachedOnline('news',londonDay())?'Fresh':'Offline ready'):'Open';
   btn.append(left,right);btn.onclick=()=>loadDaily(mode);list.append(btn);
  }
  extra.append(list);
 });
}
function showPuzzles(){
 showModal('Choose a mini','Select a crossword. Completed puzzles can be replayed.',[['Close',closeModal]],extra=>{
  const list=document.createElement('div');list.className='clue-list';
  for(let i=1;i<=PUZZLE_LIMIT;i++){
    const b=document.createElement('button');b.className='puzzle-choice'+(i===number?' current':'');
    const title=document.createElement('span');title.textContent=`Mini crossword #${i}`;
    const state=document.createElement('small');state.textContent=completed.has('practice:'+i)?'✓ Completed':edition.mode==='archive'&&i===number?'Current':'Play';
    b.append(title,state);b.onclick=()=>load(i);list.append(b);
  }
  extra.append(list);
 });
}
function settings(){showModal('Little Crossword','A private-use crossword with three daily editions, five Across and five Down, saved progress and offline play. Classic draws from 24 checked minis. Themed has eight fully themed, verified grids. News clues link to multiple publishers when fresh headlines are available. Tap a square twice to switch direction.',[
 ['Close',closeModal],['More options',()=>showModal('Puzzle options','Choose what you want to clear.',[
  ['Clear word',()=>{
    if(!solved){for(const k of active().cells){delete filled[k]}cell=active().cells[0];save();render(true)}
    closeModal();
  }],
  ['Restart mini',()=>showModal('Restart crossword?','This clears the entire grid.',[
    ['Cancel',closeModal],['Restart',()=>{filled={};clueHints={};solved=false;completed.delete(edition.key);save();activateEdition(edition)}]
  ])]
 ])]
])}
function attachInput(){
 nativeInput.addEventListener('focus',()=>{
   if(solved)return;
   keyboardVisible=true;document.body.classList.add('keyboard-open');refreshKeyboardBar();resetNative();
 });
 nativeInput.addEventListener('blur',()=>{
   // Let touch-driven navigation finish before shifting the compact panel.
   setTimeout(()=>{if(document.activeElement!==nativeInput){keyboardVisible=false;document.body.classList.remove('keyboard-open');refreshKeyboardBar()}},85);
 });
 let ignoredInput=false;
 let recentHardwareDelete=0;
 nativeInput.addEventListener('beforeinput',e=>{
   const kind=e.inputType||'';
   const isDelete=kind==='deleteContentBackward'||kind==='deleteContentForward';
   if(isDelete){
     if(e.cancelable)e.preventDefault();else ignoredInput=true;
     // Some iOS keyboard versions dispatch both keydown and beforeinput.
     if(performance.now()-recentHardwareDelete>40)backspace();
     if(e.cancelable)resetNative();
     return;
   }
   if(kind.startsWith('insert')&&e.data){
     if(e.cancelable)e.preventDefault();else ignoredInput=true;
     insertString(e.data);
     if(e.cancelable)resetNative();
   }
 });
 nativeInput.addEventListener('input',()=>{
   if(ignoredInput){ignoredInput=false;resetNative();return}
   const value=nativeInput.value;
   const letters=value.replace(/\u200B/g,'');
   if(letters)insertString(letters);
   else if(value==='')backspace();
   resetNative();
 });
 nativeInput.addEventListener('keydown',e=>{
   if(e.key==='Backspace'||e.key==='Delete'){
     e.preventDefault();recentHardwareDelete=performance.now();backspace();resetNative();
   }else if(e.key==='Enter'){
     e.preventDefault();dismissKeyboard();
   }else if(e.key==='ArrowLeft'||e.key==='ArrowRight'){
     e.preventDefault();moveTo(active().cells.indexOf(cell)+(e.key==='ArrowLeft'?-1:1));
   }else if(e.key==='ArrowDown'||e.key==='ArrowUp'){
     e.preventDefault();toggle();
   }else if(e.key==='Tab'){
     e.preventDefault();change(e.shiftKey?-1:1);
   }
 });
 // External hardware keyboard, even with the software keyboard dismissed.
 document.addEventListener('keydown',e=>{
   if(e.target===nativeInput||$('modal').classList.contains('open')){
      if(e.key==='Escape')closeModal();return;
   }
   if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement)return;
   if(/^[a-z]$/i.test(e.key)){e.preventDefault();insert(e.key.toUpperCase())}
   else if(['Backspace','Delete'].includes(e.key)){e.preventDefault();backspace()}
   else if(e.key==='ArrowLeft'||e.key==='ArrowRight'){
     e.preventDefault();moveTo(active().cells.indexOf(cell)+(e.key==='ArrowLeft'?-1:1));
   }
 });
}
attachInput();
for(const id of ['prev','next','direction','hint','keyboardToggle'])rememberKeyboard($(id));
$('prev').onclick=()=>change(-1,keyboardBeforeTap($('prev')));
$('next').onclick=()=>change(1,keyboardBeforeTap($('next')));
$('direction').onclick=()=>toggle(keyboardBeforeTap($('direction')));
$('hint').onclick=()=>hint(keyboardBeforeTap($('hint')));$('check').onclick=check;
$('keyboardToggle').onclick=()=>keyboardBeforeTap($('keyboardToggle'))?dismissKeyboard():focusNative();
$('daily').onclick=showDailyMenu;
$('random').onclick=()=>{const next=PUZZLE_LIMIT===1?1:(number+1+Math.floor(Math.random()*(PUZZLE_LIMIT-1))-1)%PUZZLE_LIMIT+1;load(next)};
document.querySelectorAll('[data-edition]').forEach(b=>b.onclick=()=>loadDaily(b.dataset.edition));
$('puzzles').onclick=showPuzzles;$('puzzleBtn').onclick=showPuzzles;$('showClues').onclick=showClues;$('settingsBtn').onclick=settings;
$('modal').onclick=e=>{if(e.target===$('modal'))closeModal()};
$('clueArea').addEventListener('touchstart',e=>{touchingClueStart=e.touches[0]?.clientX??null},{passive:true});
$('clueArea').addEventListener('touchend',e=>{if(touchingClueStart===null)return;const dx=(e.changedTouches[0]?.clientX??touchingClueStart)-touchingClueStart;touchingClueStart=null;if(Math.abs(dx)>48)change(dx<0?1:-1)},{passive:true});
window.addEventListener('pageshow',()=>{$('installNote').hidden=window.matchMedia('(display-mode: standalone)').matches||navigator.standalone===true});
if('serviceWorker'in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('./sw.js').catch(console.warn);
loadDaily('classic');
