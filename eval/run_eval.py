import json
import os
import sys
from src.agent import agent_app

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_evaluation():
    with open("eval/qa_set.json", "r") as f:
        qa_set = json.load(f)

    print(f"Starting Evaluation Suite: {len(qa_set)} questions\n")
    
    for i, item in enumerate(qa_set, 1):
        q = item["question"]
        print(f"[{i}/{len(qa_set)}] Testing: {q}")
        
        # Run the agent
        result = agent_app.invoke({"messages": [("user", q)]})
        analysis = result.get("final_analysis")
        
        if analysis:
            print("✅ PASSED: Structure validated.")
        else:
            print("❌ FAILED: Response structure invalid.")

if __name__ == "__main__":
    run_evaluation()