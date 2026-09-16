import math
from typing import Dict, Any, List
from .utils import setup_logger

logger = setup_logger("complexity")

def estimate_cyclomatic_complexity(added_lines: int, deleted_lines: int, file_ext: str) -> float:
    """Heuristic estimation of cyclomatic complexity change based on churn."""
    base_complexity = math.log1p(added_lines) * 1.5
    return base_complexity + math.log1p(deleted_lines) * 0.5

def calculate_file_size_score(total_churn: int) -> float:
    """Normalized file size metric based on total churn."""
    return math.log10(total_churn + 1) / 5.0

def detect_co_changes(file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Finds files that frequently change together."""
    co_change_list = []
    for file, metrics in file_data.items():
        if metrics.get('co_changes'):
            sorted_co_changes = sorted(metrics['co_changes'].items(), key=lambda x: x[1], reverse=True)
            co_change_list.append({
                'file': file,
                'top_co_changes': sorted_co_changes[:3]
            })
    return co_change_list

def calculate_coupling_score(file_path: str, co_change_map: Dict[str, int]) -> float:
    """Calculates how coupled a file is to other files."""
    if not co_change_map:
        return 0.0
    total_co_change_events = sum(co_change_map.values())
    unique_coupled_files = len(co_change_map)
    return (total_co_change_events * unique_coupled_files) / 100.0

def generate_complexity_report(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generates a full complexity report."""
    logger.info("Generating complexity report...")
    report = {
        'highly_coupled_files': [],
        'estimated_complexity_hotspots': []
    }
    
    for file, metrics in file_data.items():
        coupling = calculate_coupling_score(file, metrics.get('co_changes', {}))
        est_complexity = estimate_cyclomatic_complexity(
            sum(metrics['churns']), 
            0,
            file.split('.')[-1]
        )
        
        if coupling > 1.0:
            report['highly_coupled_files'].append({'file': file, 'coupling_score': coupling})
            
        if est_complexity > 10.0:
            report['estimated_complexity_hotspots'].append({'file': file, 'complexity': est_complexity})
            
    return report
