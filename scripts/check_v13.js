'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const generator=require('../generator.js');
const classic=JSON.parse(fs.readFileSync('data/classics100.json','utf8'));
const seen=new Set();
const allClues=new Set();
assert.equal(classic.length,100);
classic.forEach((spec,i)=>{
  assert.equal(spec.shape.length,5,'Classic '+(i+1)+' must have five rows');
  assert(spec.shape.every(row=>row.length===5),'Classic '+(i+1)+' must have five columns');
  for(let row=0;row<5;row++){
    const stripped=spec.shape[row].replace(/^#+|#+$/g,'');
    assert(stripped.length>=3&&stripped.length<=5&&[...stripped].every(ch=>ch==='.'),'Classic '+(i+1)+' contains a gap in a row');
  }
  for(let col=0;col<5;col++){
    const column=spec.shape.map(row=>row[col]).join('').replace(/^#+|#+$/g,'');
    assert(column.length>=3&&column.length<=5&&[...column].every(ch=>ch==='.'),'Classic '+(i+1)+' contains a gap in a column');
  }
  const mini=generator.parseMini(spec);
  assert.equal(mini.entries.filter(x=>x.direction==='Across').length,5,'Classic '+(i+1)+' Across count');
  assert.equal(mini.entries.filter(x=>x.direction==='Down').length,5,'Classic '+(i+1)+' Down count');
  assert.equal(spec.answers.length,10,'Classic '+(i+1)+' answer count');
  for(const answer of spec.answers){
    assert(!seen.has(answer),'Answer '+answer+' reused in Classic '+(i+1));
    seen.add(answer);
  }
  for(const e of mini.entries){
    assert(e.clue.length>=5&&e.hint.length>=5,'Missing clue/hint for '+e.answer);
    assert(!e.clue.startsWith('Everyday word with'),'Uncurated clue for '+e.answer);
    assert(!e.hint.startsWith('Its first letter'),'Mechanical hint for '+e.answer);
    assert(!new RegExp('\\b'+e.answer+'\\b','i').test(e.clue),'Answer leaked in clue for '+e.answer);
    const normalized=e.clue.trim().toLocaleLowerCase('en-GB');
    assert(!allClues.has(normalized),'Duplicate clue for '+e.answer);
    allClues.add(normalized);
  }
});
assert.equal(seen.size,1000);
assert.equal(allClues.size,1000);
const sandbox={};
vm.runInNewContext(fs.readFileSync('themes.js','utf8')+';globalThis.primary=THEMED_PACKS;',sandbox);
vm.runInNewContext(fs.readFileSync('extra-themes.js','utf8')+';globalThis.extra=EXTRA_MONTHLY_THEMES;',sandbox);
for(const p of [...sandbox.primary,...sandbox.extra]){
  const mini=generator.parseMini(p);
  assert.equal(mini.entries.length,10,p.title);
}
for(const file of ['app.js','menu.js','daily.js','extra-themes.js','generator.js']){
  new vm.Script(fs.readFileSync(file,'utf8'),{filename:file});
}
console.log(JSON.stringify({status:'pass',classicPuzzles:classic.length,uniqueAnswers:seen.size,monthlyThemeGrids:sandbox.primary.length+sandbox.extra.length,allCluesPresent:true,allIntersectionsValid:true}));
