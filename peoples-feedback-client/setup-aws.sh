#!/bin/bash
# ═══════════════════════════════════════════════════════
# One-time AWS S3 setup for Peoples Feedback Client
# Account: 023036697290
#
# Prerequisites:
#   1. AWS CLI installed: brew install awscli / pip install awscli
#   2. IAM user with S3FullAccess policy
#   3. aws configure (with access key + secret)
#
# Usage: ./setup-aws.sh
# ═══════════════════════════════════════════════════════
set -e
REGION="ap-south-1"
BUCKET="peoples-feedback-news"

echo "Creating S3 bucket: $BUCKET in $REGION..."
aws s3 mb "s3://$BUCKET" --region $REGION 2>/dev/null || echo "Bucket exists"

echo "Enabling static website hosting..."
aws s3 website "s3://$BUCKET" --index-document index.html --error-document index.html

echo "Setting public access..."
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

aws s3api put-bucket-policy --bucket "$BUCKET" --policy "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{
    \"Sid\": \"PublicRead\",
    \"Effect\": \"Allow\",
    \"Principal\": \"*\",
    \"Action\": \"s3:GetObject\",
    \"Resource\": \"arn:aws:s3:::${BUCKET}/*\"
  }]
}"

echo ""
echo "═══════════════════════════════════════════════════"
echo "S3 bucket ready!"
echo "Website URL: http://${BUCKET}.s3-website.${REGION}.amazonaws.com"
echo ""
echo "Next steps:"
echo "1. Add these GitHub Secrets to your repo:"
echo "   AWS_ACCESS_KEY_ID     = (your IAM access key)"
echo "   AWS_SECRET_ACCESS_KEY = (your IAM secret key)"
echo "   VITE_API_URL          = http://32.193.27.142:8005"
echo ""
echo "2. In Hostinger DNS, add CNAME:"
echo "   www -> ${BUCKET}.s3-website.${REGION}.amazonaws.com"
echo "═══════════════════════════════════════════════════"
