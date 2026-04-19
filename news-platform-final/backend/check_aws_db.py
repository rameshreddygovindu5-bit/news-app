from app.database import engine_aws
from sqlalchemy import text

def check_aws_sources():
    try:
        with engine_aws.connect() as conn:
            # Check count
            count = conn.execute(text('SELECT count(*) FROM news_sources')).scalar()
            print(f"AWS Source Count: {count}")
            
            # List sources
            res = conn.execute(text('SELECT id, name FROM news_sources ORDER BY id')).fetchall()
            print("AWS News Sources:")
            for r in res:
                print(f"{r[0]}: {r[1]}")
    except Exception as e:
        print(f"Error connecting to AWS: {e}")

if __name__ == "__main__":
    check_aws_sources()
