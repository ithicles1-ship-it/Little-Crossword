#!/usr/bin/env python3
"""No-cost multi-publisher headline crossword for a static GitHub Pages app.

No fabricated current events, no third-party AI API, no paid subscriptions.
The crossword is generated from pre-verified solution grids and editorial clues.
"""
import argparse
import concurrent.futures
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent.parent
FEEDS=[
 ("BBC News","https://feeds.bbci.co.uk/news/rss.xml"),
 ("BBC World","https://feeds.bbci.co.uk/news/world/rss.xml"),
 ("The Guardian","https://www.theguardian.com/uk/rss"),
 ("Sky News","https://feeds.skynews.com/feeds/rss/home.xml"),
 ("NPR","https://feeds.npr.org/1001/rss.xml"),
 ("Al Jazeera","https://www.aljazeera.com/xml/rss/all.xml"),
]
ALLOWED={"bbc.co.uk","bbc.com","theguardian.com","news.sky.com","npr.org","aljazeera.com"}
BLOCK=set("THE AND HIS WAS YES HAT MAN FAT CAT WAR MET NET PER SON RAT DAY NEW RED SAD GAS TILL ELSE NEED HERE NONE MALE FAR NOT HER HIM SHE SENT TEST REST MORE MOST DONE OVER".split())
TOPICS={
 "ELECT":r"\b(election|vote|voter|ballot|polls?|candidate|midterms?)\b",
 "RATES":r"\b(interest|inflation|mortgage|bank|rates?|tax)\b",
 "WAGES":r"\b(salaries|salary|wages|pay rise|workers?|employment)\b",
 "WAGE":r"\b(salaries|salary|wages|pay rise|workers?|employment)\b",
 "RENT":r"\b(tenants?|landlords?|rents?|housing|homes?)\b",
 "GAME":r"\b(games?|football|match|tournament|league|sport|competition)\b",
 "RIVAL":r"\b(rivals?|derby|opponents?|clash|final)\b",
 "ALERT":r"\b(alerts?|warning|warns?|threat|emergency|police)\b",
 "FATAL":r"\b(fatal|deaths?|killed|deadly|dies|died)\b",
 "WAVE":r"\b(waves?|surge|floods?|tsunami|sea)\b",
 "NAVAL":r"\b(navy|naval|warship|fleet|military ship)\b",
 "WEB":r"\b(website|web|internet|online|digital)\b",
 "EMAIL":r"\b(emails?|inbox|messages?|online)\b",
 "HORSE":r"\b(horse|racing|rider|equestrian)\b",
 "CAB":r"\b(taxi|ride.hailing|cabs?|private hire)\b",
 "SANTA":r"\b(christmas|santa|father christmas|festive)\b",
 "FIRED":r"\b(fired|sacked|dismissed|layoffs?|jobs? cuts|redundanc)\b",
 "FIRE":r"\b(fires?|wildfire|burning|blaze)\b",
 "YEAR":r"\b(year|annual|anniversary|2026|2027)\b",
 "GATES":r"\b(gates?|airport|border|terminal)\b",
 "SUN":r"\b(sun|solar|heatwave|sunlight|sunny)\b",
 "EVENT":r"\b(events?|festival|ceremony|conference|summit)\b",
 "RANGE":r"\b(range|far.reaching|broad|wide|variety)\b",
 "ANGRY":r"\b(angry|anger|outrage|furious|protesters?)\b",
 "HOPE":r"\b(hopes?|optimism|promises?|recovery)\b",
}

def data():
    src=(ROOT/"generator.js").read_text(encoding="utf-8")
    grids=json.loads(re.search(r"const PUZZLES=(\[.*?\]);\s*const CLUE_BANK=",src,re.S).group(1))
    clues=json.loads(re.search(r"const CLUE_BANK=(\{.*?\});\s*const PUZZLE_LIMIT=",src,re.S).group(1))
    return grids,clues

def approved(url):
    parts=urlsplit(url)
    host=(parts.hostname or "").lower()
    return parts.scheme=="https" and any(host==d or host.endswith("."+d) for d in ALLOWED)

def date_parse(raw):
    try:
        t=email.utils.parsedate_to_datetime(raw)
        if t is None: t=dt.datetime.fromisoformat(raw.replace("Z","+00:00"))
        if t.tzinfo is None: t=t.replace(tzinfo=dt.timezone.utc)
        return t.astimezone(dt.timezone.utc)
    except (TypeError,ValueError,OverflowError,AttributeError):
        try: return dt.datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(dt.timezone.utc)
        except (TypeError,ValueError,OverflowError,AttributeError): return None

def parse_feed(raw,publisher,now):
    root=ET.fromstring(raw);entries=root.findall(".//item")
    atom=False
    if not entries: entries=root.findall(".//{http://www.w3.org/2005/Atom}entry");atom=True
    records=[]
    for e in entries:
        if atom:
            ns="{http://www.w3.org/2005/Atom}"
            title=e.findtext(ns+"title","")
            link=e.find(ns+"link")
            url=link.get("href","") if link is not None else ""
            date_str=e.findtext(ns+"published","") or e.findtext(ns+"updated","")
        else:
            title=e.findtext("title","")
            url=e.findtext("link","")
            date_str=e.findtext("pubDate","") or e.findtext("{http://purl.org/dc/elements/1.1/}date","")
        published=date_parse(date_str)
        if published is None or not dt.timedelta(hours=-2)<=now-published<=dt.timedelta(hours=60):continue
        title=html.unescape(re.sub(r"<[^>]*>","",title)).strip()
        if not (15<=len(title)<=240) or not approved(url):continue
        records.append({"title":title,"url":url,"published":published.isoformat(),"source":publisher})
    return records[:70]

def fetch_one(feed,now):
    publisher,url=feed
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; LittleCrossword/2.0; personal PWA)","Accept":"application/rss+xml,application/xml,text/xml,*/*"})
    try:
        with urllib.request.urlopen(req,timeout=11) as r:raw=r.read(1500000)
        return parse_feed(raw,publisher,now)
    except Exception as e:
        print("Feed unavailable:",publisher,str(e),file=sys.stderr)
        return []

def fetch_all(now):
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        batches=executor.map(lambda feed:fetch_one(feed,now),FEEDS)
        unique={}
        for batch in batches:
            for x in batch:
                key=re.sub(r"\W+"," ",x["title"].lower()).strip()
                unique.setdefault(key,x)
    return list(unique.values())

def matches(answer,items):
    if len(answer)<4 or answer in BLOCK:return []
    exact=re.compile(r"(?<!\w)"+re.escape(answer)+r"(?!\w)",re.I)
    related=re.compile(TOPICS[answer],re.I) if answer in TOPICS else None
    out=[]
    for item in items:
        word=bool(exact.search(item["title"]))
        topic=bool(related.search(item["title"])) if related else False
        if word or topic:out.append((2 if word else 1,item,word))
    out.sort(key=lambda x:(-x[0],x[1]["source"],x[1]["url"]))
    return out[:25]


def reserved_for_today(date_str,grids):
    """The offline Classic and Themed answer lists for this UK date."""
    chosen=dt.date.fromisoformat(date_str)
    theme_start=dt.date(2026,11,6)
    day=(chosen-theme_start).days
    theme_src=(ROOT/"themes.js").read_text(encoding="utf-8")
    theme_packs=json.loads(re.search(r"const THEMED_PACKS=(\[.*?\]);",theme_src,re.S).group(1))
    theme=theme_packs[day%len(theme_packs)]["answers"]
    classic_start=dt.date(2026,11,8)
    if chosen>=classic_start:
        daily_src=(ROOT/"daily.js").read_text(encoding="utf-8")
        order=json.loads(re.search(r"const CLASSIC_ORDER=(\[.*?\]);",daily_src,re.S).group(1))
        index=order[(chosen-classic_start).days%len(order)]-1
    else:
        index=((day*7+11)%len(grids))
    return set(grids[index]["answers"])|set(theme)

def recent_news_answers(date_str):
    """Avoid returning last week's News answers when topical alternatives exist."""
    today=dt.date.fromisoformat(date_str)
    history_path=ROOT/"data"/"news-history.json"
    try: history=json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError,ValueError): history={}
    try:
        previous=json.loads((ROOT/"data"/"news.json").read_text(encoding="utf-8"))
        if previous.get("date")!=date_str:
            history[previous["date"]]=previous["puzzle"]["answers"]
    except (OSError,KeyError,ValueError,TypeError):pass
    recent=set()
    for date,answers in history.items():
        try:
            delta=(today-dt.date.fromisoformat(date)).days
            if 0<delta<=7: recent.update(answers)
        except (TypeError,ValueError):continue
    return recent

def build(items,now):
    if not items:return None
    date=now.astimezone(ZoneInfo("Europe/London")).date().isoformat()
    grids,bank=data();options=[]
    reserved=reserved_for_today(date,grids)
    recent=recent_news_answers(date)
    for i,grid in enumerate(grids):
        candidates=[(j,w,matches(w,items)) for j,w in enumerate(grid["answers"])]
        candidates=[x for x in candidates if x[2]]
        if not candidates:continue
        publishers={y[1]["source"] for _,_,xx in candidates for y in xx}
        tie=(i-dt.date.fromisoformat(date).toordinal())%len(grids)
        words=set(grid["answers"])
        # Never reuse another edition's answer on the same day if an alternative exists.
        # Prefer news words not used in the last week before maximising headline matches.
        options.append((-len(words&reserved),-len(words&recent),len(candidates),len(publishers),-tie,i,candidates))
    if not options:return None
    _,_,_,_,_,grid_id,candidates=max(options)
    grid=grids[grid_id]
    clues=[bank[w][0] for w in grid["answers"]]
    hints=[bank[w][1] for w in grid["answers"]]
    sources=[];used_urls=set();used_pubs=set()
    for j,w,potential in sorted(candidates,key=lambda x:(len(x[2]),x[0])):
        if len(sources)>=4:break
        options=sorted(potential,key=lambda x:(x[1]["source"] in used_pubs,x[1]["url"] in used_urls,-x[0]))
        rank,item,exact=options[0]
        if item["url"] in used_urls:continue
        if exact:
            masked=re.sub(r"(?<!\w)"+re.escape(w)+r"(?!\w)","_____",item["title"],flags=re.I)
            if len(masked)>105:
                at=masked.index("_____");a=max(0,at-35);b=min(len(masked),at+48)
                masked=("…" if a else "")+masked[a:b]+("…" if b<len(masked) else "")
            clue=item["source"]+" headline: “"+masked+"”"
        else:
            clue=item["source"]+" in the news: "+bank[w][0]
        if re.search(r"(?<!\w)"+re.escape(w)+r"(?!\w)",clue,re.I):continue
        clues[j]=clue;sources.append(item);used_urls.add(item["url"]);used_pubs.add(item["source"])
    if not sources:return None
    for w,clue,hint in zip(grid["answers"],clues,hints):
        if not clue or not hint or re.search(r"(?<!\w)"+re.escape(w)+r"(?!\w)",clue,re.I):
            raise ValueError("Invalid clue, hint or answer leakage")
    return {"date":date,"kind":"news","publisher":"multi-source-rss","puzzle":{
        "shape":grid["shape"],"answers":grid["answers"],"clues":clues,"hints":hints,
        "title":"In the News",
        "description":str(len(sources))+" topical clues from "+", ".join(sorted(used_pubs)),
        "sources":sources}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fixture",type=Path,action="append")
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--force",action="store_true")
    args=ap.parse_args()
    today=dt.datetime.now(ZoneInfo("Europe/London")).date().isoformat()
    path=ROOT/"data"/"news.json"
    if path.exists() and not args.force:
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("date")==today:
                print("Already published for",today,"— preserving today's answers")
                return 0
        except (ValueError,OSError): pass
    try:
        now=dt.datetime.now(dt.timezone.utc)
        if args.fixture:
            items=[]
            for i,fixture in enumerate(args.fixture):
                items+=parse_feed(fixture.read_bytes(),FEEDS[i%len(FEEDS)][0],now)
        else:items=fetch_all(now)
        print("Fresh headlines:",len(items),"publishers:",", ".join(sorted({x["source"] for x in items})))
        result=build(items,now)
        if not result:
            print("No fresh matching headlines. Keeping clearly labelled offline fallback.")
            return 0
        if args.dry_run:
            print(json.dumps(result,indent=2,ensure_ascii=False))
            return 0
        path.parent.mkdir(parents=True,exist_ok=True)
        history_path=ROOT/"data"/"news-history.json"
        try: history=json.loads(history_path.read_text(encoding="utf-8"))
        except (OSError,ValueError): history={}
        if path.exists():
            try:
                previous=json.loads(path.read_text(encoding="utf-8"))
                history[previous["date"]]=previous["puzzle"]["answers"]
            except (OSError,ValueError,TypeError,KeyError):pass
        history[today]=result["puzzle"]["answers"]
        history={k:v for k,v in history.items() if k>=str(dt.date.fromisoformat(today)-dt.timedelta(days=90))}
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        archive_path=ROOT/"data"/"news"/(today+".json")
        archive_path.parent.mkdir(parents=True,exist_ok=True)
        archive_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("Published",today,"with",len(result["puzzle"]["sources"]),"headline-linked clues")
        return 0
    except (OSError,ValueError,ET.ParseError,AttributeError) as e:
        print("Publisher unavailable:",str(e),file=sys.stderr)
        return 0

if __name__=="__main__":sys.exit(main())
