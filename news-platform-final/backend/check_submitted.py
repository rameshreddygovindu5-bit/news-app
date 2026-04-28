import sqlite3
conn = sqlite3.connect(r'newsagg.db')
c = conn.cursor()
c.execute("""
    SELECT id, substr(original_title,1,60), flag, ai_status, rank_score, 
           submitted_by, original_language, 
           CASE WHEN telugu_title IS NOT NULL AND telugu_title != '' THEN 'Y' ELSE 'N' END as has_telugu
    FROM news_articles 
    WHERE submitted_by IS NOT NULL AND submitted_by != ''
    ORDER BY id DESC LIMIT 10
""")
for r in c.fetchall():
    print(r)

print("\n--- Latest 5 articles by id ---")
c.execute("""
    SELECT id, substr(original_title,1,60), flag, ai_status, rank_score, 
           submitted_by, original_language
    FROM news_articles 
    ORDER BY id DESC LIMIT 5
""")
for r in c.fetchall():
    print(r)

conn.close()
