"""Batch evaluation script - splits questions into 2 batches to avoid API quota.

USAGE:
  python evaluate_batch.py --batch 1  # Run first 12 questions (today)
  python evaluate_batch.py --batch 2  # Run last 13 questions (tomorrow)
  python evaluate_batch.py --merge    # Combine results from both batches

This prevents hitting API quota limits (20 Gemini calls/day, 100K Groq tokens/day).
"""

import json
import argparse
from datetime import datetime
import time
import pandas as pd
from groq import Groq

from src.config import GOOGLE_API_KEY
from src.main import answer

# Configure Groq for evaluation
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found. Add to .env file")

groq_client = Groq(api_key=GROQ_API_KEY)


def evaluate_response_with_groq(question: str, expected_answer: str, 
                                 agent_answer: str) -> dict:
    """Evaluate agent response using Groq as judge."""
    
    prompt = f"""Tu es un évaluateur expert pour un système de support client téléphonique.
Évalue la réponse de l'agent par rapport à la réponse attendue.

Question du client:
{question}

Réponse attendue:
{expected_answer}

Réponse de l'agent:
{agent_answer}

Évalue selon ces critères:

1. EXACTITUDE FACTUELLE (0-4 points):
   - 4: Toutes les informations sont correctes et précises
   - 3: Informations majoritairement correctes avec erreurs mineures
   - 2: Quelques informations correctes mais erreurs significatives
   - 1: La plupart des informations sont incorrectes
   - 0: Complètement faux ou hors sujet

2. COMPLÉTUDE (0-3 points):
   - 3: Répond complètement à tous les aspects de la question
   - 2: Répond aux aspects principaux mais manque des détails
   - 1: Répond partiellement, manque des éléments importants
   - 0: Ne répond pas vraiment à la question

3. PERTINENCE (0-3 points):
   - 3: Directement pertinent, sans informations superflues
   - 2: Pertinent mais contient des éléments non nécessaires
   - 1: Partiellement pertinent avec beaucoup d'informations inutiles
   - 0: Hors sujet

Réponds UNIQUEMENT avec un JSON (pas de markdown):
{{
    "factual_accuracy": <score 0-4>,
    "completeness": <score 0-3>,
    "relevance": <score 0-3>,
    "total_score": <somme des 3 scores, sur 10>,
    "explanation": "Explication courte (2-3 phrases)",
    "main_issues": ["problème 1", "problème 2"] ou []
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean markdown
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        
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
        print(f"[ERROR] Groq evaluation failed: {e}")
        return fallback_evaluation(expected_answer, agent_answer)


def fallback_evaluation(expected_answer: str, agent_answer: str) -> dict:
    """Fallback evaluation if Groq fails."""
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
        "explanation": f"Évaluation automatique de secours (overlap: {overlap:.2%})",
        "main_issues": ["Évaluation Groq a échoué, score basique utilisé"]
    }


def run_batch_evaluation(batch_num: int):
    """Run evaluation for specified batch.
    
    Args:
        batch_num: 1 for first 12 questions, 2 for last 13 questions
    """
    
    print("=" * 80)
    print(f"TELECOMPLUS AGENT EVALUATION - BATCH {batch_num}")
    print("Agent: Gemini | Judge: Groq")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load all questions
    try:
        df = pd.read_excel("data/evaluation_questions.xlsx")
    except FileNotFoundError:
        print("ERROR: data/evaluation_questions.xlsx not found!")
        return
    
    # Split into batches
    if batch_num == 1:
        batch_df = df.iloc[0:12]  # First 12 questions
        batch_label = "1-12"
    elif batch_num == 2:
        batch_df = df.iloc[12:25]  # Last 13 questions
        batch_label = "13-25"
    else:
        print("ERROR: batch_num must be 1 or 2")
        return
    
    print(f"Batch {batch_num}: Questions {batch_label}")
    print(f"Total questions in batch: {len(batch_df)}\n")
    print("=" * 80)
    
    results = []
    
    # Evaluate each question in batch
    for idx, row in batch_df.iterrows():
        question = row["Question"]
        expected_answer = row["Réponse Attendue"]
        difficulty = row.get("Difficulté", "Unknown")
        
        print(f"\n[{idx + 1}/{len(df)}] Batch {batch_num} - Difficulty: {difficulty}")
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
        print("Evaluating with Groq judge...")
        evaluation = evaluate_response_with_groq(question, expected_answer, agent_answer)
        
        # CRITICAL: Wait 15 seconds to avoid 5 requests/minute limit
        if idx < batch_df.index[-1]:  # Don't wait after last question
            print(f"⏳ Waiting 15 seconds to avoid rate limit (5 req/min)...")
            time.sleep(15)
        
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
        
        print("-" * 80)
    
    # Save batch results
    results_df = pd.DataFrame(results)
    output_file = f"evaluation_batch{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    results_df.to_excel(output_file, index=False)
    
    # Calculate batch statistics
    mean_score = results_df["total_score"].mean()
    pass_rate = (results_df["total_score"] >= 6).sum() / len(results_df) * 100
    
    print("\n" + "=" * 80)
    print(f"BATCH {batch_num} RESULTS")
    print("=" * 80)
    print(f"Questions evaluated: {len(results_df)}")
    print(f"Mean score: {mean_score:.2f}/10")
    print(f"Pass rate (≥6/10): {pass_rate:.1f}%")
    print(f"\n✓ Batch results saved to: {output_file}")
    print("=" * 80)
    
    return output_file


def merge_batches():
    """Merge results from both batches into final report."""
    
    print("\n" + "=" * 80)
    print("MERGING BATCH RESULTS")
    print("=" * 80)
    
    # Find most recent batch files
    import glob
    batch1_files = sorted(glob.glob("evaluation_batch1_*.xlsx"))
    batch2_files = sorted(glob.glob("evaluation_batch2_*.xlsx"))
    
    if not batch1_files or not batch2_files:
        print("ERROR: Missing batch files!")
        print(f"Batch 1 files found: {len(batch1_files)}")
        print(f"Batch 2 files found: {len(batch2_files)}")
        return
    
    # Load most recent of each
    df1 = pd.read_excel(batch1_files[-1])
    df2 = pd.read_excel(batch2_files[-1])
    
    print(f"✓ Loaded {batch1_files[-1]}")
    print(f"✓ Loaded {batch2_files[-1]}")
    
    # Combine
    combined_df = pd.concat([df1, df2], ignore_index=True)
    
    # Calculate final statistics
    stats = {
        "total_questions": len(combined_df),
        "mean_score": float(combined_df["total_score"].mean()),
        "median_score": float(combined_df["total_score"].median()),
        "std_score": float(combined_df["total_score"].std()),
        "min_score": int(combined_df["total_score"].min()),
        "max_score": int(combined_df["total_score"].max()),
        "mean_factual_accuracy": float(combined_df["factual_accuracy"].mean()),
        "mean_completeness": float(combined_df["completeness"].mean()),
        "mean_relevance": float(combined_df["relevance"].mean()),
        "pass_rate": float((combined_df["total_score"] >= 6).sum() / len(combined_df) * 100),
    }
    
    # Save combined results
    output_file = f"evaluation_FINAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    combined_df.to_excel(output_file, index=False)
    
    stats_file = f"evaluation_FINAL_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # Print final results
    print("\n" + "=" * 80)
    print("FINAL EVALUATION RESULTS (BOTH BATCHES)")
    print("=" * 80)
    print(f"\nTotal questions evaluated: {stats['total_questions']}")
    print(f"\nScore Statistics (out of 10):")
    print(f"  Mean:   {stats['mean_score']:.2f}")
    print(f"  Median: {stats['median_score']:.2f}")
    print(f"  Std:    {stats['std_score']:.2f}")
    print(f"  Min:    {stats['min_score']:.0f}")
    print(f"  Max:    {stats['max_score']:.0f}")
    
    print(f"\nComponent Scores (averages):")
    print(f"  Factual Accuracy: {stats['mean_factual_accuracy']:.2f}/4")
    print(f"  Completeness:     {stats['mean_completeness']:.2f}/3")
    print(f"  Relevance:        {stats['mean_relevance']:.2f}/3")
    
    print(f"\nPass Rate (≥6/10): {stats['pass_rate']:.1f}%")
    
    print(f"\n✓ Combined results saved to: {output_file}")
    print(f"✓ Final statistics saved to: {stats_file}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Run batch evaluation')
    parser.add_argument('--batch', type=int, choices=[1, 2], 
                       help='Batch number (1 or 2)')
    parser.add_argument('--merge', action='store_true',
                       help='Merge results from both batches')
    
    args = parser.parse_args()
    
    if args.merge:
        merge_batches()
    elif args.batch:
        run_batch_evaluation(args.batch)
    else:
        print("Usage:")
        print("  python evaluate_batch.py --batch 1  # Run batch 1 (questions 1-12)")
        print("  python evaluate_batch.py --batch 2  # Run batch 2 (questions 13-25)")
        print("  python evaluate_batch.py --merge    # Combine both batches")


if __name__ == "__main__":
    main()