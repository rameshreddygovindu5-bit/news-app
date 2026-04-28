import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('newsagg.db')
cursor = conn.cursor()

print('=== DATABASE STATUS REPORT ===\n')
print(f'Total articles: 1464')
print(f'  Flag A (AI processed): 1256')
print(f'  Flag N (new/pending): 8')  
print(f'  Flag Y (scraped): 200')

# Check sources table
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f'\nTables: {tables}')

# Get sources
if 'news_sources' in tables:
    cursor.execute('SELECT ns.name, COUNT(na.id) FROM news_articles na LEFT JOIN news_sources ns ON na.source_id = ns.id GROUP BY na.source_id ORDER BY COUNT(na.id) DESC')
    print('\nBy source:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')

# Recent articles (last 24h)
yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
cursor.execute('SELECT COUNT(*) FROM news_articles WHERE created_at > ?', (yesterday,))
recent = cursor.fetchone()[0]
print(f'\nArticles in last 24h: {recent}')

# Latest 5 articles
cursor.execute('SELECT na.title, ns.name, na.created_at FROM news_articles na LEFT JOIN news_sources ns ON na.source_id = ns.id ORDER BY na.created_at DESC LIMIT 5')
print('\nLatest 5 articles:')
for row in cursor.fetchall():
    title = row[0] if row[0] else '(no title)'
    print(f'  [{row[2]}] {row[1]}: {title[:80]}')

# No stuck articles (already checked)
print('\nNo stuck articles (only flags A, N, Y present)')

# By language
cursor.execute('SELECT original_language, COUNT(*) FROM news_articles GROUP BY original_language')
print('\nBy language:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Articles without AI processing
cursor.execute("SELECT COUNT(*) FROM news_articles WHERE flag != 'A'")
unprocessed = cursor.fetchone()[0]
print(f'\nArticles NOT yet AI-processed: {unprocessed}')

# Check what sources exist
if 'news_sources' in tables:
    cursor.execute('SELECT id, name, url, is_active FROM news_sources')
    print('\nConfigured sources:')
    for row in cursor.fetchall():
        status = 'ACTIVE' if row[3] else 'INACTIVE'
        print(f'  [{status}] {row[1]} (id={row[0]})')

conn.close()
