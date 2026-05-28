from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from miner import mine_repository
from analyzer import generate_risk_metrics, compute_composite_risk
import urllib.parse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    url: str

@app.post("/analyze")
def analyze_repo(request: RepoRequest):
    raw_data = mine_repository(request.url)
    metrics_df = generate_risk_metrics(raw_data)
    final_risk_df = compute_composite_risk(metrics_df)
    
    # --- NEW: Extract the repo name and save a CSV file locally ---
    repo_name = request.url.split('/')[-1].replace('.git', '')
    csv_filename = f"{repo_name}_risk_report.csv"
    final_risk_df.to_csv(csv_filename, index=False)
    print(f"✅ Successfully saved dataset to {csv_filename}")
    # --------------------------------------------------------------
    
    result_json = final_risk_df.to_dict(orient="records")
    return {"status": "success", "data": result_json}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)