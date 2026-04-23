# AWS Sync Functionality - Setup and Troubleshooting

## Overview
The AWS Sync functionality pushes data from the local SQLite database to the production AWS PostgreSQL database.

## Issues Fixed
1. **content_hash constraint violation** - Articles without content_hash were causing sync failures
2. **Missing content_hash column** - Added content_hash column to AWS database schema
3. **Sync disabled by default** - Created scripts to enable and test sync

## Setup Instructions

### 1. Configure AWS Database Credentials
Edit `.env` file and add your AWS database credentials:
```bash
AWS_DB_HOST=your-aws-db-host
AWS_DB_PORT=5432
AWS_DB_NAME=news_db_fe
AWS_DB_USER=your-db-user
AWS_DB_PASSWORD=your-db-password
```

### 2. Enable AWS Sync
Run the enable script:
```bash
python enable_aws_sync.py
```
This will update your `.env` to enable:
- `IS_LOCAL_DEV=true`
- `SCHEDULE_AWS_SYNC_ENABLED=true`
- `SCHEDULE_AWS_SYNC_MINUTES=*/5`

### 3. Fix Existing Articles
Generate content_hash for existing articles:
```bash
python fix_content_hash.py
```

### 4. Test the Connection
Test AWS connectivity:
```bash
python test_aws_sync.py
```

### 5. Run Manual Sync
Trigger sync immediately:
```bash
python trigger_aws_sync.py
```

## Sync Methods

### 1. Automated Sync (via Celery Beat)
- Runs every 5 minutes (configurable)
- Syncs only changed articles (delta sync)
- Syncs categories, sources, wishes, polls
- Handles bidirectional vote sync for polls

### 2. Manual Sync Scripts
- `sync_articles.py` - Standard sync with content_hash fix
- `nuclear_sync.py` - Force sync ALL articles
- `trigger_aws_sync.py` - Manual Celery task trigger

### 3. Full Integrity Sync
```python
from app.tasks.celery_app import full_integrity_sync
full_integrity_sync()
```

## Troubleshooting

### Issue: "null value in column content_hash violates not-null constraint"
**Solution**: Run `python fix_content_hash.py` to generate missing content_hash values.

### Issue: AWS connection timeout
**Solution**: Check AWS credentials in `.env` and network connectivity.

### Issue: Sync not running
**Solution**: 
1. Ensure `IS_LOCAL_DEV=true` in `.env`
2. Ensure `SCHEDULE_AWS_SYNC_ENABLED=true` in `.env`
3. Check Celery worker is running: `celery -A app.tasks.celery_app worker --loglevel=info`
4. Check Celery beat is running: `celery -A app.tasks.celery_app beat --loglevel=info`

### Issue: psycopg2 not installed
**Solution**: Install required package:
```bash
pip install psycopg2-binary
```

## Monitoring

### Check Sync Status
```bash
# Check last sync metadata
python -c "
from app.database import SyncSessionLocal
from app.models.models import SyncMetadata
db = SyncSessionLocal()
meta = db.query(SyncMetadata).filter(SyncMetadata.target=='AWS_PROD').first()
if meta:
    print(f'Last sync: {meta.last_sync_at}')
    print(f'Rows OK: {meta.last_rows_ok}, Rows Err: {meta.last_rows_err}')
else:
    print('No sync metadata found')
db.close()
"
```

### Check AWS Article Count
```bash
python check_aws_articles.py
```

### Check AWS Sources
```bash
python check_aws_db.py
```

## Data Flow
1. Local SQLite (master) → AWS PostgreSQL (production)
2. Categories, Sources, Articles, Wishes, Polls synced
3. Vote counts sync bidirectional (AWS → local for poll votes)
4. Delta sync only transfers changed data
5. Conflict resolution uses "ON CONFLICT" with UPDATE

## Security Notes
- AWS credentials should be kept secure
- Use IAM roles with minimal required permissions
- Consider using AWS Secrets Manager for production
