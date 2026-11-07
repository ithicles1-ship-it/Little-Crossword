#!/usr/bin/env python3
"""No API key. Make an optional news-linked mini from public BBC RSS headlines.

Uses pre-validated puzzle solutions and human-curated clue/hint pairs. It NEVER
claims to create fresh AI-authored answers or guesses facts from news articles.
"""
from __future__ import annotations
import argparse
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent.parent
RSS_URL='https://feeds.bbci.co.uk/news/rss.xml'
BLOCK={'THE','AND','HIS','WAS','YES','HAT','MAN','FAT','CAT','WAR','MET','NET','PER','SON','RAT','DAY','NEW','RED','SAD','GAS','TILL','ELSE','NEED','HERE','NONE','MALE','FAR','NOT','HER','HIM','SHE'}

def get_data():
    text=(ROOT/'generator.js').read_text(encoding='utf8')
    grids=json.loads(re.search(r'const PUZZLES=(\[.*?\]);\s*const CLUE_BANK=',text,re.S).group(1))
    bank=json.loads(re.search(r'const CLUE_BANK=(\{.*?\});\s*const PUZZLE_LIMIT=',text,re.S).group(1))
    return grids,bank

def fetch_items(xml_bytes=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if xml_bytes is None:
        req=urllib.request.Request(RSS_URL,headers={'User-Agent':'LittleCrosswordPersonal/1.0 (+personal GitHub Pages mini crossword)'})
        with urllib.request.urlopen(req,timeout=22) as resp:
            xml_bytes=resp.read(2_000_000)
    root=ET.fromstring(xml_bytes)
    fresh=[]
    for item in root.findall('./channel/item'):
        title=html.unescape(''.join(item.findtext('title','')).strip())
        url=(item.findtext('link','') or '').strip()
        published=item.findtext('pubDate','')
        try: date=email.utils.parsedate_to_datetime(published).astimezone(dt.timezone.utc)
        except (TypeError, ValueError, OverflowError, AttributeError): continue
        if not (dt.timedelta(hours=-3)<=now-date<=dt.timedelta(hours=48)):continue
        if not (url.startswith('https://www.bbc.co.uk/') or url.startswith('https://www.bbc.com/')):continue
        if not title or len(title)>280:continue
        fresh.append({'title':title,'url':url,'published':date.isoformat()})
    return fresh[:60]

def build(items,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    day=now.astimezone(ZoneInfo('Europe/London')).date().isoformat()
    grids,bank=get_data()
    ranked=[]
    for i,g in enumerate(grids):
        hits=[]
        for j,w in enumerate(g['answers']):
            if w in BLOCK or len(w)<4:continue
            matches=[x for x in items if re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',x['title'],re.I)]
            if matches: hits.append((j,w,matches[0]))
        distinct=len(set(hit[2]['url'] for hit in hits))
        # Rotate tie-breaks to avoid always preferring early grids.
        rotate=(i-(int(now.timestamp()/86400)*7)%len(grids))%len(grids)
        ranked.append((len(hits),distinct,-rotate,i,hits))
    ranked.sort(reverse=True)
    hit_count,distinct,_,idx,hits=ranked[0]
    if hit_count<1:return None
    g=grids[idx]
    clues=[bank[w][0] for w in g['answers']]
    hints=[bank[w][1] for w in g['answers']]
    sources=[]
    # Headline gets transformed into a short fill-in-the-blank clue.
    for j,w,item in hits[:3]:
        title=item['title']
        masked=re.sub(r'(?<!\w)'+re.escape(w)+r'(?!\w)','_____',title,flags=re.I)
        if masked==title:continue
        if len(masked)>95:
            at=masked.index('_____');start=max(0,at-33);end=min(len(masked),at+58)
            masked=('…' if start else '')+masked[start:end]+('…' if end<len(masked) else '')
        clues[j]=f'From a BBC headline: “{masked}”'
        sources.append({'title':title,'url':item['url'],'published':item['published']})
    if not sources:return None
    puzzle={'shape':g['shape'],'answers':g['answers'],'clues':clues,'hints':hints,
            'title':'In the News',
            'description':f"BBC headlines · {len(sources)} linked clue{'s' if len(sources)!=1 else ''} · {day}",
            'sources':sources}
    # Content and crossing check: the source grids are already checked but validate again.
    assert len(g['answers'])==10 and len(clues)==len(hints)==10
    for w,c,h in zip(g['answers'],clues,hints):
        assert c and h and not re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',c,re.I),f'Clue leaks {w}'
    return {'date':day,'kind':'news','publisher':'free-rss-rule-based','puzzle':puzzle}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixture',type=Path,help='Local RSS fixture for testing')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    try:
        items=fetch_items(args.fixture.read_bytes() if args.fixture else None)
        result=build(items)
        if not result:
            print('No sufficiently recent relevant headlines; offline Newsroom mini stays available.')
            return 0
        if args.dry_run:
            print(json.dumps({'date':result['date'],'linked_clues':len(result['puzzle']['sources']),
                              'answers':result['puzzle']['answers']},indent=2));return 0
        path=ROOT/'data'/'news.json'
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print('Wrote',path,'for',result['date'],'with',len(result['puzzle']['sources']),'real headlines')
        return 0
    except (OSError,ValueError,ET.ParseError,AssertionError) as exc:
        print('News update unavailable:',str(exc),file=sys.stderr)
        return 0  # don't take the crossword website offline because a news feed failed

if __name__=='__main__':sys.exit(main())
