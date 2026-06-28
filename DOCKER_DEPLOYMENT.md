# Docker Deployment Guide

This guide explains how to build and deploy the Fraud Detection API using Docker.

## Prerequisites

- Docker installed on your machine
- Docker Hub account (for pushing images)
- Your `GEMINI_API_KEY`

## Quick Start - Local Testing

### Using Docker Compose (Easiest)

1. **Set your environment variable:**
   ```bash
   # Windows PowerShell
   $env:GEMINI_API_KEY="your_key_here"
   
   # Linux/Mac
   export GEMINI_API_KEY="your_key_here"
   ```

2. **Start the service:**
   ```bash
   docker-compose up
   ```

3. **Access the API:**
   - Health Check: http://localhost:8000/health
   - API Docs: http://localhost:8000/api/docs
   - API Root: http://localhost:8000

4. **Stop the service:**
   ```bash
   docker-compose down
   ```

### Using Docker Directly

1. **Build the image:**
   ```bash
   docker build -t fraud-detection-api .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8000:8000 \
     -e GEMINI_API_KEY=your_key_here \
     fraud-detection-api
   ```

3. **Run in background:**
   ```bash
   docker run -d -p 8000:8000 \
     --name fraud-api \
     -e GEMINI_API_KEY=your_key_here \
     fraud-detection-api
   ```

4. **View logs:**
   ```bash
   docker logs fraud-api
   ```

5. **Stop the container:**
   ```bash
   docker stop fraud-api
   docker rm fraud-api
   ```

## Deploy to Cloud Platforms

### Option 1: Render.com

1. **Push code to GitHub** (including Dockerfile)

2. **Create Web Service on Render:**
   - Go to https://render.com/
   - New → Web Service
   - Connect your GitHub repository
   - **Important:** Select "Docker" as Environment
   - Render auto-detects your Dockerfile

3. **Add Environment Variables:**
   ```
   GEMINI_API_KEY=your_actual_key
   API_HOST=0.0.0.0
   API_PORT=10000
   ```

4. **Deploy!**
   - Render builds and deploys automatically
   - You'll get a public URL like: `https://fraud-detection-api.onrender.com`

### Option 2: Railway.app

1. **Push code to GitHub**

2. **Deploy on Railway:**
   - Go to https://railway.app/
   - New Project → Deploy from GitHub repo
   - Select your repository
   - Railway auto-detects Dockerfile

3. **Add Environment Variables:**
   - Click on your service → Variables
   - Add `GEMINI_API_KEY` and other vars

4. **Railway automatically deploys!**

### Option 3: Docker Hub + Any Server

1. **Login to Docker Hub:**
   ```bash
   docker login
   ```

2. **Build and tag your image:**
   ```bash
   docker build -t your-dockerhub-username/fraud-detection-api:latest .
   ```

3. **Push to Docker Hub:**
   ```bash
   docker push your-dockerhub-username/fraud-detection-api:latest
   ```

4. **Deploy on any server:**
   ```bash
   # On your server (Digital Ocean, AWS, etc.)
   docker pull your-dockerhub-username/fraud-detection-api:latest
   
   docker run -d -p 80:8000 \
     --name fraud-api \
     -e GEMINI_API_KEY=your_key \
     --restart unless-stopped \
     your-dockerhub-username/fraud-detection-api:latest
   ```

### Option 4: Fly.io

1. **Install Fly CLI:**
   ```bash
   # Windows PowerShell
   iwr https://fly.io/install.ps1 -useb | iex
   
   # Linux/Mac
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login:**
   ```bash
   fly auth login
   ```

3. **Launch app:**
   ```bash
   fly launch
   ```

4. **Set secrets:**
   ```bash
   fly secrets set GEMINI_API_KEY=your_key
   ```

5. **Deploy:**
   ```bash
   fly deploy
   ```

## Environment Variables

Required environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | None (required) |
| `API_HOST` | Host to bind to | `0.0.0.0` |
| `API_PORT` | Port to run on | `8000` |
| `DATABASE_URL` | SQLite database URL | `sqlite:///./forensic_records.db` |
| `MAX_FILE_SIZE_MB` | Max upload size | `50` |

## Testing Your Deployment

### Health Check
```bash
curl https://your-deployed-url.com/health
```

### Test Forensics Endpoint
```bash
curl -X POST "https://your-deployed-url.com/api/v1/forensics/analyze?doc_type=noa" \
  -F "file=@/path/to/test.pdf"
```

### Access API Documentation
Open in browser: `https://your-deployed-url.com/api/docs`

## Troubleshooting

### Build Fails
- Check Docker is running: `docker --version`
- Clean build: `docker build --no-cache -t fraud-detection-api .`

### Container Exits Immediately
- Check logs: `docker logs fraud-api`
- Verify environment variables are set

### Port Already in Use
- Use different port: `docker run -p 8080:8000 ...`

### API Not Responding
- Check health: `docker exec fraud-api curl http://localhost:8000/health`
- View logs: `docker logs -f fraud-api`

## Production Recommendations

1. **Use Environment Variables** - Never hardcode secrets
2. **Enable HTTPS** - Use a reverse proxy like Nginx or Caddy
3. **Set Resource Limits:**
   ```bash
   docker run --memory="2g" --cpus="1.0" ...
   ```
4. **Monitor Logs** - Use logging service
5. **Backup Database** - Regular backups of `forensic_records.db`

## Security Notes

- `.env` file is excluded via `.dockerignore`
- Database stored in persistent volume
- Health checks enabled for container orchestration
- Runs as non-root user in production (can be added)

## Support

For issues, check:
- Docker logs: `docker logs fraud-api`
- Application logs: Inside container at `/app`
- Health endpoint: `/health`

