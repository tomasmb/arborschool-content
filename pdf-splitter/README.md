# PDF Splitter Lambda Function

AWS Lambda function for intelligently splitting multi-question PDFs into individual question files using AI-powered analysis.

## 📍 Production Endpoint

**processPdf**: _Will be shown after first deployment_

## 🚀 Quick Deploy

```bash
cd src/lambda/pdf-splitter
./deploy.sh
```

## 📁 Project Structure

```
src/lambda/pdf-splitter/
├── lambda_handler.py      # AWS Lambda handler
├── main.py                # Core splitting logic (13KB)
├── modules/               # Supporting modules
│   ├── pdf_processor.py  # PDF extraction & parsing
│   ├── pdf_utils.py      # PDF utilities (22KB)
│   ├── chunk_segmenter.py # Question segmentation (15KB)
│   ├── bbox_computer.py  # Bounding box calculations (15KB)
│   ├── block_matcher.py  # Content block matching (10KB)
│   ├── quality_validator.py # Split quality validation (8KB)
│   ├── part_validator.py # Part validation
│   └── split_decision.py # Split decision logic
├── requirements.txt      # Python dependencies
├── serverless.yml       # Serverless Framework config
├── package.json         # NPM deployment scripts
└── deploy.sh            # One-command deployment
```

## 🛠️ Common Commands

```bash
# Deploy to production
./deploy.sh

# Deploy to development
./deploy.sh dev

# View real-time logs
npm run logs

# Get deployment info
npm run info
```

## 🔧 How It Works

The PDF Splitter uses AI-powered analysis to:

1. **Extract PDF content** - Parse text, images, and layout from multi-question PDFs
2. **Detect question boundaries** - Identify where each question starts and ends
3. **Segment intelligently** - Split PDF into individual question files
4. **Validate quality** - Ensure each split question is complete and valid
5. **Upload to S3** - Store individual question PDFs

## 📦 Dependencies

- **PyMuPDF** (1.26.0) - PDF processing
- **boto3** (1.36.13) - AWS S3 integration
- **OpenAI** (1.91.0) - AI-powered question detection
- **pydantic** (2.11.5) - Data validation
- **httpx** (0.27.0) - HTTP client

## ⚙️ Technical Details

- **Runtime**: Python 3.11
- **Timeout**: 900 seconds (15 minutes)
- **Memory**: 3,008 MB
- **Permissions**: S3 read/write access to `tomas-ccc-public` bucket

## 🔍 API Usage

```bash
curl -X POST "https://YOUR-FUNCTION-URL/" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_url": "https://example.com/multi-question-test.pdf",
    "openai_api_key": "sk-...",
    "s3_bucket": "tomas-ccc-public",
    "s3_prefix": "questions/"
  }'
```

## 🎯 Next Steps

1. **Deploy** - Run `./deploy.sh` to deploy the function
2. **Test** - Use the function URL to test with a multi-question PDF
3. **Integrate** - Connect with your API for automated PDF splitting

## 📚 Related Services

This Lambda works together with:
- **[PDF-to-QTI](../pdf-to-qti/)** - Converts individual question PDFs to QTI format
- **CCC API** - Manages test questions and PDF processing workflows
