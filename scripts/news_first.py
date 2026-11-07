#!/usr/bin/env python3
"""News-first mini constructor: source-backed answers before grid fill.

Use *actual words in verified RSS headlines* as anchors, then build a validated
5-Across/5-Down 5x5 around them. Never invent a news claim. Offline and
subscription-free: candidate fill and clues come from the reviewed puzzle bank.
The legacy article-matching route is only an explicitly labelled fallback.
"""
import collections
import json
import random
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
NEWS_STOP=set("""
THE A AN AND OR BUT IF THEN THIS THAT THESE THOSE IN ON AT TO OF FOR BY WITH
FROM AS IS ARE WAS WERE BE BEEN BEING HAS HAVE HAD WILL WOULD SHOULD COULD
CAN MAY MIGHT MUST MORE MOST MUCH MANY SOME ANY ALL NO NOT SO DO DOES DID
HOW WHAT WHERE WHEN WHO WHY WHICH WHOSE SUCH THEIR THERE HERE AFTER BEFORE
AMID AMONG ABOUT INTO OUT OVER UNDER UP DOWN LIKE SAID SAYS SAY NEWS
LATEST LIVE TODAY TOMORROW YESTERDAY WEEK YEAR YEARS DAYS DAY MONTH NOW
SHOW SHOWS MADE MAKE MAKES SOMEONE PEOPLE PERSON HUMAN WORLD STATE STATES
FIRST LAST NEXT NEW OLD ALSO THEM THEY YOU YOUR HE SHE HIS HER ITS OUR
MORE ONCE REPORT REPORTS REVEALS REVEAL FEARS FEAR MORE WHAT'S
""".split())
# Unambiguous current-event concepts and established named things are useful
# anchors. They are only selected when *present in the actual title*.
PREFERRED=set("""
ZELDA SONIA MAYAS NASA NATO TRUMP BIDEN KAGAN TESLA APPLE SPACE SPORT
VOTES VOTE POLLS STORM FLOOD FIRE FIRES COURT TRIAL TRADE PEACE
UNION QUEEN KING ROYAL EARTH MOON MARS SOLAR TRAIN CRASH PLANE
RATES TAXES STOCK OIL GAS MUSIC OSCAR RUGBY GAME GAMES
AI NHS WALES CHINA INDIA JAPAN PARIS ROME LONDON GAZA
""".split())
MIN_ANCHORS=2

def slots(shape):
    R=len(shape);C=len(shape[0]);out=[]
    for r in range(R):
        for c in range(C):
            if shape[r][c]=='#':continue
            if c==0 or shape[r][c-1]=='#':
                cells=[]
                for x in range(c,C):
                    if shape[r][x]=='#':break
                    cells.append(r*C+x)
                if len(cells)>=3:out.append(('Across',cells))
            if r==0 or shape[r-1][c]=='#':
                cells=[]
                for y in range(r,R):
                    if shape[y][c]=='#':break
                    cells.append(y*C+c)
                if len(cells)>=3:out.append(('Down',cells))
    if len(out)!=10 or sum(x[0]=='Across' for x in out)!=5:
        raise ValueError('Not a five Across/five Down shape')
    return out

def source_words(items, fill_words):
    """Pick individual verifiable headline words, not broad thematic guesses."""
    found={}
    for article in items:
        title=article['title']
        for m in re.finditer(r'(?<![A-Za-z])([A-Za-z]{3,5})(?![A-Za-z])',title):
            word=m.group(1).upper()
            if word in NEWS_STOP or word in {"FAT","CAT","SAD","BAD","GOOD","GREAT","NEVER","OTHER","SUPER"}:continue
            if not re.fullmatch('[A-Z]{3,5}',word):continue
            proper=m.start()>0 and m.group(1)[0].isupper()
            focus=word in PREFERRED or proper
            # A concrete noun/name carries much more news meaning than 'says'.
            if not focus and word not in fill_words:continue
            points=(18 if word in PREFERRED else 0)+(12 if proper else 0)+(4 if len(word)==5 else 2)
            # A regular fill word is still allowed if it genuinely appears in a headline.
            if word in fill_words:points+=3
            found.setdefault(word,[])
            found[word].append((points,article))
    scored=[]
    for word,variants in found.items():
        best=max(variants,key=lambda x:x[0])
        scored.append((word,best[1],best[0]))
    scored.sort(key=lambda x:(-x[2],-len(x[0]),x[0]))
    return scored[:65]

def dictionary():
    classic=json.loads((ROOT/'data'/'classics100.json').read_text(encoding='utf-8'))
    manual=json.loads((ROOT/'data'/'classic-curated-fallbacks.json').read_text(encoding='utf-8'))
    fill={}
    for index,p in enumerate(classic):
        for w,c,h in zip(p['answers'],p['clues'],p['hints']):
            if not 3<=len(w)<=5 or not re.fullmatch('[A-Z]+',w):continue
            if w not in fill:
                edited=(index<18) or w in manual
                fill[w]=(c,h,4 if edited else 1)
    return classic,fill

def solve(shape, anchors, fill, exclusions, seed, max_calls=2600):
    ss=slots(shape);C=len(shape[0]);cells=['']*(len(shape)*C)
    chosen=[None]*10;used=set()
    by_len=collections.defaultdict(list)
    inverted=collections.defaultdict(lambda:collections.defaultdict(set))
    for w in fill:
        if w in exclusions:continue
        n=len(w);by_len[n].append(w)
        for j,ch in enumerate(w):inverted[n,j][ch].add(w)
    for a in anchors:
        if a[0] not in fill: # explicitly allow *real* news nouns / names as new entries
            w=a[0]
            n=len(w);by_len[n].append(w)
            for j,ch in enumerate(w):inverted[n,j][ch].add(w)
    rng=random.Random(seed)
    def word_opts(idx):
        pos=ss[idx][1];n=len(pos)
        fragments=[inverted[n,j].get(c,set()) for j,p in enumerate(pos) if (c:=cells[p])]
        if fragments:
            if not all(fragments):return []
            pool=set.intersection(*sorted(fragments,key=len))
            possibilities=[w for w in pool if w not in used]
        else:
            possibilities=[w for w in by_len[n] if w not in used]
        possibilities.sort(key=lambda w:(-fill.get(w,('','',0))[2],w))
        return possibilities
    def assign(idx,w):
        modified=[]
        for j,p in enumerate(ss[idx][1]):
            if cells[p] and cells[p]!=w[j]:
                for x in modified:cells[x]=''
                return None
            if not cells[p]:cells[p]=w[j];modified.append(p)
        chosen[idx]=w;used.add(w)
        return modified
    def undo(idx,w,changed):
        chosen[idx]=None;used.discard(w)
        for p in changed:cells[p]=''
    # Headline words MUST fit before the fill is constructed.
    def place_anchors(i):
        if i==len(anchors):return fill_rest(0)
        w=anchors[i][0]
        candidates=[j for j,slot in enumerate(ss) if chosen[j] is None and len(slot[1])==len(w)]
        rng.shuffle(candidates)
        for idx in candidates:
            changed=assign(idx,w)
            if changed is None:continue
            if place_anchors(i+1):return True
            undo(idx,w,changed)
        return False
    calls=0
    def fill_rest(depth):
        nonlocal calls
        if all(chosen):return True
        calls+=1
        if calls>max_calls:return False
        possibilities=[]
        for idx,w in enumerate(chosen):
            if w is not None:continue
            opts=word_opts(idx)
            if not opts:return False
            possibilities.append((len(opts),idx,opts))
        _,idx,opts=min(possibilities,key=lambda x:(x[0],x[1]))
        # Put the editorially-reviewed clue bank before obscure dictionary fill.
        good=[w for w in opts if fill.get(w,('','',0))[2]>=4]
        extra=[w for w in opts if w not in good]
        rng.shuffle(good);rng.shuffle(extra)
        for w in (good[:32]+extra[:22]):
            changed=assign(idx,w)
            if changed is None:continue
            if fill_rest(depth+1):return True
            undo(idx,w,changed)
        return False
    if not place_anchors(0):return None
    if len(set(chosen))!=10:return None
    return {'shape':shape,'answers':chosen,'slots':ss}

def title_clue(word,article):
    """A concrete, sourced clue; masked title never contains its own answer."""
    raw=article['title']
    masked=re.sub(r'(?<![A-Za-z])'+re.escape(word)+r'(?![A-Za-z])','____',raw,flags=re.I)
    if raw==masked:return None
    if len(masked)>105:
        at=masked.find('____');start=max(0,at-40);end=min(len(masked),at+48)
        masked=('…' if start else '')+masked[start:end]+('…' if end<len(masked) else '')
    return article['source']+' headline: '+masked

def construct(items, exclusions=None, max_tries=180):
    """News-anchor-first crossword or None when quality cannot be guaranteed."""
    exclusions=set(exclusions or [])
    classic,fill=dictionary()
    matches=source_words(items,set(fill))
    if len(matches)<2:return None
    # The grid is a *template only*; none of its previous filler answers are
    # reused intentionally unless they satisfy the crossing constraints.
    shapes=[]
    for p in classic:
        s=p['shape'];key='|'.join(s)
        if key not in {k for k,_ in shapes}:shapes.append((key,s))
    shapes.sort(key=lambda kv:(sum(row.count('#') for row in kv[1]),kv[0]))
    rng=random.Random(92721+len(items))
    attempts=0
    # Require at least two independent publishers, when available.
    top=matches[:38]
    pairs=[]
    for i,a in enumerate(top):
        for b in top[i+1:]:
            if a[1]['url']==b[1]['url']:continue
            if a[1]['source']==b[1]['source']:continue
            if len(a[0])==3 and len(b[0])==3:continue
            pairs.append((a,b))
    pairs.sort(key=lambda ab:(-(ab[0][2]+ab[1][2]),ab[0][0],ab[1][0]))
    if not pairs:
        return None
    best=None
    for a,b in pairs[:14]:
        # Rotated shape list adds variety without insisting on 24/25 tiles.
        candidate_shapes=shapes[:]
        rng.shuffle(candidate_shapes)
        for _,shape in candidate_shapes[:20]:
            attempts+=1
            if attempts>max_tries:break
            if max(len(a[0]),len(b[0]))>max(map(lambda s:s.count('.'),shape)):continue
            answer=solve(shape,[a,b],fill,exclusions,seed=attempts+len(a[0])*900,max_calls=950)
            if answer:
                best=(answer,[a,b])
                break
        if best or attempts>max_tries:break
    if not best:return None
    grid,anchors=best
    indexed={word:article for word,article,_ in anchors}
    clues=[];hints=[];sources=[]
    for w in grid['answers']:
        if w in indexed:
            article=indexed[w]
            c=title_clue(w,article)
            if not c:return None
            hint=fill[w][1] if w in fill else "A real name or term from the linked news article."
            sources.append(article)
        else:
            if w not in fill:return None
            c,hint,_=fill[w]
        if re.search(r'(?<![A-Za-z])'+re.escape(w)+r'(?![A-Za-z])',c,re.I):return None
        clues.append(c);hints.append(hint)
    if len(sources)!=2:return None
    return {
        'shape':grid['shape'],
        'answers':grid['answers'],
        'clues':clues,
        'hints':hints,
        'sources':sources,
        'title':'In the News',
        'description':'Two verified headline answers built into today’s crossword',
        'method':'headline-first'
    }
