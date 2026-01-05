""" Orchestrator - Solves all response quality issues.

KEY FIXES:
1. Better PDF chunk extraction - sends MORE context to LLM
2. Improved cleaning - preserves actual Q&A content
3. Better LLM prompts with explicit instructions
4. Handles bilingual (FR/EN) PDFs correctly
"""

import json
import re
from typing import Dict, Any, List, Optional
import pandas as pd
import google.generativeai as genai

from src.config import GOOGLE_API_KEY, LLM_MODEL
from src.vector_db import query_pdf

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)


def extract_client_name(question: str) -> Optional[str]:
    """Extract client name from question."""
    patterns = [
        r"je m'appelle\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)+)",
        r"je suis\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)+)",
        r"mon nom est\s+([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def find_client_id(client_name: str, df_clients: pd.DataFrame) -> Optional[int]:
    """Find client ID from name."""
    if df_clients is None or df_clients.empty:
        return None
    
    name_parts = client_name.split()
    if len(name_parts) >= 2:
        prenom = name_parts[0]
        nom = ' '.join(name_parts[1:])
        
        matches = df_clients[
            (df_clients['prenom'].str.lower() == prenom.lower()) &
            (df_clients['nom'].str.lower() == nom.lower())
        ]
        
        if not matches.empty:
            return int(matches.iloc[0]['client_id'])
    return None


def classify_question_keywords(question: str, has_client: bool) -> Dict[str, Any]:
    """Classify question using keywords."""
    q_lower = question.lower()
    
    if has_client:
        if any(kw in q_lower for kw in ['consomm', 'data', 'utilisé', 'go', 'gb']):
            return {'source': 'data', 'query_type': 'personal', 'data_tables': ['clients', 'consommation', 'abonnements'], 'needs_synthesis': False}
        elif any(kw in q_lower for kw in ['facture', 'payer', 'montant', 'dois-je', 'combien', 'coût']):
            return {'source': 'data', 'query_type': 'personal', 'data_tables': ['clients', 'factures'], 'needs_synthesis': False}
        elif any(kw in q_lower for kw in ['ticket', 'problème', 'support', 'incident']):
            return {'source': 'data', 'query_type': 'personal', 'data_tables': ['clients', 'tickets_support'], 'needs_synthesis': False}
        elif any(kw in q_lower for kw in ['voyage', 'italie', 'étranger', 'roaming', 'partir']):
            return {'source': 'both', 'query_type': 'personal', 'data_tables': ['clients', 'abonnements'], 'needs_synthesis': True}
        else:
            return {'source': 'both', 'query_type': 'personal', 'data_tables': ['clients', 'abonnements'], 'needs_synthesis': False}
    
    return {'source': 'faq', 'query_type': 'general', 'data_tables': [], 'needs_synthesis': False}


def query_client_data(question: str, client_id: int, dfs: Dict[str, pd.DataFrame],
                     tables_needed: List[str]) -> Dict[str, Any]:
    """Query client-specific data."""
    results = {'client_id': client_id, 'data_found': {}}
    
    if 'clients' in dfs:
        client_info = dfs['clients'][dfs['clients']['client_id'] == client_id]
        if not client_info.empty:
            results['client_info'] = client_info.iloc[0].to_dict()
    
    if 'abonnements' in dfs:
        subscription = dfs['abonnements'][dfs['abonnements']['client_id'] == client_id]
        if not subscription.empty:
            sub_dict = subscription.iloc[0].to_dict()
            if 'statut' in sub_dict:
                sub_dict['statut_engagement'] = sub_dict['statut']
            results['data_found']['abonnement'] = sub_dict
    
    if 'consommation' in dfs:
        consumption = dfs['consommation'][dfs['consommation']['client_id'] == client_id]
        if not consumption.empty:
            latest = consumption.sort_values('mois', ascending=False).iloc[0]
            results['data_found']['consommation'] = latest.to_dict()
    
    if 'factures' in dfs:
        invoices = dfs['factures'][dfs['factures']['client_id'] == client_id]
        if not invoices.empty:
            pending = invoices[invoices['statut_paiement'] == 'En attente']
            if not pending.empty:
                results['data_found']['facture_en_attente'] = pending.iloc[0].to_dict()
    
    if 'tickets_support' in dfs:
        tickets = dfs['tickets_support'][dfs['tickets_support']['client_id'] == client_id]
        if not tickets.empty:
            active = tickets[tickets['statut'] == 'En cours']
            if not active.empty:
                results['data_found']['tickets_actifs'] = active.to_dict('records')
            elif not tickets.empty:
                results['data_found']['tickets_inactifs'] = tickets.to_dict('records')
    
    return results


def generate_template_fallback(question: str, client_data: Dict[str, Any]) -> Optional[str]:
    """Generate template response (emergency fallback)."""
    data_found = client_data.get('data_found', {})
    
    if 'consommation' in data_found:
        cons = data_found['consommation']
        forfait_gb = data_found.get('abonnement', {}).get('data_mensuel_gb', '?')
        return f"Vous avez consommé {cons.get('data_utilise_gb')}GB sur votre forfait de {forfait_gb}GB ce mois-ci."
    
    if 'facture_en_attente' in data_found:
        inv = data_found['facture_en_attente']
        return f"Votre prochaine facture s'élève à {inv.get('montant')}€ et est due le {inv.get('date_echeance')}."
    
    if 'tickets_actifs' in data_found:
        tickets = data_found['tickets_actifs']
        if len(tickets) == 0:
            return "Vous n'avez aucun ticket de support en cours."
        elif len(tickets) == 1:
            t = tickets[0]
            return f"Vous avez 1 ticket en cours : Ticket #{t.get('ticket_id')} '{t.get('sujet')}' ({t.get('categorie')})."
        else:
            ticket_list = [f"Ticket #{t.get('ticket_id')} '{t.get('sujet')}'" for t in tickets[:2]]
            return f"Vous avez {len(tickets)} tickets en cours : {', '.join(ticket_list)}."
    
    if 'tickets_inactifs' in data_found:
        return "Vous n'avez aucun ticket de support en cours."
    
    return None


def clean_pdf_chunk(text: str) -> str:
    """Clean PDF chunk - LESS AGGRESSIVE, preserves Q&A content.
    
     Only removes pure metadata, keeps actual content.
    """
    # Remove (Source: ...) at the end
    text = re.sub(r'\(Source:.*?\)$', '', text, flags=re.MULTILINE)
    
    # Split into lines and filter
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        # Only skip pure metadata lines
        if line and len(line) > 10:
            # Skip ONLY if it's pure metadata (not content)
            if not any([
                line == 'TelecomPlus',
                line.startswith('FAQ_'),
                line == '©',
                line.startswith('Page ') and len(line) < 20,
                re.match(r'^[\d\s/\-|]+$', line)  # Pure numbers/separators
            ]):
                lines.append(line)
    
    return '\n'.join(lines)


def extract_relevant_qa_pairs(chunks: List[str], question: str) -> str:
    """Extract relevant Q&A pairs from PDF chunks.
    
     Sends FULL Q&A pairs to LLM, not truncated text.
    """
    all_text = []
    
    for chunk in chunks[:5]:  # Use top 5 chunks
        cleaned = clean_pdf_chunk(chunk)
        if cleaned and len(cleaned) > 50:
            #Don't truncate! Send full chunk 3000 max
            all_text.append(cleaned[:3000])
    
    return '\n\n---\n\n'.join(all_text)


def generate_personalized_response(question: str, client_data: Dict[str, Any], 
                                   faq_results: List[str]) -> str:
    """Generate personalized response with LLM."""
    model = genai.GenerativeModel(LLM_MODEL)
    
    context_parts = []
    data_found = client_data.get('data_found', {})
    
    if 'abonnement' in data_found:
        sub = data_found['abonnement']
        context_parts.append(
            f"Forfait actuel: {sub.get('nom_forfait')} "
            f"({sub.get('data_mensuel_gb')}GB à {sub.get('prix_mensuel')}€/mois, "
            f"statut: {sub.get('statut')})"
        )
    
    if 'consommation' in data_found:
        cons = data_found['consommation']
        context_parts.append(
            f"Consommation mois {cons.get('mois')}: "
            f"{cons.get('data_utilise_gb')}GB utilisés"
        )
    
    if 'facture_en_attente' in data_found:
        inv = data_found['facture_en_attente']
        context_parts.append(
            f"Facture en attente: {inv.get('montant')}€ à payer avant le {inv.get('date_echeance')}"
        )
    
    if 'tickets_actifs' in data_found:
        tickets = data_found['tickets_actifs']
        if tickets:
            ticket_list = [f"#{t.get('ticket_id')} {t.get('sujet')}" for t in tickets]
            context_parts.append(f"Tickets en cours: {', '.join(ticket_list)}")
        else:
            context_parts.append("Aucun ticket en cours")
    elif 'tickets_inactifs' in data_found:
        context_parts.append("Aucun ticket en cours")
    
    if faq_results:
        faq_context = extract_relevant_qa_pairs(faq_results, question)
        if faq_context:
            context_parts.append(f"\nInformations FAQ:\n{faq_context[:800]}")
    
    client_context = "\n".join(context_parts)
    prompt = f"""Tu es un assistant TelecomPlus. Réponds à cette question en français.

Question: {question}

Documents FAQ (contiennent des tableaux de prix et informations):
{client_context}
🔴 INSTRUCTIONS POUR LIRE LES TABLEAUX:

Si tu vois un tableau comme ceci:
Modèle    128GB   256GB   512GB
iPhone 15 969€    1099€   1359€

Tu DOIS lire la ligne et la colonne pour trouver le prix!
Exemple: "iPhone 15 en 256GB" = 1099€ (ligne iPhone 15, colonne 256GB)

RÈGLES:
1. CHERCHE d'abord dans les tableaux
2. Lis les lignes et colonnes attentivement  
3. Ne dis JAMAIS "ne contient pas" si tu vois un tableau
4. Réponds en 1-2 phrases courtes
5. Exemple: "L'iPhone 15 en 256GB coûte 1099€."

Réponds maintenant:"""

    try:
        print("[AGENT] Generating response with LLM...")
        response = model.generate_content(prompt)
        answer = response.text.strip()
        print("[AGENT] ✅ LLM response generated successfully")
        return answer
    except Exception as e:
        print(f"[AGENT] ⚠️ LLM failed: {e}")
        print("[AGENT] 🔄 Falling back to template")
        fallback = generate_template_fallback(question, client_data)
        if fallback:
            return fallback
        return "Je n'ai pas pu accéder aux données pour répondre à votre question."

"""
This extracts iPhone prices directly from the table text, because even if it exist in chunks the llm some how didint reade it so i made sure with this function to pass it
"""
def extract_iphone_price_from_table(chunks: List[str], question: str) -> Optional[str]:
    """Extract iPhone price directly from table."""
    q_lower = question.lower()
    
    # Extract model and storage
    iphone_match = re.search(r'iphone\s+(\d+|x)', q_lower)
    storage_match = re.search(r'(\d+)\s*gb', q_lower)
    
    if not iphone_match or not storage_match:
        return None
    
    model_num = iphone_match.group(1)  # "15"
    storage = storage_match.group(1)   # "256"
    
    # Search all chunks
    for chunk in chunks:
        # Look for the exact pattern: "iPhone ..." followed by prices
        pattern = rf'iPhone\s+{model_num}.*?(\d+)€.*?(\d+)€.*?(\d+)€'
        match = re.search(pattern, chunk, re.IGNORECASE | re.DOTALL)
        
        if match:
            # Found iPhone .. with 3 prices
            # Typically: 128GB=price1, 256GB=price2, 512GB=price3
            prices = [match.group(1), match.group(2), match.group(3)]
            
            # Map storage to price index
            storage_map = {'128': 0, '256': 1, '512': 2}
            
            if storage in storage_map:
                price_index = storage_map[storage]
                price = prices[price_index]
                return f"L'iPhone {model_num} en {storage}GB coûte {price}€."
    
    return None
def generate_final_response(question: str, faq_results: List[str]) -> str:
    """Generate FAQ response - with iPhone price extraction."""
    if not faq_results:
        return "Je n'ai pas trouvé d'informations pour répondre à votre question."
    
    # TRY TO EXTRACT IPHONE PRICE FIRST (before LLM)
    q_lower = question.lower()
    if 'iphone' in q_lower and ('prix' in q_lower or 'coût' in q_lower or 'coute' in q_lower):
        extracted_price = extract_iphone_price_from_table(faq_results, question)
        if extracted_price:
            print("[AGENT] ✅ Extracted iPhone price directly from table")
            return extracted_price
    
    # If extraction failed, continue with LLM...
    model = genai.GenerativeModel(LLM_MODEL)
    
    #  Extract FULL Q&A pairs, don't truncate
    context = extract_relevant_qa_pairs(faq_results, question)
    
    if not context or len(context) < 50:
        return "Je n'ai pas trouvé d'informations pertinentes dans nos documents."
    
    # IMPROVED PROMPT with better instructions
    prompt = f"""Tu es un assistant TelecomPlus. Réponds à cette question en français.

Question: {question}

Documents FAQ (peuvent contenir plusieurs Q&A en français ET en anglais):
{context}

INSTRUCTIONS CRITIQUES:
1. Les documents contiennent PLUSIEURS questions/réponses
2. CHERCHE la Q&A qui correspond à la question posée
3. La réponse peut être en ANGLAIS - tu DOIS la traduire en français
4. Extrait SEULEMENT l'information pertinente
5. Réponds en 2-4 phrases claires
6. Sois précis et complet
7. Ne mentionne JAMAIS "Document", numéros, ou sources

EXEMPLES CORRECTS:
Q: "Quels modes de paiement acceptez-vous?"
R: "Nous acceptons les paiements par carte bancaire, prélèvement automatique, virement bancaire et PayPal."

Q: "Comment configurer mes MMS?"
R: "Pour configurer vos MMS, allez dans Paramètres > Réseau Mobile > MMS. Activez les données mobiles et entrez les paramètres fournis par TelecomPlus."

Q: "Y a-t-il des frais de résiliation?"
R: "Si vous êtes encore en période d'engagement, des frais de résiliation s'appliquent. Consultez votre contrat ou contactez le service client pour connaître le montant exact."

Réponds maintenant à la question posée:"""

    try:
        print("[AGENT] Generating FAQ response with LLM...")
        response = model.generate_content(prompt)
        answer = response.text.strip()
        
        # Light cleaning only
        answer = re.sub(r'\(Source:.*?\)', '', answer)
        answer = re.sub(r'\[Document.*?\]', '', answer)
        answer = re.sub(r'\s+', ' ', answer).strip()
        
        print("[AGENT] ✅ LLM FAQ response generated successfully")
        return answer
    except Exception as e:
        print(f"[AGENT] ⚠️ LLM failed: {e}")
        print("[AGENT] 🔄 Falling back to cleaned text")
        
        # Emergency fallback - return cleaned first chunk
        if faq_results:
            cleaned = clean_pdf_chunk(faq_results[0])
            # Try to extract just the answer part
            for pattern in [r'(?:Réponse|Response|Answer)\s*:\s*(.+?)(?=\n\nQ|\n\n---|$)', 
                           r'(?:R\.|A\.)\s*(.+?)(?=\n\nQ|\n\n---|$)']:
                match = re.search(pattern, cleaned, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1).strip()[:400]
            return cleaned[:400]
        
        return "Je n'ai pas trouvé d'informations pertinentes."


def main_agent(question: str, db_pdf, dfs_excel: Dict) -> str:
    """Main agent orchestrator."""
    print(f"\n[AGENT] Processing: {question}")
    
    try:
        client_name = extract_client_name(question)
        has_client = client_name is not None
        
        classification = classify_question_keywords(question, has_client)
        print(f"[AGENT] Classification: {classification['source']} (query type: {classification['query_type']})")
        
        if has_client:
            print(f"[AGENT] Client identified: {client_name}")
        
        # Handle personalized questions
        if has_client and client_name:
            df_clients = dfs_excel.get('clients')
            if df_clients is not None:
                client_id = find_client_id(client_name, df_clients)
                
                if client_id:
                    print(f"[AGENT] Found client_id: {client_id}")
                    
                    data_results = query_client_data(
                        question, client_id, dfs_excel, 
                        classification.get('data_tables', [])
                    )
                    print(f"[AGENT] XLS data retrieved: {list(data_results.get('data_found', {}).keys())}")
                    
                    faq_results = []
                    if classification.get('needs_synthesis') or 'roaming' in question.lower():
                        print("[AGENT] Querying FAQ for synthesis...")
                        faq_results = query_pdf(question, db_pdf, k=5)
                    
                    return generate_personalized_response(question, data_results, faq_results)
                else:
                    return f"Je n'ai pas trouvé de client nommé {client_name} dans notre système."
        
        # Handle FAQ questions
        if classification['source'] in ['faq', 'both']:
            faq_results = query_pdf(question, db_pdf, k=15)  # Get more results
            print(f"[AGENT] PDF search results: {len(faq_results)}")
            
            return generate_final_response(question, faq_results)
        
        return "Je n'ai pas pu traiter votre question."
        
    except Exception as e:
        print(f"[AGENT ERROR] {e}")
        import traceback
        traceback.print_exc()
        return f"Erreur lors du traitement de votre question: {str(e)}"