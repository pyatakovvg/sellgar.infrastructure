#!/usr/bin/env python3
"""Configure an isolated Media bucket identity, preserving existing objects and users."""
import base64
import json
import subprocess
import sys

kubectl = sys.argv[1:]
if not kubectl:
    raise SystemExit('Usage: initialize-media.py <kubectl> --kubeconfig <path>')
secret = json.loads(subprocess.check_output(
    [*kubectl, '-n', 'sellgar-dev', 'get', 'secret', 'media-storage', '-o', 'json'], text=True,
))['data']
username, password = [base64.b64decode(secret[key]).decode() for key in ('username', 'password')]
policy = json.dumps({'Version': '2012-10-17', 'Statement': [
    {'Effect': 'Allow', 'Action': ['s3:GetBucketLocation', 's3:ListBucket', 's3:ListBucketMultipartUploads'],
     'Resource': ['arn:aws:s3:::sellgar']},
    {'Effect': 'Allow', 'Action': ['s3:GetObject', 's3:PutObject', 's3:DeleteObject',
                                  's3:AbortMultipartUpload', 's3:ListMultipartUploadParts'],
     'Resource': ['arn:aws:s3:::sellgar/*']},
]})
script = r'''
set -eu
IFS= read -r media_user
IFS= read -r media_password
IFS= read -r media_policy
config_dir=$(mktemp -d /tmp/media-bootstrap.XXXXXX)
trap 'rm -rf "$config_dir"' EXIT
export MC_CONFIG_DIR="$config_dir"
export MC_HOST_bootstrap="http://${MINIO_ROOT_USER}:${MINIO_ROOT_PASSWORD}@127.0.0.1:9000"
printf '%s' "$media_policy" > "$config_dir/policy.json"
mc mb --ignore-existing bootstrap/sellgar >/dev/null
if ! mc admin user info bootstrap "$media_user" >/dev/null 2>&1; then
  mc admin user add bootstrap "$media_user" "$media_password" >/dev/null
fi
mc admin policy create bootstrap sellgar-media "$config_dir/policy.json" >/dev/null
mc admin policy attach bootstrap sellgar-media --user "$media_user" >/dev/null
export MC_HOST_media="http://${media_user}:${media_password}@127.0.0.1:9000"
mc stat media/sellgar >/dev/null
printf 'Media bucket and restricted credentials verified\n'
'''
subprocess.run(
    [*kubectl, '-n', 'sellgar-dev', 'exec', '-i', 'minio-0', '--', 'sh', '-c', script],
    input=f'{username}\n{password}\n{policy}\n', text=True, check=True,
)
