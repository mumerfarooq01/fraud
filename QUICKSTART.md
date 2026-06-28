# FastAPI Backend - Quick Start Guide

## ✅ Setup Complete!

Your FastAPI backend has been successfully created and verified.

## 📁 Project Structure

```
fraud-detection-api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration
│   └── api/v1/
│       ├── routes/                # API endpoints
│       │   ├── forensics.py       # Forensic analysis endpoints
│       │   ├── comparison.py      # Document comparison endpoints
│       │   └── database.py        # Database access endpoints
│       └── schemas/               # Request/response models
│           ├── forensics.py
│           └── comparison.py
├── tests/
│   └── test_api.py                # API tests
├── .env                           # Environment variables ✅
├── .gitignore                     # Git ignore rules ✅
├── requirements.txt               # Dependencies ✅ (installed)
├── run.py                         # Server runner ✅
├── verify_setup.py                # Verification script ✅
└── README.md                      # Full documentation
```

## 🚀 How to Start the Server

### Option 1: Using run.py (Recommended)

```bash
cd C:\Users\qaboo\source\repos\fraud-detection-api
python run.py
```

### Option 2: Using uvicorn directly

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 Access the API

Once started, you can access:

- **Interactive Docs (Swagger UI)**: http://localhost:8000/api/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health
- **API Root**: http://localhost:8000/

## 🔍 Key Endpoints

### 1. Forensic Analysis
```http
POST /api/v1/forensics/analyze?doc_type=noa
Content-Type: multipart/form-data
Body: file (PDF/JPG/PNG)
```

### 2. Document Comparison
```http
POST /api/v1/comparison/validate
Content-Type: multipart/form-data
Body: t1_file (PDF), noa_file (PDF)
```

### 3. Database Access
```http
GET /api/v1/forensics/records
GET /api/v1/forensics/duplicates
GET /api/v1/forensics/stats
GET /api/v1/forensics/check-duplicate/{id_number}
```

### 4. Utility Endpoints
```http
GET /api/v1/forensics/supported-formats
GET /api/v1/forensics/checks
```

## 🧪 Testing with cURL

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Upload Document for Forensic Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/forensics/analyze?doc_type=noa" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@C:\path\to\document.pdf"
```

### Compare T1 and NOA
```bash
curl -X POST "http://localhost:8000/api/v1/comparison/validate" \
  -F "t1_file=@C:\path\to\t1.pdf" \
  -F "noa_file=@C:\path\to\noa.pdf"
```

### Get Database Statistics
```bash
curl http://localhost:8000/api/v1/forensics/stats
```

## 🧪 Run Tests

```bash
pytest tests/ -v
```

## 🔧 Configuration

Your `.env` file is already configured with:

- ✅ Gemini API Key (copied from existing project)
- ✅ CORS origins (allows localhost:8501 for Streamlit app)
- ✅ Path to existing fraud detection code
- ✅ API port 8000

## 📊 What's Next?

### 1. Start the Server
```bash
python run.py
```

### 2. Test in Browser
Open http://localhost:8000/api/docs and try the interactive API documentation

### 3. Test with Python Client
```python
import requests

# Test health
response = requests.get("http://localhost:8000/health")
print(response.json())

# Upload document
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/forensics/analyze?doc_type=noa",
        files={"file": f}
    )
    print(response.json())
```

### 4. Integrate with Frontend
Your Streamlit app can now call this API:
```python
import requests

def analyze_via_api(file_bytes, filename, doc_type):
    response = requests.post(
        "http://localhost:8000/api/v1/forensics/analyze",
        params={"doc_type": doc_type},
        files={"file": (filename, file_bytes, "application/pdf")}
    )
    return response.json()
```

## 🌐 Deploy to Production

### Railway
1. Push to GitHub
2. Connect Railway to your repo
3. Add environment variables
4. Deploy automatically

### Google Cloud Run
```bash
gcloud run deploy fraud-detection-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 💡 Tips

1. **Development**: Keep `API_RELOAD=true` for auto-reload on code changes
2. **Production**: Set `API_RELOAD=false` and use multiple workers
3. **Security**: Update `SECRET_KEY` and `API_KEY` for production
4. **Database**: The API shares the same `forensic_records.db` with Streamlit app
5. **CORS**: Add your frontend URLs to `CORS_ORIGINS` in `.env`

## 🔗 Related Files

- **Full Documentation**: `README.md`
- **Configuration**: `.env`
- **Dependencies**: `requirements.txt`
- **Verification**: Run `python verify_setup.py` anytime

---

✅ **Your API is ready to use!**

Start it with: `python run.py`




