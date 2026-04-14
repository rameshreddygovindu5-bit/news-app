"""
Deploy the Admin UI (news-platform-final/frontend/build) to S3
under the /admin/ prefix of the existing bucket.
"""
import os
import boto3
import mimetypes

bucket_name = 'peoples-feedback-rameshreddygovindu5-bit'
build_dir = os.path.join('news-platform-final', 'frontend', 'build')
s3_prefix = 'admin'  # all files go to s3://bucket/admin/...

s3 = boto3.client('s3')

print(f"Deploying {build_dir} -> s3://{bucket_name}/{s3_prefix}/ ...")

for root, dirs, files in os.walk(build_dir):
    for filename in files:
        local_path = os.path.join(root, filename)
        relative_path = os.path.relpath(local_path, build_dir).replace('\\', '/')
        s3_key = f"{s3_prefix}/{relative_path}"

        content_type, _ = mimetypes.guess_type(local_path)
        if content_type is None:
            if filename.endswith('.css'):   content_type = 'text/css'
            elif filename.endswith('.js'):  content_type = 'application/javascript'
            elif filename.endswith('.html'):content_type = 'text/html'
            else:                           content_type = 'binary/octet-stream'

        extra_args = {'ContentType': content_type}
        if filename == 'index.html':
            extra_args['CacheControl'] = 'no-cache, no-store, must-revalidate'
        else:
            extra_args['CacheControl'] = 'public, max-age=31536000, immutable'

        print(f"  Uploading {s3_key} ({content_type})")
        s3.upload_file(local_path, bucket_name, s3_key, ExtraArgs=extra_args)

print(f"\nAdmin UI deployed!")
print(f"  URL: http://{bucket_name}.s3-website.ap-south-1.amazonaws.com/admin/index.html")
