import os
import boto3
import mimetypes

bucket_name = 'peoples-feedback-rameshreddygovindu5-bit'
dist_dir = os.path.join('peoples-feedback-client', 'dist')
s3 = boto3.client('s3')

print(f"Deploying {dist_dir} to s3://{bucket_name} ...")

for root, dirs, files in os.walk(dist_dir):
    for filename in files:
        # construct the full local path
        local_path = os.path.join(root, filename)
        
        # construct the relative path (S3 key)
        # Using replace to ensure consistent '/' slashes for s3 keys on Windows
        relative_path = os.path.relpath(local_path, dist_dir).replace('\\', '/')
        
        content_type, _ = mimetypes.guess_type(local_path)
        if content_type is None:
            if filename.endswith('.css'): content_type = 'text/css'
            elif filename.endswith('.js'): content_type = 'application/javascript'
            elif filename.endswith('.html'): content_type = 'text/html'
            else: content_type = 'binary/octet-stream'

        extra_args = {'ContentType': content_type}
        
        # Cache control
        if relative_path == 'index.html':
            extra_args['CacheControl'] = 'no-cache, no-store, must-revalidate'
        else:
            extra_args['CacheControl'] = 'public, max-age=31536000, immutable'

        print(f"Uploading {relative_path} ({content_type})")
        s3.upload_file(local_path, bucket_name, relative_path, ExtraArgs=extra_args)

print(f"Deployed successfully to! http://{bucket_name}.s3-website.ap-south-1.amazonaws.com")
