# How to Add AmazonS3FullAccess Policy to news-app User

## Step 1: Sign in to AWS Console
1. Go to: https://console.aws.amazon.com/
2. Sign in with your AWS account credentials

## Step 2: Navigate to IAM Service
1. In the search bar at the top, type "IAM" 
2. Click on "IAM" from the dropdown
3. Or go directly to: https://console.aws.amazon.com/iam/

## Step 3: Go to Users
1. In the left navigation menu, click on "Users"
2. Find and click on the user named: `news-app`

## Step 4: Add Permissions
1. Scroll down to the "Permissions policies" section
2. Click the "Add permissions" dropdown button
3. Select "Attach policies" from the dropdown

## Step 5: Find and Attach AmazonS3FullAccess
1. In the "Filter policies" search box, type: `AmazonS3FullAccess`
2. Check the box next to "AmazonS3FullAccess"
3. Click the "Attach policies" button at the bottom right

## Step 6: Verify the Policy
1. You should now see "AmazonS3FullAccess" listed under "Permissions policies"
2. The user now has full S3 access

## Alternative: Using AWS CLI (if you have admin permissions)

If you have admin permissions, you can run this command:

```bash
aws iam attach-user-policy \
    --user-name news-app \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

## After Adding Permissions

Once the policy is attached:
1. The GitHub Actions workflow will be able to:
   - Create S3 buckets
   - Upload files to S3
   - Set bucket policies
   - Configure static website hosting

2. Your deployment will work automatically when you push to main branch

## Security Note

AmazonS3FullAccess gives full S3 permissions. For production, consider creating a custom policy with only the specific permissions needed:
- s3:CreateBucket
- s3:PutBucketPolicy  
- s3:PutPublicAccessBlock
- s3:DeleteBucketPolicy
- s3:GetObject
- s3:PutObject
- s3:DeleteObject
- s3:ListBucket

## Troubleshooting

If you don't see the "news-app" user:
1. Make sure you're in the correct AWS account (023036697290)
2. Check if the user exists under IAM > Users
3. If not, you may need to create the user first

If you can't attach policies:
1. Make sure you have IAM admin permissions
2. Contact your AWS administrator if needed
