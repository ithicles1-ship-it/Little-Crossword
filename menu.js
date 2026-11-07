'use strict';
// Personal Edition home, numbered library, news calendar and monthly theme collections.
// The original crossword engine remains responsible for typing, checking and saved progress.
(function(){
 const root=document.querySelector('main.app');
 const home=document.createElement('main');
 home.id='crosswordHome';home.className='crossword-home';
 document.body.insertBefore(home,root);
 root.hidden=true;
 const nowDay=()=>londonDay();
 const months=['January','February','March','April','May','June','July','August','September','October','November','December'];
 const monthSpecs=[
   {title:'Riddle Answers',pack:THEMED_PACKS[1]},
   {title:'Animals',pack:THEMED_PACKS[2]},
   {title:'In the Garden',pack:THEMED_PACKS[6]},
   {title:'Music',pack:THEMED_PACKS[7]},
   {title:'Food & Drink',pack:THEMED_PACKS[3]},
   {title:'Summer',pack:THEMED_PACKS[0]},
   {title:'At Sea',pack:THEMED_PACKS[4]},
   {title:'Holiday Escapes',pack:THEMED_PACKS[0]},
   {title:'School Days',pack:EXTRA_MONTHLY_THEMES[0]},
   {title:'Halloween Night',pack:EXTRA_MONTHLY_THEMES[1]},
   {title:'Science Lab',pack:EXTRA_MONTHLY_THEMES[2]},
   {title:'Christmas',pack:THEMED_PACKS[5]}
 ];
 let library=null,loading=null,view='home',calendarMonth=new Date(nowDay()+'T12:00:00Z'),newsSelected=nowDay();
 let lastPlayable=edition;
 const textNode=(tag,klass,txt)=>{const x=document.createElement(tag);if(klass)x.className=klass;x.textContent=txt;return x;};
 const button=(label,klass,fn)=>{const b=document.createElement('button');b.type='button';b.className=klass;b.textContent=label;b.onclick=fn;return b};
 const clear=()=>home.replaceChildren();
 function screen(title,subtitle,back){
   clear();
   const top=document.createElement('header');top.className='home-heading';
   const left=document.createElement('div');
   left.append(textNode('div','home-eyebrow','✦ LITTLE CROSSWORD'),textNode('h1','home-title',title),textNode('p','home-desc',subtitle));
   top.append(left);
   if(back)top.append(button('← Back','home-back',back));
   home.append(top);return home;
 }
 function enter(which){
   if(which)activateEdition(which);
   lastPlayable=edition;home.hidden=true;root.hidden=false;
   window.scrollTo(0,0);
 }
 function exit(){dismissKeyboard();root.hidden=true;home.hidden=false;renderHome();window.scrollTo(0,0)}
 const safeDate=d=>/^\d{4}-\d\d-\d\d$/.test(d)&&!Number.isNaN(Date.parse(d+'T12:00:00Z'));
 const currentYear=()=>+nowDay().slice(0,4);
 async function loadLibrary(){
   if(library)return library;
   if(loading)return loading;
   loading=(async()=>{
     const response=await fetch('./data/classics100.json',{cache:'force-cache'});
     if(!response.ok)throw Error('The verified collection has not finished publishing');
     const puzzles=await response.json();
     if(!Array.isArray(puzzles)||puzzles.length!==100)throw Error('Expected exactly 100 verified puzzles');
     const all=new Set();
     puzzles.forEach((p,i)=>{
       const mini=parseMini(p);
       if(mini.entries.length!==10)throw Error('Puzzle '+(i+1)+' is incomplete');
       for(const answer of p.answers){if(all.has(answer))throw Error('Answer repeated across Classic puzzles: '+answer);all.add(answer)}
     });
     if(all.size!==1000)throw Error('Classic collection must have 1,000 different answers');
     library=puzzles;return library;
   })();
   try{return await loading}finally{loading=null}
 }
 function makeClassics(){
   view='classics';
   screen('Classic','100 small crosswords. Every answer is used once in the complete collection.',renderHome);
   const intro=textNode('div','home-section-heading','YOUR CLASSIC COLLECTION');
   const status=textNode('p','home-footnote','Loading your verified puzzles…');home.append(intro,status);
   const list=document.createElement('div');list.className='classic-wall';home.append(list);
   loadLibrary().then(puzzles=>{
     if(view!=='classics')return;
     status.textContent='100 minis · 1,000 non-repeating answers · 5 Across / 5 Down';
     for(let i=0;i<100;i++){
       const id=i+1,puzzle=puzzles[i];
       const b=button(String(id).padStart(2,'0'),'classic-tile',()=>{
         enter({mode:'classic',source:'library',key:'classic-library-v1:'+id,number:id,date:nowDay(),title:'Classic #'+id,
           description:'One of 100 original minis · all new answers',spec:puzzle});
       });
       b.title='Classic puzzle '+id;
       if(completed.has('classic-library-v1:'+id)){b.classList.add('done');b.append(textNode('small','tile-check','✓'))}
       list.append(b);
     }
   }).catch(err=>{if(view!=='classics')return;status.textContent='The puzzle collection could not be loaded. Reopen the app with internet once, then try again. '+err.message});
 }
 function renderHome(){
   view='home';screen('Choose your crossword','A little challenge for whenever you have a moment.');
   const wrapper=document.createElement('div');wrapper.className='home-editions';
   const cards=[
     ['01','Classic','100 unique minis','Work through a numbered library of familiar answers.',makeClassics],
     ['02','In the News','The headline calendar','Pick a date and solve clues inspired by real news.',()=>makeNewsCalendar(nowDay())],
     ['03','Themed','A different topic each month','Explore the months, with a verified themed feature.',makeThemeMonths]
   ];
   for(const [no,title,eyebrow,desc,fn]of cards){
     const b=button('','home-edition',fn);
     b.append(textNode('span','home-edition-num',no));
     const copy=document.createElement('span');copy.className='home-edition-copy';
     copy.append(textNode('strong','home-edition-title',title),textNode('em','home-edition-sub',eyebrow),textNode('span','home-edition-description',desc));
     b.append(copy,textNode('span','home-arrow','›'));wrapper.append(b);
   }
   home.append(wrapper);
   if(lastPlayable?.key)home.append(button('↗ Resume last crossword','home-resume',()=>enter()));
   home.append(textNode('p','home-footer','Designed for your iPhone · Saved automatically · No account or subscription'));
 }
 function makeNewsCalendar(date=nowDay()){
   view='news';
   const use=safeDate(date)?date:nowDay();
   newsSelected=use;
   const y=+use.slice(0,4),m=+use.slice(5,7)-1;
   calendarMonth=new Date(Date.UTC(y,m,1,12));
   drawNewsCalendar();
 }
 function drawNewsCalendar(){
   screen('In the News','Choose a day to open its published headline crossword.',renderHome);
   addCalendar(home,calendarMonth,nowDay(),d=>openNewsDate(d),'news');
   home.append(textNode('p','home-footnote','Headline puzzles are available only for dates successfully published by the news updater. Older dates without an archive cannot be reconstructed.'));
   const quick=button('Read today’s headlines','home-primary',()=>openNewsDate(nowDay()));home.append(quick);
 }
 function addCalendar(parent,month,maximum,onDay,kind){
   const y=month.getUTCFullYear(),m=month.getUTCMonth();
   const titleRow=document.createElement('div');titleRow.className='calendar-head';
   const prev=button('‹','calendar-arrow',()=>{calendarMonth=new Date(Date.UTC(y,m-1,1,12));if(kind==='news')drawNewsCalendar();else drawThemeDays(m,y)});
   const next=button('›','calendar-arrow',()=>{calendarMonth=new Date(Date.UTC(y,m+1,1,12));if(kind==='news')drawNewsCalendar();else drawThemeDays(m,y)});
   next.disabled=(new Date(Date.UTC(y,m+1,1,12))>new Date(nowDay()+'T12:00:00Z'));
   titleRow.append(prev,textNode('strong','calendar-month',months[m]+' '+y),next);parent.append(titleRow);
   const grid=document.createElement('div');grid.className='calendar-grid';
   for(const d of ['M','T','W','T','F','S','S'])grid.append(textNode('span','calendar-weekday',d));
   const first=(new Date(Date.UTC(y,m,1,12)).getUTCDay()+6)%7;
   for(let i=0;i<first;i++)grid.append(textNode('span','calendar-blank',''));
   const length=new Date(Date.UTC(y,m+1,0,12)).getUTCDate();
   for(let day=1;day<=length;day++){
     const date=y+'-'+String(m+1).padStart(2,'0')+'-'+String(day).padStart(2,'0');
     const b=button(String(day),'calendar-day'+(date===nowDay()?' today':'')+(date===newsSelected?' active':''),()=>onDay(date));
     const future=date>maximum;
     if(future)b.disabled=true;
     if(kind==='theme')b.disabled=day!==1||future;
     if(completed.has('published:news:'+date)||completed.has('theme-month-feature:'+y+'-'+String(m+1).padStart(2,'0')))b.classList.add('complete');
     grid.append(b);
   }
   parent.append(grid);
 }
 async function openNewsDate(date){
   if(!safeDate(date)||date>nowDay())return;
   newsSelected=date;
   const candidate=getCachedOnline('news',date);
   if(candidate){try{enter(candidate);return}catch(e){console.warn('Cached edition rejected',e)}}
   try{
     let response=await fetch('./data/news/'+date+'.json',{cache:'no-store'});
     if(!response.ok&&date===nowDay())response=await fetch('./data/news.json',{cache:'no-store'});
     if(!response.ok)throw Error('No published headlines for this date');
     const payload=await response.json();
     const which=onlineEditionFromPayload(payload,'news',date);
     cacheOnline('news',date,which);
     enter(which);
   }catch(e){
     showModal('No crossword published for '+prettyDay(date),
       'The news updater has no archived crossword for that day. Try another date or today’s live edition.',
       [['Back to calendar',closeModal],['Today',()=>{closeModal();openNewsDate(nowDay())}]]);
   }
 }

 function newsPickerModal(date=nowDay()){
   const chosen=safeDate(date)?date:nowDay();
   let month=new Date(chosen+'T12:00:00Z');
   month=new Date(Date.UTC(month.getUTCFullYear(),month.getUTCMonth(),1,12));
   showModal('News calendar','Pick the date of a published headline crossword.',[['Close',closeModal]],extra=>{
     function draw(){
       extra.replaceChildren();
       const y=month.getUTCFullYear(),m=month.getUTCMonth();
       const controls=document.createElement('div');controls.className='calendar-head';
       const previous=button('‹','calendar-arrow',()=>{month=new Date(Date.UTC(y,m-1,1,12));draw()});
       const following=button('›','calendar-arrow',()=>{month=new Date(Date.UTC(y,m+1,1,12));draw()});
       following.disabled=new Date(Date.UTC(y,m+1,1,12))>new Date(nowDay()+'T12:00:00Z');
       controls.append(previous,textNode('strong','calendar-month',months[m]+' '+y),following);extra.append(controls);
       const calendar=document.createElement('div');calendar.className='calendar-grid';
       ['M','T','W','T','F','S','S'].forEach(x=>calendar.append(textNode('span','calendar-weekday',x)));
       for(let k=0;k<(new Date(Date.UTC(y,m,1)).getUTCDay()+6)%7;k++)calendar.append(textNode('span','calendar-blank',''));
       for(let k=1;k<=new Date(Date.UTC(y,m+1,0)).getUTCDate();k++){
         const day=y+'-'+String(m+1).padStart(2,'0')+'-'+String(k).padStart(2,'0');
         const b=button(String(k),'calendar-day'+(day===nowDay()?' today':''),()=>{closeModal();openNewsDate(day)});
         b.disabled=day>nowDay();
         calendar.append(b);
       }
       extra.append(calendar);
     }
     draw();
   });
 }
 function makeThemeMonths(){
   view='months';screen('Themed','Explore a new subject every month.',renderHome);
   const labels=document.createElement('div');labels.className='month-list';
   monthSpecs.forEach((spec,m)=>{
     const b=button('','month-tile',()=>makeThemeCalendar(m));
     b.append(textNode('small','month-index',String(m+1).padStart(2,'0')),textNode('strong','month-name',months[m]),textNode('span','month-topic',spec.title),textNode('span','home-arrow','›'));
     labels.append(b);
   });
   home.append(labels);
   home.append(textNode('p','home-footnote','Each month currently includes one verified topic-specific crossword. Additional daily entries will be added only when their answers and clues are ready.'));
 }
 function makeThemeCalendar(m){
   view='theme-days';const spec=monthSpecs[m];
   const year=currentYear();
   screen(spec.title,months[m]+' · Topic-first crossword collection',makeThemeMonths);
   const card=document.createElement('div');card.className='featured-theme';
   card.append(textNode('span','home-edition-num','MONTHLY FEATURE'),textNode('strong','home-edition-title',spec.title),textNode('p','home-edition-description',spec.pack.description||'Ten answers that all fit the theme.'));
   const key='theme-month-feature:'+year+'-'+String(m+1).padStart(2,'0');
   card.append(button(completed.has(key)?'✓ Replay featured mini':'Play featured mini','home-primary',()=>enter({
     mode:'theme',source:'offline',date:year+'-'+String(m+1).padStart(2,'0')+'-01',key,number:1,
     title:spec.title,description:'A featured crossword for '+months[m],spec:spec.pack
   })));
   home.append(card);
   home.append(textNode('p','home-footnote','The monthly calendar will expand when more fully themed daily puzzles are curated. We will not silently reuse unrelated answers as a new daily crossword.'));
 }
 const backButton=button('←','game-home-button',exit);backButton.setAttribute('aria-label','Back to the main menu');
 root.querySelector('.top-actions')?.prepend(backButton);
 // Replace old archive links with the new coherent main menu.
 document.getElementById('puzzleBtn').onclick=()=>{
   if(edition.mode==='news'){newsPickerModal(edition.date||nowDay());return;}
   else if(edition.mode==='theme')makeThemeCalendar(monthSpecs.findIndex(x=>x.title===edition.title)>=0?monthSpecs.findIndex(x=>x.title===edition.title):(+edition.date?.slice(5,7)||1)-1);
   else makeClassics();
   dismissKeyboard();root.hidden=true;home.hidden=false;
 };
 document.getElementById('daily').onclick=exit;
 document.getElementById('puzzles').onclick=()=>{dismissKeyboard();root.hidden=true;home.hidden=false;makeClassics()};
 document.getElementById('random').onclick=()=>{dismissKeyboard();root.hidden=true;home.hidden=false;makeClassics()};
 root.querySelectorAll('[data-edition]').forEach(b=>b.onclick=()=>{
   dismissKeyboard();root.hidden=true;home.hidden=false;
   if(b.dataset.edition==='classic')makeClassics();
   else if(b.dataset.edition==='news')makeNewsCalendar(nowDay());
   else makeThemeMonths();
 });
 window.addEventListener('popstate',()=>{if(!home.hidden)renderHome()});
 renderHome();
})();
