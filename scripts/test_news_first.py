#!/usr/bin/env python3
"""Fixture tests; never depend on the day's headlines for CI success."""
import datetime as dt
import re
from news_first import construct, slots, source_words, dictionary

NOW=dt.datetime.now(dt.timezone.utc).isoformat()
words=["ZELDA","STORM","NASA","TRADE","MARS","QUEEN","COURT","TRIAL","RUGBY","VOTES","APPLE","MUSIC","GAMES","TRAIN","FIRES","MOON","SPACE","EARTH","PLANE","RATES"]
items=[]
for i,w in enumerate(words):
    items.append({"title":f"Council discusses {w.title()} after fresh national report",
        "source":("BBC News" if i%2 else "The Guardian"),"url":f"https://example.org/story-{i}",
        "published":NOW})
classic,fill=dictionary()
from news_first import solve
sample=classic[0]
print('Sample known fill:',sample['answers'],flush=True)
print('Sample shape:',sample['shape'],flush=True)
print('Direct seeded solver:',solve(sample['shape'],[(sample['answers'][0],items[0],1),(sample['answers'][1],items[1],1)],fill,set(),123,max_calls=4000),flush=True)
anchors=source_words(items,set(fill))
print('Headline choices:',[(x[0],x[2]) for x in anchors[:22]],flush=True)
assert any(x[0]=="ZELDA" for x in anchors)
assert any(x[0]=="STORM" for x in anchors)
result=construct(items)
assert result is not None, "Could not construct news-first crossword with synthetic headlines"
shape=result["shape"]
assert len(shape)==5 and all(len(row)==5 for row in shape)
ss=slots(shape)
assert len(ss)==10
assert len(set(result["answers"]))==10
assert 1<=len(result["sources"])<=2
assert len({x["source"] for x in result["sources"]})==len(result["sources"])
assert result["method"]=="headline-first"
cells={}
for answer,(direction,positions) in zip(result["answers"],ss):
    assert len(answer)==len(positions)
    for pos,letter in zip(positions,answer):
        if pos in cells:assert cells[pos]==letter
        else:cells[pos]=letter
for word,clue in zip(result["answers"],result["clues"]):
    assert not re.search(r'(?<![A-Za-z])'+re.escape(word)+r'(?![A-Za-z])',clue,re.I)
assert len(result["clues"])==10 and len(result["hints"])==10
print("PASS news-first compact grid",result["answers"],[x["source"] for x in result["sources"]])
