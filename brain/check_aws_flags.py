import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.getenv('AWS_DB_HOST'), port=os.getenv('AWS_DB_PORT'), dbname=os.getenv('AWS_DB_NAME'), user=os.getenv('AWS_DB_USER'), password=os.getenv('AWS_DB_PASSWORD'))
cur = conn.cursor()
cur.execute("SELECT flag, COUNT(1) FROM news_articles WHERE original_language = 'en' GROUP BY flag")
print(cur.fetchall())
conn.close()
