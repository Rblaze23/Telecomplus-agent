"""Vector database for PDF document search using FAISS - BILINGUAL SUPPORT."""

from typing import List
import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


def build_vector_db(chunks, persist_path="faiss_index"):
    """Build and persist a FAISS vector database from document chunks."""
    if not chunks:
        raise ValueError("No chunks provided to build vector database")
    
    print(f"[VECTOR DB] Building index with {len(chunks)} chunks...")
    
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(persist_path)
    print(f"[VECTOR DB] Index saved to {persist_path}")
    
    return db


def load_vector_db(persist_path="faiss_index"):
    """Load a previously saved FAISS vector database."""
    print(f"[VECTOR DB] Loading index from {persist_path}...")
    
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.load_local(persist_path, embeddings, allow_dangerous_deserialization=True)
    
    print("[VECTOR DB] Index loaded successfully")
    return db


def extract_answer_from_chunk(chunk: str) -> str:
    """Extract the answer portion from a FAQ chunk."""
    patterns = [
        r"Réponse\s*:\s*(.*?)(?=Q\d+\.|Questions traitées|Question suivante|Question \d+|TelecomPlus|\Z)",
        r"Response\s*:\s*(.*?)(?=Q\d+\.|Questions traitées|Question suivante|Question \d+|TelecomPlus|\Z)",
        r"Answer\s*:\s*(.*?)(?=Q\d+\.|Questions traitées|Question suivante|Question \d+|TelecomPlus|\Z)",
        r"Q\d+\..*?\?\s*\n\s*(.*?)(?=Q\d+\.|Questions traitées|Question suivante|TelecomPlus|\Z)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, chunk, re.DOTALL | re.IGNORECASE)
        if match:
            answer = match.group(1).strip()
            answer = re.sub(r'\s+', ' ', answer)
            answer = re.sub(r'^\s*[|\-•]\s*', '', answer)
            
            if (answer and len(answer) > 30 and 
                'TelecomPlus' not in answer[:50] and
                'FAQ' not in answer[:20] and
                '©' not in answer):
                return answer
    
    # Fallback extraction
    lines = chunk.split('\n')
    content_lines = []
    for line in lines:
        line = line.strip()
        if (line and len(line) > 20 and
            'TelecomPlus' not in line and
            'FAQ' not in line and
            '©' not in line and
            'Page' not in line and
            not line.startswith('Q') and
            not re.match(r'^[\d\s/\-|]+$', line)):
            content_lines.append(line)
    
    if content_lines:
        return ' '.join(content_lines[:3])
    
    return ""


def clean_and_format_answer(answer: str) -> str:
    """Clean up extracted answer text."""
    answer = re.sub(r'\s+', ' ', answer)
    answer = re.sub(r'\d+/\d+', '', answer)
    answer = re.sub(r'Page \d+', '', answer)
    answer = re.sub(r'•\s*', '- ', answer)
    answer = re.sub(r'\.{2,}', '.', answer)
    return answer.strip()


def query_pdf(question: str, db, k: int = 10) -> List[str]:
    """Search PDF documents with bilingual support for FR/EN PDFs.
    
    Args:
        question: User's question (can be French or English)
        db: FAISS vector database
        k: Number of results to return
        
    Returns:
        List of relevant answer texts with source information
    """
    # Define translations for common French queries
    fr_to_en = {
        "quels modes de paiement": "payment methods accepted",
        "modes de paiement": "payment methods",
        "moyens de paiement": "payment methods",
        "comment configurer": "how to configure setup",
        "configurer mes mms": "configure mms settings multimedia messages",
        "frais de résiliation": "cancellation fees termination early cancel",
        "résilier": "cancel terminate end",
        "roaming": "roaming international abroad",
    }
    
    question_lower = question.lower()
    
    # Determine if we need English translation
    english_query = None
    for fr_term, en_term in fr_to_en.items():
        if fr_term in question_lower:
            english_query = en_term
            print(f"[SEARCH] Bilingual mode: FR + EN ({en_term})")
            break
    
    # Perform searches
    all_docs = []
    seen = set()
    
    # Search 1: Original question
    docs_fr = db.similarity_search(question, k=k)
    
    # Search 2: English translation 
    docs_en = []
    if english_query:
        docs_en = db.similarity_search(english_query, k=k)
    
    # INTERLEAVE results - alternate between FR and EN
    # This ensures EN results appear in top 10
    max_len = max(len(docs_fr), len(docs_en))
    for i in range(max_len):
        # Add from English first (higher priority for bilingual PDFs)
        if i < len(docs_en):
            sig = docs_en[i].page_content[:100]
            if sig not in seen:
                all_docs.append(docs_en[i])
                seen.add(sig)
        
        # Then add from French
        if i < len(docs_fr):
            sig = docs_fr[i].page_content[:100]
            if sig not in seen:
                all_docs.append(docs_fr[i])
                seen.add(sig)
    
    # Take top K from interleaved results
    docs = all_docs[:k]
    
    # Extract and format answers
    answers = []
    seen_answers = set()
    
    for doc in docs:
        # DON'T extract - send the WHOLE chunk!
        # Just clean metadata
        raw_content = doc.page_content
        
        # Remove metadata lines but keep ALL Q&As
        lines = []
        for line in raw_content.split('\n'):
            line = line.strip()
            # Only skip pure metadata, keep everything else
            if (line and 
                not line.startswith('TelecomPlus') and
                'FAQ' not in line[:20] and
                '©' not in line and
                'Page' not in line[:20] and
                '|' not in line):
                lines.append(line)
        
        answer = '\n'.join(lines)
        
        if not answer or len(answer) < 30:
            continue
        
        content_sig = answer[:50].lower()
        if content_sig in seen_answers:
            continue
        
        seen_answers.add(content_sig)
        
        # Get source info
        source = doc.metadata.get('source', 'FAQ PDF')
        if '/' in source:
            source = source.split('/')[-1]
        if '\\' in source:
            source = source.split('\\')[-1]
        
        page = doc.metadata.get('page', 'n/a')
        
        formatted_answer = f"{answer}\n(Source: {source}, Page: {page})"
        answers.append(formatted_answer)
        
        if len(answers) >= 5:
            break
    
    return answers


def query_pdf_with_score(question: str, db, k: int = 10, 
                         score_threshold: float = 0.7) -> List[tuple]:
    """Search PDF documents with relevance scores."""
    docs_and_scores = db.similarity_search_with_score(question, k=k)
    
    results = []
    
    for doc, score in docs_and_scores:
        similarity = 1 / (1 + score)
        
        if similarity < score_threshold:
            continue
        
        answer = extract_answer_from_chunk(doc.page_content)
        if answer:
            answer = clean_and_format_answer(answer)
            if len(answer) >= 20:
                results.append((answer, similarity))
    
    return results