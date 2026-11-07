'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const context=vm.createContext({console});
for(const file of ['clue-alternates.js','generator.js','themes.js','daily.js']){
  vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),context,{filename:file});
}
const run=code=>vm.runInContext(code,context);
const puzzles=run('PUZZLES'),themes=run('THEMED_PACKS'),limit=run('PUZZLE_LIMIT');
const seenClues=new Set(),seenHints=new Set(),seenAnswers=new Set();
const normalize=s=>s.trim().toLocaleLowerCase('en-GB').replace(/[.?!,;:]+$/,'');
function validate(spec,name){
  context.spec=spec;
  const puzzle=run('parseMini(spec)');
  const across=puzzle.entries.filter(e=>e.direction==='Across');
  const down=puzzle.entries.filter(e=>e.direction==='Down');
  if(across.length!==5||down.length!==5)throw Error(name+': expected five Across and five Down');
  if(new Set(puzzle.entries.map(e=>e.answer)).size!==10)throw Error(name+': repeated answer in one puzzle');
  for(const e of puzzle.entries){
    if(!e.clue.trim()||!e.hint.trim())throw Error(name+': missing clue/hint');
    if(new RegExp('\\b'+e.answer+'\\b','i').test(e.clue))throw Error(name+': answer appears in clue '+e.answer);
  }
  return puzzle;
}
for(let i=1;i<=limit;i++){
  const puzzle=run('createCrossword('+i+')');
  validate({shape:puzzles[i-1].shape,answers:puzzle.entries.map(e=>e.answer),clues:puzzle.entries.map(e=>e.clue),hints:puzzle.entries.map(e=>e.hint)},'Practice #'+i);
  for(const e of puzzle.entries){
    const clue=normalize(e.clue),hint=normalize(e.hint);
    if(seenClues.has(clue))throw Error('Repeated practice clue: '+e.clue);
    if(seenHints.has(hint))throw Error('Repeated practice hint: '+e.hint);
    seenClues.add(clue);seenHints.add(hint);seenAnswers.add(e.answer);
  }
}
for(const theme of themes)validate(theme,theme.title);
const start=new Date('2026-11-08T00:00:00Z');
const recent=[];
const classicIds=[];
for(let i=0;i<24;i++){
  const day=new Date(start.getTime()+86400000*i).toISOString().slice(0,10);
  const classic=run("dailyChoice('classic',"+JSON.stringify(day)+")");
  const theme=run("dailyChoice('theme',"+JSON.stringify(day)+")");
  const words=puzzles[classic.number-1].answers;
  const todayTheme=new Set(theme.spec.answers);
  if(words.some(w=>todayTheme.has(w)))throw Error(day+': Classic and Themed share an answer');
  if(recent.length&&words.some(w=>recent[recent.length-1].includes(w)))throw Error(day+': consecutive Classic answers overlap');
  recent.push(words);classicIds.push(classic.number);
}
assert.equal(new Set(classicIds).size,24,'Classic must use all 24 grids before repeating');
assert.equal(seenClues.size,limit*10);
console.log('Crossword QA passed:',JSON.stringify({classicPuzzles:limit,themedPuzzles:themes.length,distinctClassicAnswers:seenAnswers.size,distinctClues:seenClues.size,distinctHints:seenHints.size,cycle:classicIds}));
