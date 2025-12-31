# 📱 TelecomPlus - Système de Support Client Intelligent

## 📋 Description du Projet

Système agentique multi-source pour le support client de TelecomPlus. Le système combine:
- **Recherche sémantique (RAG)** dans les documents FAQ (PDFs)
- **Requêtes intelligentes** sur les données clients (Excel)
- **LLM orchestration** avec Google Gemini pour décisions et génération de réponses
- **Monitoring complet** des performances et traçabilité

---

## 🏗️ Architecture du Système

```
┌─────────────────────────────────────────────────────────────┐
│                    UTILISATEUR                               │
│                  (Question en français)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR (orchestrator.py)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Classification avec LLM (Gemini)                 │   │
│  │     → Détermine: FAQ, DATA, ou BOTH                  │   │
│  │     → Identifie les tables pertinentes               │   │
│  └──────────────────────────────────────────────────────┘   │
│                       │                                      │
│       ┌───────────────┴───────────────┐                     │
│       ▼                               ▼                     │
│  ┌─────────┐                    ┌──────────┐               │
│  │  FAQ    │                    │  DATA    │               │
│  │ (PDFs)  │                    │ (Excel)  │               │
│  └─────────┘                    └──────────┘               │
│       │                               │                     │
│       ▼                               ▼                     │
│  vector_db.py                   data_queries.py             │
│  - FAISS search                 - LLM query generation      │
│  - Extraction                   - Pandas operations         │
│       │                               │                     │
│       └───────────────┬───────────────┘                     │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Génération de réponse finale (LLM)                  │   │
│  │  → Synthèse intelligente                             │   │
│  │  → Langage naturel                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 MONITORING (monitoring.py)                   │
│  - Logs JSONL                                                │
│  - Métriques de performance                                  │
│  - Traçabilité complète                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Choix Techniques et Justifications

### 1. **LLM: Google Gemini 1.5 Flash**
**Pourquoi?**
- Gratuit avec API fournie par le professeur
- Rapide (faible latence)
- Bon pour classification et génération
- Support du français natif

**Alternatives considérées:**
- OpenAI GPT-4: Payant, excellente qualité
- Claude: Payant, très bon raisonnement
- Llama open-source: Nécessite infrastructure

### 2. **RAG: FAISS + HuggingFace Embeddings**
**Pourquoi?**
- FAISS: Ultra-rapide, local, pas de coûts
- all-MiniLM-L6-v2: Léger (80MB), bon équilibre qualité/vitesse
- Pas besoin de connexion externe

**Alternatives:**
- Pinecone/Weaviate: Cloud, payant
- Chroma: Bon mais plus lourd
- OpenAI embeddings: Excellent mais coûteux

### 3. **Architecture: LLM-Orchestrated Agent**
**Pourquoi?**
- Flexible: LLM décide intelligemment de la source
- Évolutif: Facile d'ajouter de nouvelles sources
- Traçable: Chaque décision est loggée

**Alternatives:**
- ReAct Agent (LangChain): Plus complexe, parfois instable
- Multi-agent avec LangGraph: Over-engineering pour ce cas
- Règles fixes: Pas assez flexible

### 4. **Data Queries: LLM-Assisted Pandas**
**Pourquoi?**
- LLM comprend l'intention → génère plan de requête
- Pandas: Flexible, pas besoin de SQL
- Sécurisé: Pas d'exécution de code arbitraire

**Alternatives:**
- SQL Agent: Nécessite conversion en SQL
- PandasAI: Dépendance externe lourde
- create_pandas_dataframe_agent: Moins contrôlable

---

## 📦 Installation

### 1. Cloner et créer une branche
```bash
git clone https://github.com/Rblaze23/telecomplus-agent.git
cd telecomplus-agent
git checkout -b FEATURE/votre-nom
```

### 2. Créer environnement virtuel
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer l'API Gemini
Créer un fichier `.env` à la racine:
```
GOOGLE_API_KEY="key"
```

---

## 🚀 Utilisation

### Lancer l'interface Streamlit
```bash
streamlit run app.py
```

L'interface s'ouvre à `http://localhost:8501`

### Lancer l'évaluation
```bash
python evaluate.py
```

Cela génère:
- `evaluation_results_YYYYMMDD_HHMMSS.xlsx`: Résultats détaillés
- `evaluation_stats_YYYYMMDD_HHMMSS.json`: Statistiques agrégées

### Tester manuellement
```python
from src.main import answer

response = answer("Quels modes de paiement acceptez-vous?")
print(response)
```

---

## 📊 Résultats d'Évaluation

### Métriques d'Évaluation (LLM-as-a-Judge)
Notre système évalue chaque réponse sur 3 critères:

1. **Exactitude Factuelle** (0-4 points)
   - Toutes les informations sont-elles correctes?
   
2. **Complétude** (0-3 points)
   - La réponse couvre-t-elle tous les aspects?
   
3. **Pertinence** (0-3 points)
   - La réponse est-elle directement utile?

**Score total: 0-10 points**

### Résultats Attendus (objectif)
- Score moyen: **≥ 7.0/10**
- Taux de réussite (≥6/10): **≥ 80%**
- Exactitude factuelle: **≥ 3.0/4**

### Performance Actuelle
*À compléter après exécution de evaluate.py*

```
Total questions: 25
Score moyen: X.X/10
Taux de réussite: XX%

Par composant:
- Exactitude: X.X/4
- Complétude: X.X/3
- Pertinence: X.X/3
```

---

## 📁 Structure du Projet

```
dauphine-project-iasd-2025/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Point d'entrée principal
│   ├── orchestrator.py         # Cerveau: classification + coordination
│   ├── vector_db.py            # Recherche sémantique dans PDFs
│   ├── data_queries.py         # Requêtes intelligentes sur Excel
│   ├── load_data.py            # Chargement des données Excel
│   ├── load_pdfs.py            # Chargement et chunking des PDFs
│   └── monitoring.py           # Système de monitoring et logs
│
├── data/
│   ├── xlsx/                   # Données Excel (6 tables)
│   │   ├── clients.xlsx
│   │   ├── forfaits.xlsx
│   │   ├── abonnements.xlsx
│   │   ├── consommation.xlsx
│   │   ├── factures.xlsx
│   │   └── tickets_support.xlsx
│   │
│   ├── pdfs/                   # Documents FAQ (7 PDFs)
│   │   ├── FAQ_Facturation_et_Paiements.pdf
│   │   ├── FAQ_Forfaits_et_Abonnements.pdf
│   │   ├── FAQ_Support_Technique.pdf
│   │   └── ... (4 autres)
│   │
│   └── evaluation_questions.xlsx  # Dataset d'évaluation (25 questions)
│
├── logs/                       # Logs générés par monitoring
│   ├── agent_log_YYYYMMDD.jsonl
│   └── metrics_YYYYMMDD.json
│
├── faiss_index/                # Base vectorielle FAISS
│   ├── index.faiss
│   └── index.pkl
│
├── app.py                      # Interface Streamlit
├── evaluate.py                 # Script d'évaluation LLM-as-a-judge
├── requirements.txt            # Dépendances Python
├── .env                        # Variables d'environnement (API key)
└── README.md                   # Cette documentation
```

---

## 🔍 Monitoring et Traçabilité

### Logs Disponibles

Le système génère automatiquement:

1. **Logs détaillés (JSONL)**
   - Fichier: `logs/agent_log_YYYYMMDD.jsonl`
   - Contenu: Chaque requête avec tous les événements
   ```json
   {
     "query_id": "q_1234567890",
     "timestamp": "2025-12-06T10:30:00",
     "question": "Quels modes de paiement?",
     "events": [
       {"type": "classification", "data": {"source": "faq"}},
       {"type": "pdf_query", "data": {"results_found": 3}}
     ],
     "latency_seconds": 1.23,
     "success": true
   }
   ```

2. **Métriques agrégées (JSON)**
   - Fichier: `logs/metrics_YYYYMMDD.json`
   - Contenu: Statistiques de session
   ```json
   {
     "total_queries": 100,
     "successful_queries": 95,
     "success_rate": 95.0,
     "avg_latency": 1.15,
     "source_usage": {
       "faq": 60,
       "data": 30,
       "both": 10
     }
   }
   ```

### Afficher les Statistiques
```python
from src.main import print_agent_summary
print_agent_summary()
```

### Analyser les Logs
```python
from src.monitoring import analyze_logs

stats = analyze_logs("logs/agent_log_20251206.jsonl")
print(stats)
```

---

## 🎓 Points Forts du Projet

### ✅ Performance et Pertinence (30%)
- **LLM-as-a-judge** complet avec Gemini
- Évaluation sur 3 dimensions (exactitude, complétude, pertinence)
- Métriques détaillées par difficulté
- Génération de rapports Excel

### ✅ Qualité du Code (30%)
- **Documentation complète** avec docstrings
- Code organisé et modulaire
- Gestion d'erreurs robuste
- Prompts bien structurés et explicites
- Séparation des responsabilités claire

### ✅ Architecture Agentique (25%)
- **LLM orchestration** intelligente (pas juste keywords)
- Classification dynamique avec raisonnement
- Génération de réponses naturelles
- Synthèse multi-sources
- Extensible et maintenable

### ✅ Monitoring (15%)
- Logs JSONL complets
- Métriques en temps réel
- Traçabilité totale des décisions
- Analyse de performance
- Débogage facilité

---

## 🚨 Points d'Attention

### Ce qui pourrait être amélioré
1. **Gestion des identités clients**: Actuellement pas d'authentification
2. **Cache des embeddings**: Régénérés à chaque démarrage
3. **Gestion du contexte multi-tour**: Pas de mémoire conversationnelle
4. **Tests unitaires**: Pas de tests automatisés

### Améliorations possibles
- Ajouter LangSmith/Langfuse pour monitoring cloud
- Implémenter un cache Redis pour les requêtes fréquentes
- Ajouter des tests avec pytest
- Créer un dashboard de monitoring avec Streamlit

---

## 📝 Exemples de Questions Supportées

### Questions FAQ (Générales)
```
✓ "Quels modes de paiement acceptez-vous?"
✓ "Y a-t-il des frais de résiliation?"
✓ "Comment fonctionne le roaming international?"
✓ "Quels sont les forfaits disponibles?"
```

### Questions DATA (Clients)
```
✓ "Combien de clients avez-vous?"
✓ "Quelles sont les factures impayées?"
✓ "Quelle est la consommation moyenne?"
✓ "Combien de tickets de support ouverts?"
```

### Questions Hybrides
```
✓ "Quel est le forfait le plus populaire et son prix?"
✓ "Combien de clients sont hors engagement?"
```

---

## 👥 Équipe et Contributions

**Développeur**: [Votre Nom]
**Cours**: IASD - Université Paris Dauphine
**Année**: 2025-2026
**Professeur**: [Nom du professeur]

### Contributions Git
```bash
# Voir vos commits
git log --oneline --author="votre-nom"

# Statistiques
git shortlog -sn
```

---

## 📚 Références et Documentation

### Technologies Utilisées
- **LangChain**: https://python.langchain.com/
- **FAISS**: https://github.com/facebookresearch/faiss
- **Gemini API**: https://ai.google.dev/
- **Streamlit**: https://streamlit.io/

### Articles de Référence
- RAG: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- LLM-as-a-Judge: "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
- Agent Architectures: "ReAct: Synergizing Reasoning and Acting in Language Models"

---

## 📞 Support

Pour toute question:
 Créer une issue sur GitHub
 Email: ramy.lazghab@dauphine.eu

---

## 📄 License

Ce projet est réalisé dans un cadre académique pour l'Université Paris Dauphine.