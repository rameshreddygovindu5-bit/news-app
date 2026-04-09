# Peoples Feedback — News Client

Public news website deployed on EC2 (`i-0e448dd106cf9aeed`).

## Deploy (automatic)
Every push to `main` triggers GitHub Actions → builds → deploys to EC2.

### One-time setup:
1. SSH into EC2: `ssh -i key.pem ubuntu@<EC2_IP>`
2. Run: `sudo bash setup-ec2.sh`
3. Add GitHub Secrets (repo → Settings → Secrets):
   - `EC2_HOST` = EC2 public IP
   - `EC2_USER` = `ubuntu`
   - `EC2_SSH_KEY` = contents of your .pem file
   - `VITE_API_URL` = `http://<EC2_IP>:8005`
4. Push to `main` → auto-deploys

### Local dev:
```bash
npm install
npm run dev   # http://localhost:3001
```
Backend must be running on port 8005.
