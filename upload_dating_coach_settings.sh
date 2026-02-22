#!/bin/bash
# Upload dating_coach app-settings to S3
# Run: bash upload_dating_coach_settings.sh

set -e

BUCKET="shittyapps-config"
REGION="us-east-1"
FILE="dating_coach.json"
S3_KEY="app-settings/dating_coach.json"

echo "📦 Uploading $FILE to s3://$BUCKET/$S3_KEY ..."

aws s3 cp "$FILE" "s3://$BUCKET/$S3_KEY" \
  --region "$REGION" \
  --content-type "application/json"

echo "✅ Done! Config uploaded."
echo ""
echo "⚠️  Config Service кэширует ответы. Если нужно обновить сразу —"
echo "   передеплой Config Service на Render или подожди пока кэш истечёт."
