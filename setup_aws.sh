#!/bin/bash
# AWS S3 Setup Script for Network Monitor
# This script creates the S3 bucket and configures it for static website hosting

set -e

# Configuration
BUCKET_NAME="s3bucket"
REGION="eu-west-2"

echo "=========================================="
echo "Network Monitor - AWS S3 Setup"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    echo "Install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

echo "Using bucket name: $BUCKET_NAME"
echo "Region: $REGION"
echo ""

# Create S3 bucket
echo "Creating S3 bucket..."
if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"
else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION"
fi

# Disable block public access for website hosting
echo "Configuring public access..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# Enable static website hosting
echo "Enabling static website hosting..."
aws s3 website "s3://$BUCKET_NAME/" \
    --index-document index.html \
    --error-document index.html

# Create bucket policy for public read access to website files
echo "Setting bucket policy..."
cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": [
        "arn:aws:s3:::$BUCKET_NAME/index.html",
        "arn:aws:s3:::$BUCKET_NAME/dashboard.js",
        "arn:aws:s3:::$BUCKET_NAME/locations.json",
        "arn:aws:s3:::$BUCKET_NAME/summaries/*"
      ]
    }
  ]
}
EOF

aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --policy file:///tmp/bucket-policy.json

rm /tmp/bucket-policy.json

# Enable CORS for API access
echo "Configuring CORS..."
cat > /tmp/cors.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws s3api put-bucket-cors \
    --bucket "$BUCKET_NAME" \
    --cors-configuration file:///tmp/cors.json

rm /tmp/cors.json

# Create IAM user for Raspberry Pi (optional but recommended)
echo ""
echo "Creating IAM user for Raspberry Pi..."
IAM_USER="network-monitor-pi"

if aws iam get-user --user-name "$IAM_USER" &> /dev/null; then
    echo "IAM user $IAM_USER already exists"
else
    aws iam create-user --user-name "$IAM_USER"
    
    # Create and attach policy
    cat > /tmp/pi-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::$BUCKET_NAME"
    }
  ]
}
EOF
    
    aws iam put-user-policy \
        --user-name "$IAM_USER" \
        --policy-name "NetworkMonitorS3Access" \
        --policy-document file:///tmp/pi-policy.json
    
    rm /tmp/pi-policy.json
    
    # Create access key
    echo ""
    echo "Creating access key for Raspberry Pi..."
    KEY_OUTPUT=$(aws iam create-access-key --user-name "$IAM_USER")
    
    ACCESS_KEY=$(echo "$KEY_OUTPUT" | grep -o '"AccessKeyId": "[^"]*' | cut -d'"' -f4)
    SECRET_KEY=$(echo "$KEY_OUTPUT" | grep -o '"SecretAccessKey": "[^"]*' | cut -d'"' -f4)
    
    echo ""
    echo "=========================================="
    echo "IMPORTANT: Save these credentials!"
    echo "=========================================="
    echo "Access Key ID: $ACCESS_KEY"
    echo "Secret Access Key: $SECRET_KEY"
    echo ""
    echo "Configure on Raspberry Pi with:"
    echo "  aws configure"
    echo "=========================================="
fi

# Get website URL
WEBSITE_URL="http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo "Bucket: $BUCKET_NAME"
echo "Region: $REGION"
echo "Website URL: $WEBSITE_URL"
echo ""
echo "Next steps:"
echo "1. Upload index.html: aws s3 cp index.html s3://$BUCKET_NAME/"
echo "2. Configure Raspberry Pi with AWS credentials"
echo "3. Update config.json with bucket name: $BUCKET_NAME"
echo "4. Run network_monitor.py on Raspberry Pi"
echo "=========================================="
