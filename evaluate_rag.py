"""
evaluate_rag.py — Proper RAG evaluation: retrieval + generation metrics.

Retrieval:  Hit Rate@k and Mean Reciprocal Rank (MRR)
Generation: Semantic similarity between the generated answer and a reference answer
"""

import numpy as np
from sentence_transformers import SentenceTransformer, util
# Importing pipeline components from your core implementation
from rag import (build_or_load_index, answer_question, transform_query,
                 _get_reranker, RETRIEVE_K, RERANK_K)

# Combined comprehensive test set mapped to sample_tfl_fares.txt
TEST_CASES = [
    # --- Original Test Cases ---
    {
        "question": "How do I get to Heathrow?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "You can reach Heathrow via the Piccadilly line, Elizabeth line, or Heathrow Express from Paddington.",
    },
    {
        "question": "Do children travel free?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "Children under 11 travel free on buses and trams when accompanied by an adult.",
    },
    {
        "question": "What is the Hopper fare?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "The Hopper fare allows unlimited bus and tram transfers within one hour using the same payment method.",
    },
    {
        "question": "Is contactless accepted on the Stansted Express?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "No, contactless and Oyster are not accepted on the Stansted Express; you need a separate ticket.",
    },
    {
        "question": "Which stations are step-free?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "94 Tube stations, over 60 Overground stations, and all Elizabeth line stations have step-free access.",
    },
    
    # --- Core System & Fare Checking Cases ---
    {
        "question": "What are the hours for peak travel fares?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "Peak fares apply on weekdays, typically Monday to Friday from 06:30 to 09:30 and 16:00 to 19:00.",
    },
    {
        "question": "How does daily and weekly fare capping work?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "Once your Pay As You Go journeys hit the daily or weekly cap for the zones traveled, additional eligible journeys are not charged.",
    },
    {
        "question": "Can I link my railcard discount to my Oyster card?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "Yes, railcard holders can add discounts to their Oyster card at station ticket machines.",
    },
    
    # --- Airport Travel Alternatives ---
    {
        "question": "Can I use an Oyster card to get to Gatwick Airport?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "Yes, Oyster and Contactless are accepted on all train services between London and Gatwick Airport.",
    },
    {
        "question": "What is the journey time and line for London City Airport?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "London City Airport is served by the DLR and takes approximately 20 minutes to reach Bank station.",
    },
    
    # --- Night Services Network ---
    {
        "question": "Which lines run during the Night Tube and what are their frequencies?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "The Victoria, Jubilee, Central, Northern, and Piccadilly lines run every 8 to 20 minutes depending on the line and branch.",
    },
    {
        "question": "What nights does the Night Overground operate and on what route?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "The Night Overground operates on Friday and Saturday nights on the Windrush line between Highbury & Islington and New Cross Gate.",
    },
    {
        "question": "Are Night Tube fares more expensive?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "No, Night Tube travel is charged at standard off-peak rates.",
    },
    
    # --- System FAQ Mechanics ---
    {
        "question": "Can I pay for my travel using Apple Pay?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "Yes, you can use any contactless-enabled device, including Apple Pay and Google Pay.",
    },
    {
        "question": "What happens if I forget to touch out at the end of my journey?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "If you forget to touch out, you may be charged a maximum fare, and you should contact TfL support for corrections.",
    },
    {
        "question": "Can my friend and I share the same Oyster card for a journey?",
        "expected_source": "sample_tfl_fares.txt",
        "reference": "No, each passenger must have their own separate payment method to travel.",
    }
]

# Small, efficient local transformer for evaluating alignment semantic similarity
_sim_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def evaluate_retrieval(vectordb):
    """Hit Rate@k and MRR: verifies if the index properly groups and surfaces target files."""
    hits, reciprocal_ranks = [], []
    for case in TEST_CASES:
        q = case["question"]
        expected = case["expected_source"]

        # Simulate execution pipeline: transformation -> vector match -> cross-encoder re-rank
        search_q = transform_query(q)
        candidates = vectordb.similarity_search(search_q, k=RETRIEVE_K)
        
        reranker = _get_reranker()
        scores = reranker.predict([(q, d.page_content) for d in candidates])
        ranked = [d for _, d in sorted(zip(scores, candidates),
                                       key=lambda x: x[0], reverse=True)][:RERANK_K]

        # Evaluate positioning depth inside final window context
        rank = None
        for i, doc in enumerate(ranked):
            src = doc.metadata.get("source", "")
            if expected in src:
                rank = i + 1
                break
        
        hits.append(1 if rank else 0)
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)

    hit_rate = np.mean(hits)
    mrr = np.mean(reciprocal_ranks)
    return hit_rate, mrr


def evaluate_generation(vectordb):
    """Calculates cosine semantic similarity between the generated string and gold standard values."""
    sims = []
    for case in TEST_CASES:
        result = answer_question(vectordb, case["question"])
        
        # Vectorize and compare semantic tensors
        emb_gen = _sim_model.encode(result.text, convert_to_tensor=True)
        emb_ref = _sim_model.encode(case["reference"], convert_to_tensor=True)
        sim = util.cos_sim(emb_gen, emb_ref).item()
        sims.append(sim)
        
        print(f"  Q: {case['question']}")
        print(f"     Similarity to reference: {sim:.3f}")
        print(f"     Answer string: {result.text[:120]}...\n")
        
    return np.mean(sims)


def main():
    print("Initializing vector index mapping configuration...")
    vectordb = build_or_load_index()

    print("=" * 60)
    print("RUNNING RETRIEVAL EVALUATION")
    print("=" * 60)
    hit_rate, mrr = evaluate_retrieval(vectordb)
    print(f"  Hit Rate@{RERANK_K}: {hit_rate:.2f}  (fraction retrieving the right source)")
    print(f"  MRR:          {mrr:.2f}  (how highly the right source ranks)")

    print("\n" + "=" * 60)
    print("RUNNING GENERATION EVALUATION")
    print("=" * 60)
    avg_sim = evaluate_generation(vectordb)
    print(f"  Avg semantic similarity to reference: {avg_sim:.3f}")
    print("  (1.0 = identical meaning, higher is better)")


if __name__ == "__main__":
    main()