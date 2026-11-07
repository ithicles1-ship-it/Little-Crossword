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
# Dense 5 × 5 layouts with exactly five Across and five Down.
# Every row and column has one uninterrupted answer; no isolated islands or gaps.
BANNED=set("""natasha pierre andrew sonya princess rostov anatole napoleon bolkonski
denisov nicholas kutuzov prince his her him was had said got get did can are
has the who its may not will then than once been all just very also only
emperor captain russian french mariya saint xxx www intima septa russe pseudo
coli tonsil veldt gypsy cytst cyst cysts plasma stasis lesion lesions rubles
archons sabre tetra gentry dowry rouble ruble liege mesentery didn lise
nigga spic spick nigger chink fag faggot slut bitch porn fuck shit yyy yyyy
strt knite wo haw wohaw litle maget gorup faier nise pra i prai
ters wree yeard heare orney erned anye seein ash am asham fu er fuer
staf triol unhip atune etym cyber cyber cobol nft php ftp css xml
cials durin eies verie boite owne shewe onleh witha selle tagua inti riche entre imma

avec verso versa utero niger negro monei cocao ovata wanna wanta parte
unnnt len dost inapt rec com thy pas o paso USSR ussr cole

javascript jpeg json sql api url app apps www http https catty iam icee
""".split())
# A few everyday short words missing from the historical spelling corpus.
SAFE_THREE=set("""ads app bio boo bop bra bro bum bun cog coy cud cue doc dud
duo eel eke elk fin flu fry gab gel gob goo gym hex hob hoe hog hub ilk irk
jab jag jig jog lag lob lop lug lye maw mew mom mow mum nab nil oaf oat pap
pep pic pod pry pun pup rap rig sag sax sis sod sop soy spa tab tad tan tee
tot ups urn vet woo yen yip yuk zap zoo""".split())

def compact_shapes():
    """All connected 5×5 row/column-convex puzzles with 10 entries."""
    import itertools
    row_options=["#"*off+"."*size+"#"*(5-off-size)
                 for size in (3,4,5) for off in range(6-size)]
    designs=[]
    for shape in itertools.product(row_options,repeat=5):
        cols=["".join(row[c] for row in shape) for c in range(5)]
        if any(col.count(".")<3 or "#" in col.strip("#") for col in cols):
            continue
        lengths=[row.count(".") for row in shape]+[col.count(".") for col in cols]
        if lengths.count(3)>2 or sum(lengths)<38:continue
        designs.append(list(shape))
    if len(designs)<20:raise RuntimeError("Compact shape catalogue is unexpectedly small")
    return designs

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
    import collections
    common_path=ROOT/"data"/"common-10000-short.txt"
    common=[w.strip() for w in common_path.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.startswith("#")]
    rankings={word.upper():i for i,word in enumerate(common)}
    frequencies={w.upper():freq for w,freq in en.spelling.items()
        if re.fullmatch(r"[a-z]{3,5}",w) and freq>=1 and w not in BANNED
        and en.lexicon.get(w,"").startswith(("NN","VB","JJ","RB"))}
    for w,pos in en.lexicon.items():
        if not re.fullmatch(r"[a-z]{3,5}",w) or w in BANNED:
            continue
        if not pos.startswith(("NN","VB","JJ","RB")):continue
        if (w in SAFE_THREE and len(w)==3) or (len(w)>3 and w.upper() in rankings):
            frequencies.setdefault(w.upper(),1)
    # The familiar-word frequency list takes priority over technical dictionary fill.
    def value(w):
        rank=rankings.get(w,20000)
        familiar=10000/(rank+200) if rank<20000 else 0
        return familiar+__import__("math").log1p(frequencies[w])*1.8
    pools={n:sorted((w for w in frequencies if len(w)==n),key=lambda w:(-value(w),w))
           for n in (3,4,5)}
    lookup={n:[collections.defaultdict(set) for _ in range(n)] for n in (3,4,5)}
    for n,words in pools.items():
        for w in words:
            for j,ch in enumerate(w):lookup[n][j][ch].add(w)
    print("Compact word pools:",{n:len(words) for n,words in pools.items()},flush=True)
    shapes=compact_shapes()
    shape_info=[]
    for shape in shapes:
        grid_slots=slots(shape)
        # Use Across then Down for stable generation. Convert back to the actual
        # numbered crossword's row-major ordering before writing the puzzle.
        words_slots=sorted(grid_slots,key=lambda slot:(slot[0]!="Across",slot[1][0]))
        shape_info.append((shape,grid_slots,words_slots))
    used=set();solutions=[]
    def fill(selected,seed,maxcalls):
        grid=[""]*25;chosen=[None]*10;inside=set();calls=0
        rng=random.Random(seed)
        def candidates(slot):
            cs=slot[1];n=len(cs);pattern=[grid[i] for i in cs]
            matches=[lookup[n][j][ch] for j,ch in enumerate(pattern) if ch]
            if not matches:
                return [w for w in pools[n] if w not in used and w not in inside]
            common_matches=set.intersection(*sorted(matches,key=len))
            return [w for w in common_matches if w not in used and w not in inside]
        def search(depth):
            nonlocal calls
            calls+=1
            if depth==10:return True
            if calls>=maxcalls:return False
            options=[]
            for i,slot in enumerate(selected):
                if chosen[i] is not None:continue
                opts=candidates(slot)
                if not opts:return False
                options.append((len(opts),-len(slot[1]),i,opts))
            _,_,i,available=min(options,key=lambda x:x[:3])
            rng.shuffle(available)
            available.sort(key=lambda w:(-value(w)/(1+rng.random()*100)))
            for word in available[:70]:
                changed=[]
                for j,pos in enumerate(selected[i][1]):
                    if not grid[pos]:grid[pos]=word[j];changed.append(pos)
                chosen[i]=word;inside.add(word)
                if search(depth+1):return True
                chosen[i]=None;inside.remove(word)
                for pos in changed:grid[pos]=""
            return False
        return chosen if search(0) else None
    def extend_pool():
        import cmudict
        pronounced=set(cmudict.words())
        # Rescue only when the frequency-verified bank cannot complete the
        # collection. Keep the familiar vocabulary and all existing solutions.
        # Newly admitted words are a lower priority and are checked for
        # dictionary definitions before publishing.
        count=0
        for w,pos in en.lexicon.items():
            if not re.fullmatch(r"[a-z]{4,5}",w) or w in BANNED:
                continue
            if not pos.startswith(("NN","VB","JJ","RB")) or pos.startswith("NNP"):
                continue
            if w not in pronounced:continue
            upper=w.upper()
            if upper in frequencies:continue
            frequencies[upper]=.1
            n=len(upper);pools[n].append(upper)
            for j,ch in enumerate(upper):lookup[n][j][ch].add(upper)
            count+=1
        for n in (4,5):pools[n].sort(key=lambda w:(-value(w),w))
        print("Added",count,"lower-priority dictionary words for remaining compact grids",flush=True)

    started=time.monotonic()
    expanded=False
    for i in range(100):
        indices=list(range(len(shape_info)))
        rng=random.Random(12345+i*9973)
        rng.shuffle(indices)
        # Balance 1- and 2-short-answer patterns to prevent exhausting 3-letter
        # words, while still looking close to the original 5×5 widget.
        preferred=1 if i%3==0 else 2
        indices.sort(key=lambda idx:(sum(len(cs)==3 for _,cs in shape_info[idx][2])!=preferred,rng.random()))
        result=None
        for pass_number in range(2 if not expanded else 1):
            if pass_number==1:
                extend_pool()
                expanded=True
            for attempt,shape_index in enumerate(indices):
                shape,numbered,solve_slots=shape_info[shape_index]
                words=fill(solve_slots,42+i*123+attempt*117,
                           2500 if i<30 else (8500 if expanded else 7000))
                if words:
                    answer_by_cell={(direction,tuple(cells)):word
                        for (direction,cells),word in zip(solve_slots,words)}
                    ordered=[answer_by_cell[(direction,tuple(cells))] for direction,cells in numbered]
                    if len(set(ordered))!=10 or used.intersection(ordered):
                        raise AssertionError("Repeated answer")
                    used.update(ordered)
                    result={"shape":shape,"answers":ordered}
                    solutions.append(result)
                    break
            if result is not None:break
        if result is None:
            raise RuntimeError("Could not create 100 distinct compact grids: stopped at "
                               +str(i)+" completed. Existing published collection is unchanged.")
        if (i+1)%10==0:
            print("Completed",i+1,"compact grids",len(used),"distinct answers",
                  round(time.monotonic()-started,1),"seconds",flush=True)
    assert len(solutions)==100 and len(used)==1000
    for puzzle in solutions:
        if len(puzzle["shape"])!=5 or any(len(row)!=5 for row in puzzle["shape"]):
            raise AssertionError("Non-5×5 grid")
    return solutions

def plain(value):
    text=html.unescape(re.sub(r"<[^>]*>","",str(value or "")))
    return re.sub(r"\s+"," ",text).strip()

def dictionary_prefix(prefix):
    url=("https://raw.githubusercontent.com/mhollingshead/open-dictionary/"
         "main/api/"+prefix[0]+"/"+prefix+".json")
    req=urllib.request.Request(url,headers={"User-Agent":"LittleCrossword/1.0","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=18) as response:
            return prefix,json.loads(response.read(16000000))
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

CURATED_FALLBACKS=json.loads((ROOT/"data"/"classic-curated-fallbacks.json").read_text(encoding="utf-8"))

def clue_pair(word,senses,old_bank):
    if word in CURATED_FALLBACKS:
        return CURATED_FALLBACKS[word]
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
