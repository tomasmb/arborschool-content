# PDF-to-QTI Lambda Deployment Guide

## Overview

This directory contains the AWS Lambda functions for converting PDF questions to QTI 3.0 XML format.

**Production Endpoints:**
- convertPdfToQti: https://6yuvwmyy6mjtu5ojqbkindumpq0zaxwv.lambda-url.us-east-1.on.aws/
- questionDetail: https://dwz3c4pziukfhwfqkkauvzh4bu0uicgu.lambda-url.us-east-1.on.aws/

## Project Structure

```
src/lambda/pdf-to-qti/
├── lambda_handler.py           # Main PDF-to-QTI conversion handler
├── question_detail_handler.py  # Question metadata extraction handler
├── main.py                     # Core conversion logic
├── modules/                    # Supporting modules
│   ├── pdf_processor.py       # PDF extraction
│   ├── question_detector.py   # Question type detection
│   ├── qti_transformer.py     # QTI XML generation
│   ├── question_evaluator.py  # Question validation
│   ├── prompt_builder.py      # AI prompt construction
│   └── qti_configs.py         # QTI configurations
├── requirements.txt           # Python dependencies
├── serverless.yml            # Serverless Framework config
├── package.json              # NPM scripts for deployment
└── deploy.sh                 # Deployment script
```

## Quick Start

### Deploy to Production

```bash
cd src/lambda/pdf-to-qti
./deploy.sh
```

### Deploy to Development

```bash
./deploy.sh dev
```

## Prerequisites

1. **Node.js 18+** (for Serverless Framework)
2. **Python 3.11**
3. **Docker** (for building Python dependencies)
4. **AWS CLI** configured with `saml-prod` profile
5. **Valid AWS credentials** with Lambda deployment permissions

## Installation

```bash
cd src/lambda/pdf-to-qti

# Install Serverless Framework and plugins
npm install

# Verify AWS credentials
aws sts get-caller-identity --profile saml-prod
```

## Deployment

### Using the Deploy Script (Recommended)

```bash
# Deploy to production
./deploy.sh

# Deploy to development
./deploy.sh dev
```

### Using NPM Scripts

```bash
# Deploy to production
npm run deploy

# Deploy to development
npm run deploy:dev

# Deploy only a specific function (faster)
npm run deploy:function -- -f convertPdfToQti
```

### Using Serverless CLI Directly

```bash
# Full deployment
serverless deploy --stage prod --aws-profile saml-prod --verbose

# Deploy single function
serverless deploy function -f convertPdfToQti --stage prod --aws-profile saml-prod
```

## Monitoring

### View Logs

```bash
# Real-time logs for convertPdfToQti
npm run logs

# Real-time logs for questionDetail
npm run logs:detail

# Or using serverless directly
serverless logs -f convertPdfToQti --stage prod --tail
```

### Get Deployment Info

```bash
npm run info

# Shows:
# - Function names
# - Function URLs
# - Runtime information
# - Memory/timeout settings
```

## Making Changes

1. **Edit the code** in this directory
2. **Test locally** if possible (see Testing section)
3. **Deploy your changes:**
   ```bash
   ./deploy.sh
   ```
4. **Monitor the deployment** in the output
5. **Test the deployed function** using curl or the API

## Testing Locally

### Test with a local PDF

```bash
# Activate Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test the main conversion logic
python main.py test_question.pdf output/ --openai-api-key $OPENAI_API_KEY
```

### Test the deployed Lambda

```bash
# Test convertPdfToQti endpoint
curl -X POST "https://6yuvwmyy6mjtu5ojqbkindumpq0zaxwv.lambda-url.us-east-1.on.aws/" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_url": "https://example.com/question.pdf",
    "openai_api_key": "sk-..."
  }'

# Test questionDetail endpoint
curl -X POST "https://dwz3c4pziukfhwfqkkauvzh4bu0uicgu.lambda-url.us-east-1.on.aws/" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_url": "https://example.com/question.pdf",
    "openai_api_key": "sk-..."
  }'
```

## Troubleshooting

### Deployment Issues

**Problem: Docker not running**
```
Error: Docker is not running
```
**Solution:** Start Docker Desktop

**Problem: AWS credentials expired**
```
Error: The security token included in the request is expired
```
**Solution:** Refresh your AWS SSO credentials

**Problem: Package too large**
```
Error: Code storage limit exceeded
```
**Solution:** The serverless config uses `slim: true` to reduce package size. If issues persist, check for unnecessary files.

### Runtime Issues

**Check CloudWatch Logs:**
```bash
serverless logs -f convertPdfToQti --stage prod --startTime 1h
```

**Common Issues:**
- **Timeout:** Increase timeout in `serverless.yml` (max 900s)
- **Memory:** Increase memorySize in `serverless.yml` (max 10240 MB)
- **Dependencies:** Ensure all dependencies are in `requirements.txt`

## Configuration

### Environment Variables

Edit `serverless.yml` to add/modify environment variables:

```yaml
provider:
  environment:
    QTI_VALIDATION_ENDPOINT: http://your-validator.com/validate
    # Add more variables here
```

### Function Settings

Edit `serverless.yml` to modify function configuration:

```yaml
functions:
  convertPdfToQti:
    timeout: 900        # Execution timeout (seconds)
    memorySize: 3008    # Memory allocation (MB)
    # Add more settings
```

## Rollback

If a deployment causes issues:

```bash
# List deployments
serverless deploy list --stage prod

# Rollback to previous deployment
serverless rollback --timestamp TIMESTAMP --stage prod
```

## Cleanup

To remove all Lambda functions:

```bash
npm run remove
# or
serverless remove --stage prod --aws-profile saml-prod
```

**⚠️ WARNING:** This will delete all functions and cannot be undone!

## CI/CD Integration

For automated deployments, use:

```bash
# In your CI/CD pipeline
cd src/lambda/pdf-to-qti
npm ci
serverless deploy --stage prod --aws-profile saml-prod
```

## Additional Resources

- [Serverless Framework Docs](https://www.serverless.com/framework/docs)
- [AWS Lambda Docs](https://docs.aws.amazon.com/lambda/)
- [Python Requirements Plugin](https://github.com/serverless/serverless-python-requirements)
