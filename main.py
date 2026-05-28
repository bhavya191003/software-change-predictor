from miner import mine_repository
from analyzer import generate_risk_metrics, compute_composite_risk

if __name__ == "__main__":
    # Target repository for testing
    TARGET_REPO = "https://github.com/pallets/flask.git"
    
    print("\n[1/3] Mining repository history...")
    raw_data = mine_repository(TARGET_REPO)
    
    print("\n[2/3] Computing statistical metrics (Entropy, Churn)...")
    metrics_df = generate_risk_metrics(raw_data)
    
    print("[3/3] Calculating composite risk scores...")
    final_risk_df = compute_composite_risk(metrics_df)
    
    print("\n=======================================================")
    print(" 🚨 TOP 5 HIGHEST RISK FILES (PARETO HOTSPOTS) 🚨")
    print("=======================================================\n")
    
    # Print the top 5 highest risk files with their specific stats
    columns_to_show = ['file_path', 'entropy', 'commit_frequency', 'bug_ratio', 'risk_score']
    print(final_risk_df[columns_to_show].head(5).to_string(index=False))
    print("\n")