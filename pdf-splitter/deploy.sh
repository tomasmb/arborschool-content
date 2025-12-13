#!/bin/bash
set -e

echo "🚀 Deploying PDF Splitter Lambda Function"
echo "========================================="

# Check if serverless is installed
if ! command -v serverless &> /dev/null; then
    echo "📦 Installing Serverless Framework..."
    npm install
fi

# Check AWS credentials
if ! aws sts get-caller-identity --profile saml-prod &> /dev/null; then
    echo "❌ AWS credentials not found or expired for profile 'saml-prod'"
    echo "Please configure AWS credentials first"
    exit 1
fi

echo "✅ AWS credentials verified"

# Deploy
STAGE=${1:-prod}
echo "📤 Deploying to stage: $STAGE"

if [ "$STAGE" = "prod" ]; then
    npx serverless deploy --stage prod --aws-profile saml-prod --verbose
else
    npx serverless deploy --stage "$STAGE" --aws-profile saml-prod --verbose
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 To view logs:"
echo "   npm run logs"
echo ""
echo "📊 To get deployment info:"
echo "   npm run info"
