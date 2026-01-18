"""Rate-limit-safe evaluation.

I FIX THE PROBLEMs ;) :
- Gemini free tier: 5 requests per MINUTE (not 20 per day!)
- Solution: Wait 15 seconds between questions (4 per minute = safe)
- This means 25 questions × 15s = 6-7 minutes total
"""

import json
import argparse
from datetime import datetime
import time
import pandas as pd
from groq import Groq

from src.config import GOOGLE_API_KEY
from src.main import answer

# Configure Groq
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found")

groq_client = Groq(api_key=GROQ_API_KEY)

# CRITICAL: Wait time between questions to avoid rate limit
WAIT_SECONDS = 15  # 15 seconds = 4 requests/minute (safe under 5/min limit)


def evaluate_response_with_groq(question: str, expected_answer: str, 
                                 agent_answer: str) -> dict:
    """Evaluate with Groq."""
    
    prompt = f"""Tu es un évaluateur expert pour un système de support client.
Évalue la réponse de l'agent par rapport à la réponse attendue.

Question: {question}
Réponse attendue: {expected_answer}
Réponse de l'agent: {agent_answer}

Évalue selon:
1. EXACTITUDE FACTUELLE (0-4 points)
2. COMPLÉTUDE (0-3 points)
3. PERTINENCE (0-3 points)

Réponds en JSON (pas de markdown):
{{
    "factual_accuracy": <0-4>,
    "completeness": <0-3>,
    "relevance": <0-3>,
    "total_score": <0-10>,
    "explanation": "...",
    "main_issues": [...]
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        
        response_text = response_text.replace("```", "").strip()
        evaluation = json.loads(response_text)
        
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
        print(f"[ERROR] Groq failed: {e}")
        return fallback_evaluation(expected_answer, agent_answer)


def fallback_evaluation(expected_answer: str, agent_answer: str) -> dict:
    """Fallback evaluation."""
    import re
    
    expected_lower = expected_answer.lower()
    agent_lower = agent_answer.lower()
    
    expected_words = set(re.findall(r'\b\w{4,}\b', expected_lower))
    agent_words = set(re.findall(r'\b\w{4,}\b', agent_lower))
    
    if len(expected_words) == 0:
        overlap = 0.5
    else:
        overlap = len(expected_words & agent_words) / len(expected_words)
    
    score = int(overlap * 10)
    
    return {
        "factual_accuracy": int(overlap * 4),
        "completeness": int(overlap * 3),
        "relevance": int(overlap * 3),
        "total_score": score,
        "explanation": f"Évaluation de secours (overlap: {overlap:.2%})",
        "main_issues": ["Évaluation Groq a échoué"]
    }


def run_full_evaluation():
    """Run full evaluation with proper rate limiting."""
    
    print("=" * 80)
    print("TELECOMPLUS AGENT EVALUATION (Rate-Limit Safe)")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Wait time between questions: {WAIT_SECONDS} seconds")
    print(f"Estimated total time: {25 * WAIT_SECONDS / 60:.1f} minutes\n")
    
    # Load questions
    try:
        df = pd.read_excel("data/evaluation_questions.xlsx")
    except FileNotFoundError:
        print("ERROR: data/evaluation_questions.xlsx not found!")
        return
    
    print(f"Loaded {len(df)} questions\n")
    print("=" * 80)
    
    results = []
    
    # Evaluate each question with wait time
    for idx, row in df.iterrows():
        question = row["Question"]
        expected_answer = row["Réponse Attendue"]
        difficulty = row.get("Difficulté", "Unknown")
        
        print(f"\n[{idx + 1}/{len(df)}] Difficulty: {difficulty}")
        print(f"Q: {question}")
        
        # Get agent's answer
        try:
            agent_answer = answer(question)
            display_answer = agent_answer[:200] + "..." if len(agent_answer) > 200 else agent_answer
            print(f"A: {display_answer}")
        except Exception as e:
            agent_answer = f"ERROR: {str(e)}"
            print(f"A: {agent_answer}")
        
        # Evaluate with Groq
        print("Evaluating with Groq...")
        evaluation = evaluate_response_with_groq(question, expected_answer, agent_answer)
        
        print(f"Score: {evaluation['total_score']}/10 "
              f"(Accuracy: {evaluation['factual_accuracy']}/4, "
              f"Completeness: {evaluation['completeness']}/3, "
              f"Relevance: {evaluation['relevance']}/3)")
        
        if evaluation.get("explanation"):
            print(f"Explanation: {evaluation['explanation']}")
        
        # Store results
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
        
        # CRITICAL: Wait before next question to avoid rate limit
        if idx < len(df) - 1:  # Don't wait after last question
            print(f"⏳ Waiting {WAIT_SECONDS} seconds to avoid rate limit...")
            time.sleep(WAIT_SECONDS)
        
        print("-" * 80)
    
    # Calculate statistics
    results_df = pd.DataFrame(results)
    
    stats = {
        "total_questions": len(results_df),
        "mean_score": float(results_df["total_score"].mean()),
        "median_score": float(results_df["total_score"].median()),
        "std_score": float(results_df["total_score"].std()),
        "min_score": int(results_df["total_score"].min()),
        "max_score": int(results_df["total_score"].max()),
        "mean_factual_accuracy": float(results_df["factual_accuracy"].mean()),
        "mean_completeness": float(results_df["completeness"].mean()),
        "mean_relevance": float(results_df["relevance"].mean()),
        "pass_rate": float((results_df["total_score"] >= 6).sum() / len(results_df) * 100),
    }
    
    # Save results
    output_file = f"evaluation_FINAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    results_df.to_excel(output_file, index=False)
    
    stats_file = f"evaluation_FINAL_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # Print results
    print("\n" + "=" * 80)
    print("FINAL EVALUATION RESULTS")
    print("=" * 80)
    print(f"\nTotal questions: {stats['total_questions']}")
    print(f"\nScore Statistics (out of 10):")
    print(f"  Mean:   {stats['mean_score']:.2f}")
    print(f"  Median: {stats['median_score']:.2f}")
    print(f"  Std:    {stats['std_score']:.2f}")
    print(f"  Min:    {stats['min_score']:.0f}")
    print(f"  Max:    {stats['max_score']:.0f}")
    
    print(f"\nComponent Scores:")
    print(f"  Factual Accuracy: {stats['mean_factual_accuracy']:.2f}/4")
    print(f"  Completeness:     {stats['mean_completeness']:.2f}/3")
    print(f"  Relevance:        {stats['mean_relevance']:.2f}/3")
    
    print(f"\nPass Rate (≥6/10): {stats['pass_rate']:.1f}%")
    
    print(f"\n✓ Results saved to: {output_file}")
    print(f"✓ Statistics saved to: {stats_file}")
    print("=" * 80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    run_full_evaluation()
