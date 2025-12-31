"""Intelligent orchestrator using Gemini LLM for decision-making and response generation.

This module routes questions to appropriate data sources and generates natural responses.
"""

import json
import re
from typing import Dict, Any, List
import google.generativeai as genai

from src.config import GOOGLE_API_KEY, LLM_MODEL
from src.vector_db import query_pdf
from src.data_queries import query_excel_intelligent

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)


def classify_question_with_llm(question: str) -> Dict[str, Any]:
    """Use LLM to classify the question and determine which data sources to query."""
    model = genai.GenerativeModel(LLM_MODEL)

    prompt = f"""Tu es un assistant de classification pour TelecomPlus.
Analyse cette question et détermine quelle source de données utiliser.

Question: {question}

RÈGLES IMPORTANTES:
- FAQ: Questions générales (comment, pourquoi, quels types, quelles options, procédures, politiques)
- DATA: SEULEMENT si la question demande des informations sur UN CLIENT SPÉCIFIQUE ou des statistiques

Exemples:
- "Quels forfaits proposez-vous?" → FAQ
- "Comment éviter les frais?" → FAQ
- "Ma facture du mois dernier?" → DATA
- "Combien de clients avez-vous?" → DATA

Réponds UNIQUEMENT avec un JSON (pas de markdown):
{{"source": "faq", "reasoning": "explication", "data_tables": []}}"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean markdown
        if "```" in response_text:
            response_text = response_text.split(
                "```")[1] if response_text.count("```") >= 2 else response_text
            response_text = response_text.replace("json", "").strip()

        classification = json.loads(response_text)
        return classification
    except Exception as e:
        print(f"[ERROR] Classification failed: {e}")
        return fallback_classification(question)


def fallback_classification(question: str) -> Dict[str, Any]:
    """Fallback classification if LLM fails."""
    personal_keywords = ["mon", "ma", "mes"]
    general_keywords = ["quels", "comment", "pourquoi", "types de"]

    q_lower = question.lower()

    if "combien de clients" in q_lower or "nombre de" in q_lower:
        return {"source": "data", "reasoning": "Statistiques", "data_tables": ["clients"]}

    if any(kw in q_lower for kw in personal_keywords):
        return {"source": "data", "reasoning": "Question personnelle", "data_tables": []}

    return {"source": "faq", "reasoning": "Question générale", "data_tables": []}


def generate_final_response(question: str, faq_results: List[str], data_results: Any) -> str:
    """Generate natural response using Gemini."""

    # If no results at all
    if not faq_results and not data_results:
        return "Je n'ai pas trouvé d'informations pour répondre à votre question. Pouvez-vous reformuler?"

    model = genai.GenerativeModel(LLM_MODEL)

    # Prepare context - ONLY the actual answers, no metadata
    context_parts = []

    if faq_results:
        # Don't extract - send FULL chunks to LLM!
        # Just remove metadata markers
        cleaned_faqs = []
        for i, faq in enumerate(faq_results, 1):
            # Remove source info
            clean = faq.split("(Source:")[0].strip()
            # Remove headers/footers but keep all Q&As
            lines = []
            for line in clean.split('\n'):
                line_clean = line.strip()
                # Skip pure metadata lines
                if (line_clean and
                    'TelecomPlus' not in line_clean and
                    'FAQ' not in line_clean and
                    '©' not in line_clean and
                    'Page' not in line_clean[:20] and
                        '|' not in line_clean):
                    lines.append(line_clean)

            if lines:
                clean_chunk = '\n'.join(lines)
                if len(clean_chunk) > 50:
                    cleaned_faqs.append(f"[Document {i}]:\n{clean_chunk}")

        if cleaned_faqs:
            context_parts.append("Documents trouvés:\n\n" +
                                 "\n\n".join(cleaned_faqs))

    if data_results and isinstance(data_results, dict) and "data" in data_results:
        context_parts.append(f"Données: {data_results['data'][:3]}")

    context = "\n\n".join(context_parts)

    if not context.strip():
        return "Je n'ai pas trouvé d'informations pertinentes."

    # Generate response with VERY explicit instructions
    prompt = f"""Tu es un assistant TelecomPlus. Réponds à cette question en français.

Question: {question}

{context}

INSTRUCTIONS CRITIQUES:
1. Les documents ci-dessus contiennent PLUSIEURS questions/réponses (Q1, Q2, Q3...)
2. CHERCHE la Q/R qui correspond EXACTEMENT à la question posée
3. Si tu vois "Q9. What payment methods" et la question demande "modes de paiement", c'est la bonne!
4. IGNORE les autres Q/R qui ne correspondent pas
5. Extrait SEULEMENT la réponse pertinente
6. Traduis en français si nécessaire
7. Sois précis et complet (2-4 phrases)
8. Ne mentionne JAMAIS "Document", "Q9", numéros de questions

EXEMPLE:
Question: "Quels modes de paiement acceptez-vous?"
Dans le document tu vois:
  Q8. billing statements → IGNORE
  Q9. What payment methods are accepted? → C'EST CELLE-CI!
  Q10. automatic payments → IGNORE
Réponse: "Nous acceptons carte bancaire, virements en ligne et prélèvements."

Réponds maintenant:"""

    try:
        response = model.generate_content(prompt)
        answer = response.text.strip()

        # AGGRESSIVE cleanup - remove ANY remaining metadata
        answer = re.sub(r'\(Source:.*?\)', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'\(.*?\.pdf.*?\)', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'Source:.*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'Page:.*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'FAQ_\w+\.pdf', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'TelecomPlus.*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'©.*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'\|\s*\|', '', answer)
        answer = re.sub(r'\s+', ' ', answer).strip()

        # If still has metadata, use only first sentence
        if any(word in answer.lower() for word in ['source', 'page', 'telecomplus', 'pdf']):
            sentences = answer.split('.')
            answer = sentences[0] + '.' if sentences else answer

        return answer if answer else "Je n'ai pas pu générer une réponse appropriée."

    except Exception as e:
        print(f"[ERROR] Response generation failed: {e}")
        # Fallback: return first cleaned FAQ
        if faq_results:
            first = faq_results[0].split("(Source:")[0].strip()
            return first[:300]
        return "Erreur lors de la génération de la réponse."


def main_agent(question: str, db_pdf, dfs_excel: Dict) -> str:
    """Main agent orchestrator."""

    print(f"\n[AGENT] Processing: {question}")

    try:
        # Step 1: Classify
        classification = classify_question_with_llm(question)
        print(f"[AGENT] Classification: {classification['source']}")

        faq_results = []
        data_results = None

        # Step 2: Query sources
        if classification["source"] in ["faq", "both"]:
            faq_results = query_pdf(question, db_pdf, k=10)  # Get 10 results
            print(f"[AGENT] FAQ results: {len(faq_results)}")

            if faq_results:
                # Show ALL results found
                for i, res in enumerate(faq_results[:3], 1):
                    preview = res[:80].replace('\n', ' ')
                    print(f"[AGENT] Result {i}: {preview}...")

        if classification["source"] in ["data", "both"]:
            tables = classification.get("data_tables", [])
            data_results = query_excel_intelligent(question, dfs_excel, tables)
            print(f"[AGENT] Data results: {type(data_results)}")

        # Step 3: Generate natural response
        print("[AGENT] Generating response with LLM...")
        final_response = generate_final_response(
            question, faq_results, data_results)

        print(f"[AGENT] Response length: {len(final_response)} chars")
        print(f"[AGENT] Response preview: {final_response[:80]}...")

        # CRITICAL CHECK: If response still has metadata, it means LLM failed
        if any(marker in final_response for marker in ["(Source:", "FAQ_", "TelecomPlus", "Page:"]):
            print("[WARNING] Response still contains metadata! Using fallback...")
            # Emergency fallback: just return a generic message
            return "Je peux vous aider avec votre question. Pour des informations détaillées, veuillez consulter notre FAQ ou contacter le service client."

        return final_response

    except Exception as e:
        print(f"[AGENT ERROR] {e}")
        import traceback
        traceback.print_exc()
        return f"Erreur: {str(e)}"