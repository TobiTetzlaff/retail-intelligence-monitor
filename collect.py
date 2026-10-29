import json,re,html,os,time,calendar,datetime,collections,urllib.parse
from pathlib import Path
import requests,feedparser
from difflib import SequenceMatcher
NOW=datetime.datetime.now(datetime.timezone.utc)
START=NOW-datetime.timedelta(days=7)
ROOT=Path(__file__).parent
SOURCES={
'handel':['Lebensmittel Zeitung','Handelsblatt','stores+shops','etailment','Exciting Commerce','TextilWirtschaft','EHI Retail Institute','Supermarktblog','OnlinehändlerNews','Retail News','HDE'],
'konsum':['NIM Konsumklima','NielsenIQ','Destatis','Eurostat','Ipsos','YouGov','rheingold Institut','IFH Köln','McKinsey Consumer','Eurofound'],
'tech':['heise online','THE DECODER','MIT Technology Review','t3n','TechCrunch','Golem','Handelsblatt KI','VentureBeat','AI News','Nature Machine Intelligence']}
QUERIES={
'handel':['Einzelhandel Deutschland Strategie Unternehmen','Lebensmittelhandel E-Commerce Logistik Handel Deutschland','Retail Innovation Filialen Omnichannel Deutschland'],
'konsum':[   'Konsumverhalten Kaufentscheidungen Verbraucher Studie Deutschland',
    'Shopper Insights Kaufverhalten Handel Studie',
    'Markenbindung Markenwechsel Handelsmarken Konsumenten Studie',
    'Preiswahrnehmung Zahlungsbereitschaft Konsumpsychologie Studie',
    'Nachhaltigkeit Werte Einstellungen Konsum Forschung',
    'Customer Experience Einkaufsverhalten Verbraucherbefragung',
    'Konsumklima Verbrauchervertrauen Kaufkraft Deutschland',
    'Consumer Behavior Retail Research Europe',
    'Social Commerce KI Kaufberatung Technologieakzeptanz Studie',
    'Verhaltensökonomie Kaufentscheidung Konsum Experiment'],
'tech':['künstliche Intelligenz Unternehmen Agenten Automatisierung','AI technology innovation enterprise applications','KI Handel Robotik Digitalisierung Technologie']}
KEYWORDS={
'handel':['handel','retail','supermarkt','filial','e-commerce','onlinehandel','discounter','logistik','lieferkette','rewe','aldi','lidl','kaufland','edeka','otto','amazon','shop','lebensmittel'],
'konsum':['konsum','verbrauch','kaufverhalten','kaufkraft','konsumklima','inflation','haushalt','verbraucher','einkauf','preis','studie','umfrage','consumer','shopper','confidence','vertrauen'],
'tech':['ki','künstliche intelligenz','artificial intelligence','agent','robot','automatisierung','technologie','software','digital','modell','llm','chip','innovation','ai ','machine learning']}
EXCLUDE=['fußball','bundesliga','promi','horoskop','rezept','sportwetten']
SESSION=requests.Session();SESSION.headers.update({'User-Agent':'RetailIntelligenceMonitor/1.0 (public RSS aggregation)'})
def clean(s):
 s=html.unescape(re.sub('<[^>]+>',' ',str(s or '')))
 return re.sub(r'\s+',' ',s).strip()
def norm(s):
 s=re.sub(r'[^a-z0-9äöüß ]',' ',s.lower());return re.sub(r'\s+',' ',s).strip()
def fetch(query):
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query+' when:7d','hl':'de','gl':'DE','ceid':'DE:de'})
 try:
  r=SESSION.get(url,timeout=16);r.raise_for_status();return feedparser.parse(r.content).entries[:65]
 except Exception as e:
  print('Feed error:',query,str(e));return []
def pubdate(e):
 for field in ('published_parsed','updated_parsed'):
  if e.get(field):
   try:return datetime.datetime.fromtimestamp(calendar.timegm(e[field]),datetime.timezone.utc)
   except Exception:pass
 return None
def sentences(text,n=2):
 parts=re.split(r'(?<=[.!?])\s+',clean(text));return [p for p in parts if len(p)>25][:n]
def summarize(item):
 title=item['title'].rstrip('.!?')+'.'
 detail=clean(item.get('description',''))
 parts=sentences(detail,3)
 second=next((s for s in parts if SequenceMatcher(None,norm(s),norm(title)).ratio()<.72 and len(s)>35),'Die Meldung betrifft eine aktuelle Entwicklung im Themenfeld '+{'handel':'Handel und Handelsmanagement','konsum':'Konsumverhalten und Konsumklima','tech':'Technologie und KI'}[item['category']]+'.')
 return title+' '+second

def collect(cat):
 records=[];seen=set()
 for q in QUERIES[cat]:
  for e in fetch(q):
   date=pubdate(e)
   if not date or date<START or date>NOW+datetime.timedelta(hours=2):continue
   title=clean(e.get('title',''))
   if ' - ' in title: title,src=title.rsplit(' - ',1)
   else:src=clean(e.get('source',{}).get('title','')) or 'Nachrichtenquelle'
   if len(title)<24 or any(x in title.lower() for x in EXCLUDE):continue
   key=norm(title)
   if key in seen:continue
   seen.add(key)
   desc=clean(e.get('summary',''))
   hits=sum(1 for k in KEYWORDS[cat] if k in (title+' '+desc).lower())
   if hits<1:continue
   records.append({'title':title,'source':src,'url':e.get('link',''),'date':date.isoformat(),'description':desc,'category':cat,'hits':hits})
  time.sleep(.25)
 groups=[]
 for rec in sorted(records,key=lambda r:(-r['hits'],r['date']),reverse=False):
  tokens=set(norm(rec['title']).split())-{'der','die','das','und','für','mit','bei','von','auf','in','im','ein','eine','zu','des','den','nach','wie','the','and','for','with','from'}
  best=None;bestscore=0
  for g in groups:
   other=g['tokens'];overlap=len(tokens&other)/max(1,min(len(tokens),len(other)))
   similarity=SequenceMatcher(None,norm(rec['title']),norm(g['items'][0]['title'])).ratio()
   score=max(overlap,similarity)
   if score>bestscore:best,bestscore=g,score
  if best is not None and bestscore>=.68:best['items'].append(rec);best['tokens']|=tokens
  else:groups.append({'items':[rec],'tokens':tokens})
 output=[]
 for g in groups:
  items=g['items'];unique=len(set(x['source'].lower() for x in items))
  primary=max(items,key=lambda x:(x['hits'],x['date']))
  age=(NOW-datetime.datetime.fromisoformat(primary['date'])).total_seconds()/86400
  relevance=min(100,round(22+min(28,primary['hits']*7)+min(28,(unique-1)*12)+max(0,18-age*2.5)+min(4,len(items)-1)))
  output.append({'title':primary['title'],'summary':summarize(primary),'url':primary['url'],'source':primary['source'],'date':primary['date'][:10],'score':relevance,'sources':sorted(set(x['source'] for x in items)),'source_count':unique,'article_count':len(items)})
 output.sort(key=lambda x:(-x['score'],-x['source_count'],x['date']))
 return output[:10],len(records)
def lead(items):
 if not items:return 'Für diesen Zeitraum konnten keine ausreichend passenden Meldungen ermittelt werden. Bitte später erneut prüfen. Die Quellenabdeckung hängt von öffentlich verfügbaren RSS-Meldungen ab.'
 statements=[]
 for x in items[:3]:statements.append(x['title'].rstrip('.!?')+'.')
 while len(statements)<3:statements.append('Weitere belastbare Entwicklungen konnten im aktuellen Zeitraum nicht eindeutig identifiziert werden.')
 return ' '.join(statements)
PSYCH=[
 {'title':'Warum Menschen Verluste stärker gewichten als Gewinne','theories':['Prospect Theory (Kahneman & Tversky, 1979)','Endowment Effect (Thaler, 1980)'],'reference':[{'label':'Kahneman & Tversky (1979), Econometrica','url':'https://doi.org/10.2307/1914185'},{'label':'Thaler (1980), Journal of Economic Behavior & Organization','url':'https://doi.org/10.1016/0167-2681(80)90051-7'}], 'sentences':['Kaufentscheidungen beruhen nicht ausschließlich auf dem objektiven Nutzen eines Produkts.','Die Prospect Theory beschreibt, dass Menschen mögliche Ergebnisse relativ zu einem Referenzpunkt bewerten.','Verluste können dabei psychologisch stärker wirken als gleich große Gewinne.','Im Handel kann deshalb eine wegfallende Vergünstigung stärker auffallen als eine gleich hohe zusätzliche Vergünstigung.','Der Endowment Effect ergänzt diese Perspektive durch die häufig höhere Bewertung bereits besessener Güter.','Ein kostenloser Testzeitraum kann das Gefühl von Besitz erzeugen, bevor eine Kaufentscheidung fällt.','Auch die Gestaltung von Rückgabeoptionen kann die wahrgenommene Entscheidungssicherheit beeinflussen.','Die Stärke dieser Effekte hängt allerdings von Kontext, Erfahrung und konkretem Entscheidungsdesign ab.','Für die Handelsforschung bieten sich Experimente an, die identische Angebote mit unterschiedlichen Referenzpunkten vergleichen.','Entscheidend ist dabei, tatsächliches Wahlverhalten zu messen und nicht nur deklarierte Kaufabsichten.']},
 {'title':'Warum die Entscheidungen anderer unser Kaufverhalten beeinflussen','theories':['Social Proof (Cialdini, 1984)','Social Comparison Theory (Festinger, 1954)'],'reference':[{'label':'Festinger (1954), Human Relations','url':'https://doi.org/10.1177/001872675400700202'},{'label':'Cialdini, Influence (Buchinformation)','url':'https://www.harpercollins.com/products/influence-robert-b-cialdini'}], 'sentences':['Menschen orientieren sich bei unsicheren Entscheidungen häufig am Verhalten anderer.','Das Prinzip Social Proof beschreibt die Nutzung sozialer Hinweise als Entscheidungshilfe.','Die Social Comparison Theory erklärt ergänzend, warum Menschen eigene Einschätzungen mit denen anderer vergleichen.','Im Onlinehandel können Bewertungen und sichtbare Nachfrage als solche Hinweise dienen.','Dabei ist die Glaubwürdigkeit der Vergleichsgruppe entscheidend.','Eine hohe Anzahl positiver Rezensionen ersetzt jedoch nicht die Prüfung ihrer Qualität.','Soziale Hinweise können Unsicherheit reduzieren, aber auch Konformität fördern.','Der Effekt hängt unter anderem von Produktkategorie, Involvement und wahrgenommenem Risiko ab.','In Experimenten ließe sich die Wirkung von Bewertungsanzahl und sozialer Ähnlichkeit getrennt untersuchen.','Für Händler ergibt sich daraus die Aufgabe, soziale Information transparent und unverzerrt darzustellen.']}
]
def main():
 data={'updated_at':NOW.isoformat(),'window_start':START.isoformat(),'categories':{},'methodology':'RSS-basierte Recherche mit heuristischem Ranking; Mehrfachberichterstattung wird über Titelähnlichkeit angenähert. Scores und Zusammenfassungen sind keine KI-Validierung. Quellen und Links vor Weiterverwendung prüfen.'}
 for cat in SOURCES:
  items,count=collect(cat);data['categories'][cat]={'items':items,'lead':lead(items),'candidate_count':count,'preferred_sources':SOURCES[cat]};print(cat,count,len(items))
 data['psychology']=PSYCH[NOW.date().toordinal()%len(PSYCH)]
 (ROOT/'site'/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
