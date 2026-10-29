"""Retail Intelligence Monitor: RSS news and Gemini psychology feature.
Requires: pip install requests feedparser google-genai pydantic
"""
import calendar
import datetime as dt
import html
import json
import os
import re
import time
import urllib.parse
from difflib import SequenceMatcher
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parent
NOW = dt.datetime.now(dt.timezone.utc)
START = NOW - dt.timedelta(days=7)
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'RetailIntelligenceMonitor/2.0 (RSS research)'})

SOURCES = {
    'handel': ['Lebensmittel Zeitung', 'Handelsblatt', 'stores+shops', 'etailment', 'Exciting Commerce', 'TextilWirtschaft', 'EHI Retail Institute', 'Supermarktblog', 'OnlinehändlerNews', 'Retail News', 'HDE'],
    'konsum': ['NIM', 'NielsenIQ', 'Destatis', 'Eurostat', 'Ipsos', 'YouGov', 'rheingold Institut', 'IFH Köln', 'McKinsey', 'Eurofound', 'GfK', 'Kantar', 'Bitkom', 'EHI Retail Institute', 'Journal of Consumer Research'],
    'tech': ['heise online', 'THE DECODER', 'MIT Technology Review', 't3n', 'TechCrunch', 'Golem', 'Handelsblatt KI', 'VentureBeat', 'AI News', 'Nature Machine Intelligence'],
}
QUERIES = {
    'handel': ['Einzelhandel Deutschland Strategie Unternehmen', 'Lebensmittelhandel E-Commerce Logistik Handel Deutschland', 'Retail Innovation Filialen Omnichannel Deutschland'],
    'konsum': [
        'Konsumverhalten Kaufentscheidungen Verbraucher Studie Deutschland',
        'Shopper Insights Kaufverhalten Handel Studie',
        'Markenbindung Markenwechsel Handelsmarken Konsumenten Studie',
        'Preiswahrnehmung Zahlungsbereitschaft Konsumpsychologie Studie',
        'Nachhaltigkeit Werte Einstellungen Konsum Forschung',
        'Customer Experience Einkaufsverhalten Verbraucherbefragung',
        'Konsumklima Verbrauchervertrauen Kaufkraft Deutschland',
        'Consumer Behavior Retail Research Europe',
        'Social Commerce KI Kaufberatung Technologieakzeptanz Studie',
        'Verhaltensökonomie Kaufentscheidung Konsum Experiment',
    ],
    'tech': ['künstliche Intelligenz Unternehmen Agenten Automatisierung', 'AI technology innovation enterprise applications', 'KI Handel Robotik Digitalisierung Technologie'],
}
KEYWORDS = {
    'handel': ['handel', 'retail', 'supermarkt', 'filial', 'e-commerce', 'onlinehandel', 'discounter', 'logistik', 'lieferkette', 'rewe', 'aldi', 'lidl', 'kaufland', 'edeka', 'otto', 'amazon', 'shop', 'lebensmittel'],
    'konsum': ['konsum', 'verbrauch', 'kaufverhalten', 'kaufkraft', 'konsumklima', 'haushalt', 'verbraucher', 'einkauf', 'preis', 'studie', 'umfrage', 'consumer', 'shopper', 'vertrauen', 'marken', 'forschung', 'befragung', 'experiment', 'customer', 'entscheid', 'nachhaltig', 'zahlung', 'loyal', 'verhalten'],
    'tech': ['ki', 'künstliche intelligenz', 'artificial intelligence', 'agent', 'robot', 'automatisierung', 'technologie', 'software', 'digital', 'modell', 'llm', 'chip', 'innovation', 'ai ', 'machine learning'],
}
EXCLUDE = ['fußball', 'bundesliga', 'promi', 'horoskop', 'rezept', 'sportwetten']
EVIDENCE = ['studie', 'untersuchung', 'befragung', 'umfrage', 'forschung', 'experiment', 'erhebung', 'analyse', 'survey', 'research', 'report', 'panel', 'daten', 'ergebnis']

# Only preselected literature is cited. Gemini must not invent references.
TOPICS = [
    {'title': 'Verlustaversion und Referenzpunkte', 'theories': ['Prospect Theory'], 'reference': [{'label': 'Kahneman & Tversky (1979), Econometrica', 'url': 'https://doi.org/10.2307/1914185'}]},
    {'title': 'Besitztumseffekt und Wertzuschreibung', 'theories': ['Endowment Effect'], 'reference': [{'label': 'Thaler (1980), Journal of Economic Behavior & Organization', 'url': 'https://doi.org/10.1016/0167-2681(80)90051-7'}]},
    {'title': 'Sozialer Vergleich und Kaufentscheidungen', 'theories': ['Social Comparison Theory'], 'reference': [{'label': 'Festinger (1954), Human Relations', 'url': 'https://doi.org/10.1177/001872675400700202'}]},
    {'title': 'Psychologische Grundbedürfnisse und Autonomie', 'theories': ['Self-Determination Theory'], 'reference': [{'label': 'Deci & Ryan (2000), Psychological Inquiry', 'url': 'https://doi.org/10.1207/S15327965PLI1104_01'}]},
    {'title': 'Einstellungen, soziale Normen und Verhaltenskontrolle', 'theories': ['Theory of Planned Behavior'], 'reference': [{'label': 'Ajzen (1991), Organizational Behavior and Human Decision Processes', 'url': 'https://doi.org/10.1016/0749-5978(91)90020-T'}]},
    {'title': 'Verfügbarkeitsheuristik und Risikowahrnehmung', 'theories': ['Heuristics and Biases'], 'reference': [{'label': 'Tversky & Kahneman (1974), Science', 'url': 'https://doi.org/10.1126/science.185.4157.1124'}]},
    {'title': 'Normative Einflüsse und gesellschaftliches Verhalten', 'theories': ['Focus Theory of Normative Conduct'], 'reference': [{'label': 'Cialdini, Reno & Kallgren (1990), Journal of Personality and Social Psychology', 'url': 'https://doi.org/10.1037/0022-3514.58.6.1015'}]},
    {'title': 'Wahrgenommener Nutzen und Einfachheit digitaler Services', 'theories': ['Technology Acceptance Model'], 'reference': [{'label': 'Davis (1989), MIS Quarterly', 'url': 'https://doi.org/10.2307/249008'}]},
]


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(value or '')))).strip()


def norm(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9äöüß ]', ' ', value.lower())).strip()


def fetch(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': query + ' when:7d', 'hl': 'de', 'gl': 'DE', 'ceid': 'DE:de'})
    try:
        response = SESSION.get(url, timeout=16)
        response.raise_for_status()
        return feedparser.parse(response.content).entries[:65]
    except Exception as exc:
        print('RSS Fehler:', query, exc)
        return []


def pubdate(entry):
    for field in ('published_parsed', 'updated_parsed'):
        if entry.get(field):
            try:
                return dt.datetime.fromtimestamp(calendar.timegm(entry[field]), dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                pass
    return None


def summarize(item):
    title = item['title'].rstrip('.!?') + '.'
    parts = re.split(r'(?<=[.!?])\s+', clean(item.get('description', '')))
    second = next((p for p in parts if len(p) > 35 and SequenceMatcher(None, norm(p), norm(title)).ratio() < .72), None)
    if not second:
        second = 'Die Meldung betrifft eine aktuelle Entwicklung in ' + {'handel': 'Handel und Handelsmanagement', 'konsum': 'Konsumforschung und Verbraucherverhalten', 'tech': 'Technologie und KI'}[item['category']] + '.'
    return title + ' ' + second


def collect(category):
    records, seen = [], set()
    for query in QUERIES[category]:
        for entry in fetch(query):
            date = pubdate(entry)
            if not date or not START <= date <= NOW + dt.timedelta(hours=2):
                continue
            title = clean(entry.get('title', ''))
            if ' - ' in title:
                title, source = title.rsplit(' - ', 1)
            else:
                source = clean(entry.get('source', {}).get('title', '')) or 'Nachrichtenquelle'
            if len(title) < 24 or any(term in title.lower() for term in EXCLUDE):
                continue
            key = norm(title)
            if key in seen:
                continue
            seen.add(key)
            description = clean(entry.get('summary', ''))
            combined = (title + ' ' + description).lower()
            hits = sum(1 for term in KEYWORDS[category] if term in combined)
            if hits < 1:
                continue
            evidence = sum(1 for term in EVIDENCE if term in combined)
            records.append({'title': title, 'source': source, 'url': entry.get('link', ''), 'date': date.isoformat(), 'description': description, 'category': category, 'hits': hits, 'evidence': evidence})
        time.sleep(.15)
    groups = []
    for rec in sorted(records, key=lambda r: (-r['hits'], r['date'])):
        tokens = set(norm(rec['title']).split()) - {'der', 'die', 'das', 'und', 'für', 'mit', 'bei', 'von', 'auf', 'in', 'im', 'ein', 'eine', 'zu', 'des', 'den', 'nach', 'wie', 'the', 'and', 'for', 'with', 'from'}
        best, best_score = None, 0
        for group in groups:
            overlap = len(tokens & group['tokens']) / max(1, min(len(tokens), len(group['tokens'])))
            similarity = SequenceMatcher(None, norm(rec['title']), norm(group['items'][0]['title'])).ratio()
            score = max(overlap, similarity)
            if score > best_score:
                best, best_score = group, score
        if best is not None and best_score >= .68:
            best['items'].append(rec)
            best['tokens'] |= tokens
        else:
            groups.append({'items': [rec], 'tokens': tokens})
    output = []
    for group in groups:
        items = group['items']
        unique = len(set(item['source'].lower() for item in items))
        primary = max(items, key=lambda item: (item['hits'] + (min(item['evidence'], 3) * 2 if category == 'konsum' else 0), item['date']))
        age = (NOW - dt.datetime.fromisoformat(primary['date'])).total_seconds() / 86400
        bonus = min(14, primary['evidence'] * 5) if category == 'konsum' else 0
        relevance = min(100, round(20 + min(26, primary['hits'] * 6) + min(25, (unique - 1) * 11) + max(0, 17 - age * 2.5) + bonus + min(4, len(items) - 1)))
        output.append({'title': primary['title'], 'summary': summarize(primary), 'url': primary['url'], 'source': primary['source'], 'date': primary['date'][:10], 'score': relevance, 'sources': sorted(set(item['source'] for item in items)), 'source_count': unique, 'article_count': len(items)})
    output.sort(key=lambda item: (-item['score'], -item['source_count'], item['date']))
    return output[:10], len(records)


def lead(items):
    if not items:
        return 'Für diesen Zeitraum wurden keine ausreichend passenden Meldungen gefunden.'
    return ' '.join(item['title'].rstrip('.!?') + '.' for item in items[:3])


def psychology():
    '''Create one article; never block the news website if Gemini is unavailable.'''
    run_number = int(os.getenv('GITHUB_RUN_NUMBER', '1'))
    topic = TOPICS[(run_number - 1) % len(TOPICS)]
    previous_file = ROOT / 'site' / 'data.json'

    def fallback():
        # Prefer the last published article if it exists in the checkout.
        if previous_file.exists():
            try:
                previous = json.loads(previous_file.read_text(encoding='utf-8')).get('psychology')
                if isinstance(previous, dict) and previous.get('sentences') and previous.get('reference'):
                    print('Gemini nicht erreichbar: bisherigen Psychologieartikel beibehalten.')
                    return previous
            except (OSError, ValueError, TypeError):
                pass
        # A verified, prewritten fallback if no previous article is available.
        print('Gemini nicht erreichbar: wissenschaftlichen Reserveartikel verwenden.')
        return {
            'title': 'Warum Verluste unsere Kaufentscheidungen beeinflussen',
            'theories': ['Prospect Theory'],
            'reference': [{'label': 'Kahneman & Tversky (1979), Econometrica', 'url': 'https://doi.org/10.2307/1914185'}],
            'sentences': [
                'Menschen beurteilen wirtschaftliche Entscheidungen häufig relativ zu einem Referenzpunkt.',
                'Die Prospect Theory beschreibt, wie Gewinne und Verluste im Verhältnis zu diesem Bezugspunkt wahrgenommen werden.',
                'Verluste können psychologisch stärker wirken als gleich hohe Gewinne.',
                'Dieser Effekt wird als Verlustaversion bezeichnet.',
                'Ein Referenzpunkt kann sich aus Erwartungen, bisherigen Preisen oder dem aktuellen Besitz ergeben.',
                'Deshalb kann dieselbe Preisänderung je nach Ausgangslage unterschiedlich bewertet werden.',
                'Die Theorie hilft dabei, scheinbar widersprüchliche Entscheidungen unter Unsicherheit zu verstehen.',
                'Sie bedeutet jedoch nicht, dass alle Menschen in jeder Situation gleich reagieren.',
                'Erfahrung, Kontext und die konkrete Darstellung einer Entscheidung können die Wirkung verändern.',
                'Im Handel lassen sich solche Mechanismen mit kontrollierten Preisexperimenten untersuchen.'
            ],
            'example': [
                'Ein Kunde sieht einen Artikel zunächst für achtzig Euro.',
                'Während einer Aktion kostet derselbe Artikel sechzig Euro.',
                'Wenn der Preis wieder steigt, kann der Kunde dies als Verlust einer Vergünstigung erleben.'
            ],
            'generated': False
        }

    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        print('WARNUNG: GEMINI_API_KEY fehlt; verwende Reserveartikel.')
        return fallback()

    try:
        from google import genai
        from google.genai import types
        from pydantic import BaseModel, Field

        class Article(BaseModel):
            title: str
            sentences: list[str] = Field(min_length=10, max_length=10)
            example: list[str] = Field(min_length=3, max_length=3)

        prompt = f'''Verfasse auf Deutsch einen neuen wissenschaftlich informierten Kurzbeitrag zum Thema: {topic['title']}.
Theoretischer Rahmen: {', '.join(topic['theories'])}.
Zulässige Literaturgrundlage (keine zusätzlichen Quellen erfinden): {json.dumps(topic['reference'], ensure_ascii=False)}.
Gib genau 10 vollständige Sätze im JSON-Array sentences und genau 3 vollständige Sätze
als realistisches Beispiel aus dem Handel oder Konsumalltag im JSON-Array example aus.
Ergänze eine prägnante Überschrift im Feld title. Keine erfundenen Befunde, Zitate oder Zahlen.
Ein Satz pro Array-Element, ohne Markdown. Die Sätze werden als Fließtext angezeigt.
Schreibe eigenständig, erläutere Theorie, Wirkmechanismus, Anwendungsgrenzen und mögliche Effekte.
Neue Perspektive für Workflow-Lauf {run_number}.
'''
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000))
        try:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite'),
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type='application/json',
                            response_schema=Article,
                            temperature=0.6,
                        ),
                    )
                    article = Article.model_validate_json(response.text)
                    if not all(len(re.findall(r'[.!?]', sentence)) == 1 and sentence.strip().endswith(('.', '!', '?')) for sentence in article.sentences + article.example):
                        raise ValueError('Antwort enthaelt nicht genau einen Satz pro Element')
                    print('Psychologieartikel erfolgreich mit Gemini generiert.')
                    return {
                        'title': article.title,
                        'theories': topic['theories'],
                        'reference': topic['reference'],
                        'sentences': article.sentences,
                        'example': article.example,
                        'generated': True,
                    }
                except Exception as exc:
                    print(f'Gemini-Versuch {attempt + 1}/3 fehlgeschlagen: {type(exc).__name__}: {str(exc)[:180]}')
                    if attempt < 2:
                        time.sleep(3 * (attempt + 1))
        finally:
            client.close()
    except Exception as exc:
        print(f'Gemini momentan nicht nutzbar: {type(exc).__name__}: {str(exc)[:180]}')
    return fallback()

def main():
    data = {'updated_at': NOW.isoformat(), 'window_start': START.isoformat(), 'categories': {}, 'methodology': 'RSS-Recherche mit heuristischem Ranking und 7-Tage-Fenster. Konsumstudien werden über Signalwörter priorisiert, nicht auf Evidenzqualität geprüft. Psychologieartikel werden mit Gemini aus kuratierter Literatur generiert; fachliche Überprüfung vor wissenschaftlicher Weiterverwendung empfohlen.'}
    for category in SOURCES:
        items, count = collect(category)
        data['categories'][category] = {'items': items, 'lead': lead(items), 'candidate_count': count, 'preferred_sources': SOURCES[category]}
        print(category, 'Kandidaten:', count, 'Top:', len(items))
    data['psychology'] = psychology()
    output = ROOT / 'site' / 'data.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Fertig:', output)


if __name__ == '__main__':
    main()
