# Document Fraud Detection API

FastAPI backend for detecting fraudulent tax documents using forensic analysis.

## Features

- 🔍 **Forensic Analysis**: Comprehensive document forensics (alignment, fonts, metadata, etc.)
- 📊 **Document Comparison**: T1 vs NOA cross-validation
- 🗄️ **Database Tracking**: NOA ID duplicate detection
- 📸 **Multi-Format Support**: PDF, JPEG, PNG
- 📚 **Auto-Generated Docs**: Swagger UI and ReDoc
- 🔒 **Secure**: CORS, file validation, error handling

## Quick Start

### 1. Installation

```bash
cd fraud-detection-api
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file from example:
```bash
# Copy the settings
GEMINI_API_KEY=your_actual_key_here
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
CORS_ORIGINS=http://localhost:3000,http://localhost:8501
MAX_FILE_SIZE_MB=50
FRAUD_DETECTION_CODE_PATH=../fraud-detection-poc
```

### 3. Run Server

```bash
python run.py
```

Server starts at: `http://localhost:8000`

### 4. View Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Forensic Analysis

**POST** `/api/v1/forensics/analyze`

Upload document for forensic analysis.

```bash
curl -X POST "http://localhost:8000/api/v1/forensics/analyze?doc_type=noa" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "overall_score": 25.5,
  "risk_level": "LOW",
  "alignment": {
    "risk_score": 20,
    "applicable": true,
    "issues": []
  },
  "fonts": {
    "risk_score": 30,
    "applicable": true
  },
  "noa_id_check": {
    "risk_score": 0,
    "id_number": "5X4YR5JX",
    "is_duplicate": false
  },
  "processing_time": 8.234,
  "file_name": "document.pdf",
  "doc_type": "noa"
}
```

### Document Comparison

**POST** `/api/v1/comparison/validate`

Compare T1 and NOA documents.

```bash
curl -X POST "http://localhost:8000/api/v1/comparison/validate" \
  -F "t1_file=@t1.pdf" \
  -F "noa_file=@noa.pdf"
```

**Response:**
```json
{
  "overall_risk": "low",
  "checks": [
    {
      "check": "SIN Match",
      "status": "pass",
      "confidence": 95,
      "details": "SIN numbers match"
    }
  ],
  "t1_data": {...},
  "noa_data": {...},
  "processing_time": 12.5
}
```

### Database Access

**GET** `/api/v1/forensics/records` - Get all records  
**GET** `/api/v1/forensics/duplicates` - Get duplicate detections  
**GET** `/api/v1/forensics/check-duplicate/{id}` - Check if ID exists  
**GET** `/api/v1/forensics/stats` - Get database statistics

```bash
# Get all records
curl http://localhost:8000/api/v1/forensics/records

# Get statistics
curl http://localhost:8000/api/v1/forensics/stats
```

### Utility Endpoints

**GET** `/api/v1/forensics/supported-formats` - Get supported formats  
**GET** `/api/v1/forensics/checks` - Get list of all checks  
**GET** `/health` - Health check  
**GET** `/` - API information

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
fraud-detection-api/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   └── api/v1/
│       ├── routes/          # API endpoints
│       │   ├── forensics.py
│       │   ├── comparison.py
│       │   └── database.py
│       └── schemas/         # Request/response models
│           ├── forensics.py
│           └── comparison.py
├── tests/                   # Test files
├── .env                     # Environment variables
├── .gitignore              # Git ignore rules
├── requirements.txt         # Dependencies
├── run.py                   # Application runner
└── README.md               # This file
```

## Development

### Adding New Endpoints

1. Create route file in `app/api/v1/routes/`
2. Define schemas in `app/api/v1/schemas/`
3. Include router in `app/main.py`

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Server host | 0.0.0.0 |
| `API_PORT` | Server port | 8000 |
| `API_RELOAD` | Auto-reload on changes | true |
| `GEMINI_API_KEY` | Google Gemini API key | None |
| `MAX_FILE_SIZE_MB` | Max upload size | 50 |
| `CORS_ORIGINS` | Allowed CORS origins | localhost:3000,8501 |
| `FRAUD_DETECTION_CODE_PATH` | Path to existing code | ../fraud-detection-poc |

## Error Handling

The API uses standard HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid file, wrong format, etc.)
- `500` - Internal Server Error

Error responses include:
```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "type": "ExceptionType"
}
```

## Security

- **File Validation**: Size and type checking
- **CORS**: Configurable origins
- **Error Masking**: Internal errors don't expose sensitive info
- **Temporary Files**: Cleaned up after processing

## Deployment

### Local Development
```bash
python run.py
```

### Production (Gunicorn)
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker
```bash
docker build -t fraud-detection-api .
docker run -p 8000:8000 --env-file .env fraud-detection-api
```

### Cloud Platforms

- **Railway**: Connect GitHub repo, configure env vars, deploy
- **Google Cloud Run**: `gcloud run deploy`
- **AWS Lambda**: Use Mangum adapter
- **DigitalOcean**: App Platform deployment

## Troubleshooting

### Import Errors

If you get "cannot import forensics":

1. Check that `fraud-detection-poc/` exists at `../fraud-detection-poc`
2. Verify `FRAUD_DETECTION_CODE_PATH` in `.env`
3. Try absolute path: `C:\Users\...\fraud-detection-poc`

### Port Already in Use

```bash
# Change port in .env
API_PORT=8001
```

### Gemini API Not Working

1. Check API key is set in `.env`
2. Verify API key is valid
3. Check you have credits/quota remaining

## Performance

- **Average Response Time**: 3-12 seconds (depending on document size)
- **Max File Size**: 50MB (configurable)
- **Concurrent Requests**: Supports multiple simultaneous uploads
- **Database**: SQLite (shared with Streamlit app)

## License

Private - Internal Use Only

## Support

For issues or questions:
1. Check the `/health` endpoint
2. Review error messages in response
3. Check server logs
4. Verify environment configuration

---

Built with ❤️ using FastAPI




