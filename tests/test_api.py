from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)

def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_supported_formats():
    """Test supported formats endpoint"""
    response = client.get("/api/v1/forensics/supported-formats")
    assert response.status_code == 200
    data = response.json()
    assert "formats" in data
    assert "max_size_mb" in data

def test_get_forensic_stats():
    """Test forensic stats endpoint"""
    response = client.get("/api/v1/forensics/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_records" in data

def test_get_forensic_checks():
    """Test get forensic checks endpoint"""
    response = client.get("/api/v1/forensics/checks")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert len(data["checks"]) > 0




