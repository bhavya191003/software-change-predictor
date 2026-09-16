# API Reference

The Software Change Predictor backend exposes a RESTful API powered by FastAPI.

**Base URL:** `http://localhost:8000`

---

## POST `/analyze`
Initiates a mining and analysis run on a specified repository.

**Request Body (JSON):**
```json
{
  "repo_url": "https://github.com/example/repo",
  "branch": "main",
  "top_n": 50
}
```

**Response (JSON):**
```json
{
  "status": "success",
  "repository": "example/repo",
  "results": [
    {
      "file": "src/main.py",
      "composite_risk": 0.85,
      "risk_level": "Critical",
      "entropy": 4.2
    }
  ]
}
```

---

## GET `/health`
Check the health status of the API server.

**Response:**
```json
{
  "status": "healthy",
  "uptime": "12:34:56"
}
```

---

## GET `/api/info`
Retrieve system version and available models.

**Response:**
```json
{
  "version": "1.0.0",
  "ml_models_loaded": true,
  "supported_metrics": ["entropy", "velocity", "gini"]
}
```

---

## POST `/export/csv`
Export the analysis results as a CSV file.

**Request Body (JSON):**
```json
{
  "analysis_id": "uuid-1234",
  "format": "csv"
}
```

**Response:** Returns a downloadable CSV file attachment.

---

## Error Responses
| Code | Description |
|------|-------------|
| `400 Bad Request` | Invalid parameters provided in the request. |
| `404 Not Found` | Repository or branch not found. |
| `429 Too Many Requests` | Rate limit exceeded. |
| `500 Internal Error` | An unexpected error occurred during processing. |

## Rate Limiting Notes
The API is currently rate-limited to 10 requests per minute per IP to prevent resource exhaustion during heavy repository mining.

## CORS Configuration
Cross-Origin Resource Sharing (CORS) is enabled for all origins (`*`) by default in development mode. In production, this should be restricted to the specific frontend domain.
