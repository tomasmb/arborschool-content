# PDF-to-QTI Lambda Functions

AWS Lambda functions for converting PDF questions to QTI 3.0 XML format.

## 📍 Production Endpoints

- **convertPdfToQti**: https://6yuvwmyy6mjtu5ojqbkindumpq0zaxwv.lambda-url.us-east-1.on.aws/
- **questionDetail**: https://dwz3c4pziukfhwfqkkauvzh4bu0uicgu.lambda-url.us-east-1.on.aws/

## 🚀 Quick Deploy

```bash
cd src/lambda/pdf-to-qti
./deploy.sh
```

That's it! The deploy script will:
1. Check AWS credentials (saml-prod profile)
2. Install dependencies via Serverless Framework
3. Build Python packages with Docker
4. Deploy both Lambda functions
5. Show you the updated function URLs

## 📁 Project Structure

```
src/lambda/pdf-to-qti/
├── lambda_handler.py           # Main PDF→QTI conversion handler
├── question_detail_handler.py  # Question metadata extraction
├── main.py                     # Core conversion logic
├── modules/                    # 10,456 lines of Python code
│   ├── pdf_processor.py       # PDF extraction & parsing
│   ├── question_detector.py   # AI-powered question type detection
│   ├── qti_transformer.py     # QTI XML generation
│   ├── question_evaluator.py  # Question validation
│   ├── prompt_builder.py      # AI prompt construction
│   ├── qti_configs.py         # QTI configurations
│   ├── ai_processing/         # AI content analysis
│   ├── content_processing/    # Content transformation
│   ├── image_processing/      # Image extraction & analysis
│   ├── utils/                 # Utility functions
│   └── validation/            # XML & visual validation
├── requirements.txt           # Python dependencies
├── serverless.yml            # Serverless Framework config
├── package.json              # NPM deployment scripts
├── deploy.sh                 # One-command deployment
└── DEPLOYMENT.md             # Detailed deployment guide
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

# Deploy single function (faster)
npm run deploy:function -- -f convertPdfToQti
```

## 📖 Documentation

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide with troubleshooting
- **[Original README](../../parser/pdf-to-qti/README.md)** - API documentation and examples

## 🔧 Making Changes

1. Edit code in this directory
2. Run `./deploy.sh`
3. Test the deployed function

Changes are deployed in ~2-3 minutes.

## 📦 What's Included

This directory contains the **complete source code** for the PDF-to-QTI Lambda functions recovered from AWS. All 10,456 lines of Python code are now safely version-controlled in this repo.

## ⚙️ Technical Details

- **Runtime**: Python 3.11
- **Timeout**: 900 seconds (15 minutes)
- **Memory**: 3,008 MB
- **Dependencies**: Pillow, PyMuPDF, OpenAI, Selenium, etc.
- **Deployment**: Serverless Framework with Docker for pip packages

## 🎯 Next Steps

1. **Test the current deployment** - Make sure everything works
2. **Make your changes** - Edit the code as needed
3. **Redeploy** - Run `./deploy.sh` to update the Lambda

For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).
