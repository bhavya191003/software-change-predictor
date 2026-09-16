from pydantic import BaseModel, Field
from typing import List, Optional

class RepoRequest(BaseModel):
    url: str = Field(..., description="The URL or local path to the Git repository")

class FileRiskMetric(BaseModel):
    file_path: str
    commit_frequency: int
    velocity: float
    total_churn: int
    author_count: int
    entropy: float
    bug_ratio: float
    risk_score: float
    risk_category: str

class AnalysisSummary(BaseModel):
    total_files: int
    high_risk_count: int
    avg_entropy: float
    avg_risk: float
    max_risk_score: float
    total_commits_analyzed: int
    analysis_duration_seconds: float

class PredictionResult(BaseModel):
    file_path: str
    current_risk: float
    predicted_risk: float
    trend: str
    confidence: float

class AnalysisResponse(BaseModel):
    status: str
    data: List[FileRiskMetric]
    summary: AnalysisSummary
    predictions: List[PredictionResult]
