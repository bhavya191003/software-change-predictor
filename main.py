import argparse
import logging
from backend.miner import mine_repository
from backend.analyzer import generate_risk_metrics, compute_composite_risk
from backend.predictor import generate_predictions
from backend.utils import setup_logger

logger = setup_logger("cli")

def main():
    parser = argparse.ArgumentParser(description="Software Change Predictor CLI")
    parser.add_argument("--repo", type=str, required=True, help="Path or URL to the git repository")
    parser.add_argument("--output", type=str, default="output.csv", help="Output CSV file path")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top risky files to display")
    
    args = parser.parse_args()
    
    logger.info(f"Starting analysis for repository: {args.repo}")
    
    # 1. Mine Repository
    file_data = mine_repository(args.repo)
    if not file_data:
        logger.warning("No relevant source files found or failed to mine.")
        return
        
    # 2. Analyze Metrics
    metrics_df = generate_risk_metrics(file_data)
    
    # 3. Compute Composite Risk
    risk_df = compute_composite_risk(metrics_df)
    
    # 4. Generate Predictions
    prediction_df = generate_predictions(risk_df)
    
    # Merge predictions
    final_df = risk_df.merge(prediction_df, on="file_path", how="left")
    
    # Save output
    final_df.to_csv(args.output, index=False)
    logger.info(f"Analysis saved to {args.output}")
    
    # Display Top N
    print(f"\n--- Top {args.top_n} Riskiest Files ---")
    top_n_df = final_df.head(args.top_n)
    for _, row in top_n_df.iterrows():
        print(f"[{row['risk_category']}] {row['file_path']} - Score: {row['risk_score']:.4f}")

if __name__ == "__main__":
    main()