from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import time
import io
import os
import pandas as pd
from typing import List
from pathlib import Path

from .models import RepoRequest, AnalysisResponse, FileRiskMetric, AnalysisSummary, PredictionResult
from .miner import mine_repository
from .analyzer import generate_risk_metrics, compute_composite_risk
from .predictor import generate_predictions
from .utils import setup_logger, validate_github_url

logger = setup_logger("api")

# Resolve the frontend directory path
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="Software Change Predictor API",
    description="API for mining git repositories and predicting defect-prone files using ML.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main frontend dashboard at the root URL."""
    index_path = _frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return JSONResponse({"error": "Frontend not found"}, status_code=404)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Path: {request.url.path} - Method: {request.method} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/api/info")
def get_info():
    """Returns API version and capabilities."""
    return {
        "version": "1.0.0",
        "name": "Software Change Predictor",
        "capabilities": ["mining", "risk_analysis", "ml_prediction", "complexity_analysis"],
        "supported_extensions": [".py", ".cpp", ".h", ".java", ".js", ".ts", ".go", ".rs"]
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_repo(req: RepoRequest):
    """Analyze a Git repository for defect risk."""
    if not validate_github_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid repository URL or path")
        
    start_time = time.time()
    try:
        # 1. Mine
        logger.info(f"Starting analysis for: {req.url}")
        file_data = mine_repository(req.url)
        if not file_data:
            raise HTTPException(status_code=404, detail="No source files found or failed to clone.")
            
        # 2. Analyze
        metrics_df = generate_risk_metrics(file_data)
        risk_df = compute_composite_risk(metrics_df)
        
        # 3. Predict
        predictions_df = generate_predictions(risk_df)
        
        # Merge results
        final_df = risk_df.merge(predictions_df, on="file_path", how="left")
        final_df.fillna({'predicted_risk': 0.0, 'trend': 'Stable', 'confidence': 0.0}, inplace=True)
        
        # Prepare response data
        data_list = []
        pred_list = []
        
        for _, row in final_df.iterrows():
            data_list.append(FileRiskMetric(
                file_path=row['file_path'],
                commit_frequency=row['commit_frequency'],
                velocity=row['velocity'],
                total_churn=row['total_churn'],
                author_count=row['author_count'],
                entropy=row['entropy'],
                bug_ratio=row['bug_ratio'],
                risk_score=row['risk_score'],
                risk_category=row['risk_category']
            ))
            
            pred_list.append(PredictionResult(
                file_path=row['file_path'],
                current_risk=row['risk_score'],
                predicted_risk=row['predicted_risk'],
                trend=row['trend'],
                confidence=row['confidence']
            ))
            
        # Summary
        duration = time.time() - start_time
        summary = AnalysisSummary(
            total_files=len(final_df),
            high_risk_count=len(final_df[final_df['risk_category'].isin(['High', 'Critical'])]),
            avg_entropy=float(final_df['entropy'].mean()),
            avg_risk=float(final_df['risk_score'].mean()),
            max_risk_score=float(final_df['risk_score'].max()),
            total_commits_analyzed=sum(len(v['commits']) for v in file_data.values()),
            analysis_duration_seconds=round(duration, 2)
        )
        
        logger.info(f"Analysis complete in {duration:.2f}s — {len(final_df)} files analyzed")
        
        return AnalysisResponse(
            status="success",
            data=data_list,
            summary=summary,
            predictions=pred_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/export/csv")
async def export_csv(req: RepoRequest):
    """Export analysis results as a downloadable CSV file."""
    if not validate_github_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid repository URL")
    
    try:
        file_data = mine_repository(req.url)
        if not file_data:
            raise HTTPException(status_code=404, detail="No source files found.")
        
        metrics_df = generate_risk_metrics(file_data)
        risk_df = compute_composite_risk(metrics_df)
        
        # Select columns for export
        export_cols = ['file_path', 'commit_frequency', 'velocity', 'total_churn', 
                       'author_count', 'entropy', 'bug_ratio', 'risk_score', 'risk_category']
        export_df = risk_df[[c for c in export_cols if c in risk_df.columns]]
        
        # Stream CSV response
        stream = io.StringIO()
        export_df.to_csv(stream, index=False)
        stream.seek(0)
        
        repo_name = req.url.rstrip('/').split('/')[-1].replace('.git', '')
        
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={repo_name}_risk_report.csv"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# Mount frontend static assets LAST (catch-all mount must be after all
# API routes, otherwise it would intercept API requests)
# ──────────────────────────────────────────────────────────────────────
if _frontend_dir.exists():
    app.mount("/css", StaticFiles(directory=str(_frontend_dir / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(_frontend_dir / "js")), name="js")
