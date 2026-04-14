# Deployment Debugging Guide

## Quick Tests to Identify the Issue

### 1. Browser Cache Test
```bash
# Open in incognito/private mode
# Or hard refresh with Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)
```

### 2. Check Which Deployment is Active
```bash
# If using S3 deployment:
http://peoples-feedback-[your-username].s3-website.ap-south-1.amazonaws.com

# If using EC2 deployment:
http://32.193.27.142
http://32.193.27.142/admin/
```

### 3. Verify Backend API
```bash
curl http://32.193.27.142:8005/docs
curl http://32.193.27.142:8005/health
```

### 4. Check Deployment Logs
```bash
# SSH into EC2 to check backend logs
ssh -i your-key.pem ubuntu@32.193.27.142
tail -f ~/news-platform-final/backend/backend.log
```

## Common Issues & Solutions

### Issue 1: Browser Caching
- **Symptom**: Old UI appears despite successful deployment
- **Solution**: Clear browser cache or use incognito mode

### Issue 2: Backend Not Restarting
- **Symptom**: New frontend but old API responses
- **Check**: `ps aux | grep uvicorn` on EC2
- **Fix**: Manually restart backend
```bash
sudo kill -9 $(sudo lsof -t -i :8005)
cd ~/news-platform-final/backend
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 2 &
```

### Issue 3: Nginx Cache
- **Symptom**: Static files not updating
- **Solution**: Restart Nginx instead of reload
```bash
sudo systemctl restart nginx
```

### Issue 4: Wrong Deployment Target
- **Check**: Which workflow is actually running?
- **Verify**: GitHub Actions run logs

## Manual Deployment Commands

### Force Redeploy to EC2
```bash
# Trigger workflow manually
git commit --allow-empty -m "Force redeploy"
git push origin main
```

### Direct SSH Deployment
```bash
ssh -i your-key.pem ubuntu@32.193.27.142
cd ~/news-platform-final/backend
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# Restart services as needed
```
