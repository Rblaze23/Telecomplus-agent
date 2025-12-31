"""Batch evaluation to avoid rate limits.

Run this multiple times to evaluate all questions in batches of 5.
Example: python evaluate_batch.py 1
"""

import json
from datetime import datetime
import time
import sys
import pandas as pd
import google.generativeai as genai

from src.config import GOOGLE_API_KEY, LLM_MODEL
from src.main import answer

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)


def evaluate_response_with_llm(question: str, expected_answer: str, 
                                agent_answer: str) -> dict:
    """Evaluate with LLM - same as evaluate.py"""
    model = genai.GenerativeModel(LLM_MODEL)
    
    prompt = f"""Tu es un évaluateur expert pour un système de support client téléphonique.
Évalue la réponse de l'agent par rapport à la réponse attendue.

Question du client: {question}
Réponse attendue: {expected_answer}
Réponse de l'agent: {agent_answer}

Évalue selon ces critères:
1. EXACTITUDE FACTUELLE (0-4 points)
2. COMPLÉTUDE (0-3 points)
3. PERTINENCE (0-3 points)

Réponds UNIQUEMENT avec un JSON (pas de markdown):
{{"factual_accuracy": 0-4, "completeness": 0-3, "relevance": 0-3, "total_score": 0-10, "explanation": "...", "main_issues": []}}"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean markdown
        if "```" in response_text:
            response_text = response_text.split("```")[1] if response_text.count("```") >= 2 else response_text
            response_text = response_text.replace("json", "").strip()
        
        response_text = response_text.replace("```", "").strip()
        evaluation = json.loads(response_text)
        
        # Validate scores
        evaluation["factual_accuracy"] = max(0, min(4, evaluation.get("factual_accuracy", 0)))
        evaluation["completeness"] = max(0, min(3, evaluation.get("completeness", 0)))
        evaluation["relevance"] = max(0, min(3, evaluation.get("relevance", 0)))
        evaluation["total_score"] = (
            evaluation["factual_accuracy"] + 
            evaluation["completeness"] + 
            evaluation["relevance"]
        )
        
        return evaluation
    except Exception as e:
        print(f"[ERROR] Evaluation failed: {e}")
        return {
            "factual_accuracy": 0,
            "completeness": 0,
            "relevance": 0,
            "total_score": 0,
            "explanation": "Erreur d'évaluation",
            "main_issues": [str(e)]
        }


def run_batch_evaluation(batch_num: int = 1, batch_size: int = 5):
    """Evaluate one batch of questions."""
    
    print("=" * 80)
    print(f"BATCH {batch_num} EVALUATION")
    print("=" * 80)
    
    # Load questions
    df = pd.read_excel("data/evaluation_questions.xlsx")
    
    # Calculate batch range
    start_idx = (batch_num - 1) * batch_size
    end_idx = min(start_idx + batch_size, len(df))
    
    if start_idx >= len(df):
        print("All questions already evaluated!")
        return
    
    print(f"Evaluating questions {start_idx + 1} to {end_idx} of {len(df)}\n")
    
    results = []
    
    for idx in range(start_idx, end_idx):
        row = df.iloc[idx]
        question = row["Question"]
        expected_answer = row["Réponse Attendue"]
        difficulty = row.get("Difficulté", "Unknown")
        
        print(f"\n[{idx + 1}/{len(df)}] {difficulty}")
        print(f"Q: {question}")
        
        # Get answer
        try:
            agent_answer = answer(question)
            print(f"A: {agent_answer[:150]}...")
        except Exception as e:
            agent_answer = f"ERROR: {str(e)}"
            print(f"A: {agent_answer}")
        
        # Wait to avoid rate limit
        print("Waiting 15 seconds...")
        time.sleep(15)
        
        # Evaluate
        print("Evaluating...")
        evaluation = evaluate_response_with_llm(question, expected_answer, agent_answer)
        
        print(f"Score: {evaluation['total_score']}/10")
        
        results.append({
            "question_id": idx + 1,
            "question": question,
            "expected_answer": expected_answer,
            "agent_answer": agent_answer,
            "difficulty": difficulty,
            "total_score": evaluation["total_score"],
            "factual_accuracy": evaluation["factual_accuracy"],
            "completeness": evaluation["completeness"],
            "relevance": evaluation["relevance"],
            "explanation": evaluation["explanation"],
            "main_issues": ", ".join(evaluation.get("main_issues", []))
        })
        
        print("-" * 80)
    
    # Save batch results
    batch_file = f"evaluation_batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    results_df = pd.DataFrame(results)
    results_df.to_excel(batch_file, index=False)
    print(f"\n✓ Batch saved to: {batch_file}")
    
    # Show batch stats
    avg_score = results_df["total_score"].mean()
    print(f"\nBatch {batch_num} Average Score: {avg_score:.2f}/10")
    print(f"Next batch: python evaluate_batch.py {batch_num + 1}")


if __name__ == "__main__":
    # Get batch number from command line or default to 1
    batch_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    run_batch_evaluation(batch_num=batch_num, batch_size=5)
    
    print("\n" + "=" * 80)
    print("TO CONTINUE:")
    print(f"python evaluate_batch.py {batch_num + 1}")
    print("=" * 80)