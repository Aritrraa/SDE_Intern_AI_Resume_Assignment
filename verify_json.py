import json
import sys

def run_checks():
    try:
        with open('./output/results.json') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("results.json not found")
        sys.exit(1)

    ranked = data.get('ranked_candidates', [])
    prev_score = 999
    
    for idx, c in enumerate(ranked):
        score = c['total_score']
        if score > prev_score:
            print(f"FAIL: Ranking failed at idx {idx}: {score} > {prev_score}")
            sys.exit(1)
        prev_score = score
        
        bd = c['score_breakdown']
        calc_score = sum([bd['ai_project_depth'], bd['python_backend'], bd['cloud_fullstack'], bd['github'], bd['engineering_depth']])
        
        # Penalties are applied during compute_total_score, which adjusts ai_project_depth directly.
        # But wait, GitHub score is capped. The sum of breakdown is exact.
        if calc_score != score:
            print(f"FAIL: Arithmetic failed for {c['candidate_name']}: {calc_score} != {score}")
            sys.exit(1)
        
        if not (0 <= bd['ai_project_depth'] <= 40):
            print("FAIL: AI out of bounds")
            sys.exit(1)
        if not (0 <= bd['python_backend'] <= 30):
            print("FAIL: Python out of bounds")
            sys.exit(1)
        if not (0 <= bd['cloud_fullstack'] <= 15):
            print("FAIL: Cloud out of bounds")
            sys.exit(1)
        if not (0 <= bd['github'] <= 10):
            print("FAIL: GitHub out of bounds")
            sys.exit(1)
        if not (0 <= bd['engineering_depth'] <= 5):
            print("FAIL: Engineering out of bounds")
            sys.exit(1)
            
    print(f"PASS: JSON arithmetic, bounds, and order verified for {len(ranked)} candidates.")
    print(f"Total: {data['batch_summary']['total_resumes']}")
    print(f"Eligible: {data['batch_summary']['eligible']}")
    print(f"Rejected: {data['batch_summary']['rejected']}")

run_checks()
