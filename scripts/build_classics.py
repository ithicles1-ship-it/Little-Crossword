#!/usr/bin/env python3
"""Build 100 compact crosswords with exactly 1000 distinct answer words.

The words are drawn from an offline frequency lexicon. Clue descriptions are
from Wiktionary via open-dictionary; see data/CLASSIC-SOURCES.md for attribution.
No paid API, user account, or AI key required.
"""
import concurrent.futures
import collections
import html
import json
import random
import re
import time
import urllib.request
from pathlib import Path
from textblob import en

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"data"/"classics100.json"
SHAPES=[
 [".....#.",".#.##..",".#.##..","....#..","....#..",".##....","#.....#"],
 ["#......",".##....","..#.##.","..#....","..#...#","....#.#","..###.#"],
 ["......#","..#####","....##.","....#..",".#.#...",".#.....","##.##.."],
]
BANNED=set("""natasha pierre andrew sonya princess rostov anatole napoleon bolkonski
denisov nicholas kutuzov prince had said got get did can are has was his her him
the who its may not will then than once been all just very also only emperor
captain russian french mariya saint xxx www intima septa russe pseudo coli tonsil
veldt gypsy cytst cyst cysts plasma stasis lesion lesions rubles archons
sabre tetra gentry dowry rouble ruble liege mesentery""".split())
SKIP_SENSE=("obsolete","archaic","rare","dated","historical","vulgar","offensive",
            "military jargon","abbreviation of","a surname","a given name",
            "chiefly", "an archaic")
PAT_WORD=re.compile(r"[A-Za-z][A-Za-z'-]*")
rng_seed=20261107

def slots(shape):
    R,C=len(shape),len(shape[0]);out=[]
    for r in range(R):
        for c in range(C):
            if shape[r][c]=="#":continue
            for direction,dr,dc in (("Across",0,1),("Down",1,0)):
                if direction=="Across" and c and shape[r][c-1]!="#":continue
                if direction=="Down" and r and shape[r-1][c]!="#":continue
                rr,cc=r,c;cells=[]
                while rr<R and cc<C and shape[rr][cc]!="#":
                    cells.append(rr*C+cc);rr+=dr;cc+=dc
                if len(cells)>=3:out.append((direction,cells))
    assert len(out)==10 and sum(x[0]=="Across" for x in out)==5
    return out

def build_answers():
    frequencies={w.upper():freq for w,freq in en.spelling.items()
                 if re.fullmatch(r"[a-z]{3,6}",w) and freq>=4 and w not in BANNED
                 and en.lexicon.get(w,"").startswith(("NN","VB","JJ","RB"))}
    forbidden=set()
    pools={n:sorted((w for w in frequencies if len(w)==n),key=lambda w:(-frequencies[w],w)) for n in range(3,7)}
    def fill(shape,slot_list,puzzle_number,attempt):
        cells=[""]*(len(shape)*len(shape[0]))
        values=[None]*10;inside=set();calls=0
        random_state=random.Random(100000+puzzle_number*37+attempt*119)
        def choices(slot):
            pattern=[cells[pos] for pos in slot[1]]
            return [w for w in pools[len(pattern)]
                    if w not in forbidden and w not in inside
                    and all(not letter or letter==w[i] for i,letter in enumerate(pattern))]
        def place(depth):
            nonlocal calls
            calls+=1
            if depth==10:return True
            if calls>950:return False
            available=[]
            for idx,slot in enumerate(slot_list):
                if values[idx] is not None:continue
                opts=choices(slot)
                if not opts:return False
                available.append((len(opts),-len(slot[1]),idx,opts))
            available.sort(key=lambda v:(v[0],v[1]))
            _,_,idx,options=available[0]
            offers=options[:75]
            offers.sort(key=lambda w:options.index(w)*.032+random_state.random()*3)
            for word in offers:
                changed=[]
                for i,pos in enumerate(slot_list[idx][1]):
                    if not cells[pos]:cells[pos]=word[i];changed.append(pos)
                inside.add(word);values[idx]=word
                if place(depth+1):return True
                values[idx]=None;inside.remove(word)
                for pos in changed:cells[pos]=""
            return False
        return values if place(0) else None
    puzzles=[]
    for n in range(100):
        found=None
        for attempt in range(80):
            shape=SHAPES[(n*17+attempt*37)%len(SHAPES)]
            found=fill(shape,slots(shape),n,attempt)
            if found:
                assert not forbidden.intersection(found)
                forbidden.update(found)
                puzzles.append({"shape":shape,"answers":found})
                break
        if not found:raise RuntimeError("Unable to produce crossword #"+str(n+1))
    answers=[w for puzzle in puzzles for w in puzzle["answers"]]
    assert len(answers)==1000 and len(set(answers))==1000
    return puzzles

def plain(value):
    text=html.unescape(re.sub(r"<[^>]*>","",str(value or "")))
    return re.sub(r"\s+"," ",text).strip()

def dictionary_prefix(prefix):
    url=("https://raw.githubusercontent.com/mhollingshead/open-dictionary/"
         "main/api/"+prefix[0]+"/"+prefix+".json")
    req=urllib.request.Request(url,headers={"User-Agent":"LittleCrossword/1.0","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=18) as response:
            return prefix,json.loads(response.read(1500000))
    except Exception as e:
        print("Definition group unavailable:",prefix,str(e),flush=True)
        return prefix,{}

def definitions(words):
    prefixes=sorted({w[:2].lower() for w in words})
    print("Reading",len(prefixes),"open-dictionary groups",flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        pages=dict(executor.map(dictionary_prefix,prefixes))
    result={}
    for word in words:
        entry=pages.get(word[:2].lower(),{}).get(word.lower(),{})
        available=[]
        for etymology in entry.get("etymologies",[]):
            for part in etymology.get("partsOfSpeech",[]):
                pos=part.get("partOfSpeech","word")
                for sense in part.get("senses",[]):
                    meaning=plain(sense.get("sense",""))
                    if 12<=len(meaning)<=180 and not any(k in meaning.lower()[:35] for k in SKIP_SENSE):
                        if re.search(r"\b"+re.escape(word)+r"\b",meaning,re.I):continue
                        examples=[plain(x) for x in sense.get("examples",[]) if isinstance(x,str)]
                        available.append((meaning,pos,examples))
        result[word]=available
    return result

def clue_pair(word,senses,old_bank):
    if not senses and word in old_bank:
        return old_bank[word]
    if not senses:
        # A transparent, genuinely solvable wordplay fallback, not a fake definition.
        vowels="".join(c for c in word if c in "AEIOU")
        clue=f"Everyday word with {len(word)} letters, containing the vowels {', '.join(vowels) if vowels else 'none'} in that order"
        hint=f"Its first letter is {word[0]}; it ends with {word[-1]}."
        return [clue,hint]
    meaning,pos,examples=senses[0]
    clue=meaning[0].upper()+meaning[1:].rstrip(".")+"." if meaning else f"A {pos.lower()}."
    # Prefer a contextual example with the missing word; this helps instead of giving a letter.
    hint=None
    for sentence in examples:
        if re.search(r"\b"+re.escape(word)+r"\b",sentence,re.I) and 17<len(sentence)<155:
            masked=re.sub(r"\b"+re.escape(word)+r"\b","____",sentence,flags=re.I)
            hint="Complete the sentence: "+masked
            break
    if not hint:
        alt=next((m for m,p,e in senses[1:] if m.casefold()!=meaning.casefold()
                 and not re.search(r"\b"+re.escape(word)+r"\b",m,re.I)),None)
        if alt:hint="Another use: "+alt.rstrip(".")+"."
        else:hint="Think of a "+pos.lower()+" in ordinary conversation: "+meaning.rstrip(".")+"."
    return [clue[:170],hint[:190]]

def main():
    puzzles=build_answers()
    print("Generated",len(puzzles),"valid grids with 1000 disjoint answers",flush=True)
    src=(ROOT/"generator.js").read_text(encoding="utf-8")
    match=re.search(r"const CLUE_BANK=(\{.*?\});\s*const PUZZLE_LIMIT=",src,re.S)
    existing=json.loads(match.group(1)) if match else {}
    unique={w for p in puzzles for w in p["answers"]}
    dictionary=definitions(unique)
    fallback_count=0
    for puzzle in puzzles:
        pairs=[clue_pair(word,dictionary.get(word,[]),existing) for word in puzzle["answers"]]
        for word,(clue,hint) in zip(puzzle["answers"],pairs):
            if not dictionary.get(word,[]):fallback_count+=1
            if re.search(r"\b"+re.escape(word)+r"\b",clue,re.I):
                raise ValueError("Clue leaks answer: "+word)
        puzzle["clues"]=[x[0] for x in pairs]
        puzzle["hints"]=[x[1] for x in pairs]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(puzzles,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("Wrote",OUT,"puzzles",len(puzzles),"fallback definitions",fallback_count,"bytes",OUT.stat().st_size,flush=True)

if __name__=="__main__":main()
