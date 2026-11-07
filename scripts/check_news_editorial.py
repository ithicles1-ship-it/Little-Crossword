#!/usr/bin/env python3
"""Editorial safeguards for the headline-first crossword publisher."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import news_first

ROOT=Path(__file__).resolve().parent.parent
manual=json.loads((ROOT/'data'/'classic-curated-fallbacks.json').read_text())
_,fill=news_first.dictionary()
assert fill, 'No approved fill vocabulary'
assert all(w in manual and [c,h]==manual[w] for w,(c,h,score) in fill.items()), (
    'News must not use unedited dictionary first senses')
assert all(score>=4 for _,_,score in fill.values())
two=[
 {'title':'NASA announces new Moon research programme',
  'source':'BBC News','url':'https://www.bbc.co.uk/news/example-a'},
 {'title':'Zelda game franchise announces a new entry',
  'source':'The Guardian','url':'https://www.theguardian.com/example-b'}
]
words=news_first.source_words(two,set(fill))
for answer in ('NASA','ZELDA'):
    candidate=next((a for a in words if a[0]==answer),None)
    assert candidate,answer+' must be extracted from an actual supplied headline'
    clue=news_first.title_clue(answer,candidate[1])
    assert clue and '____' in clue
    assert not re.search(r'(?<![A-Za-z])'+answer+r'(?![A-Za-z])',clue,re.I)
    assert candidate[1]['url'] in {x['url'] for x in two}
published=ROOT/'data'/'news.json'
if published.exists():
    payload=json.loads(published.read_text())
    p=payload.get('puzzle',{})
    assert p.get('method') in ('headline-first','matched-existing-fallback',None)
    for article in p.get('sources',[]):
        assert article.get('url','').startswith('https://')
        assert article.get('title') and article.get('source')
    for answer,clue in zip(p.get('answers',[]),p.get('clues',[])):
        assert not re.search(r'(?<![A-Za-z])'+re.escape(answer)+r'(?![A-Za-z])',clue,re.I),answer
print('News editorial QA passed:',len(fill),'approved filler words, actual source anchors and verified clue masks')
