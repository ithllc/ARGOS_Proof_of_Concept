import json
import re
from typing import List
from collections import Counter
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from redis_client import redis_client

def synthesize(paper_ids: List[str], synthesis_key: str | None = None) -> dict:
    """Synthesize concepts from a list of parsed papers (paper:ID stored in redis)."""
    texts = []
    metadata = {}
    for pid in paper_ids:
        paper = redis_client.get_all_hash_fields(pid) or {}
        text = paper.get("text", "")
        title = paper.get("title", "")
        texts.append(text[:5000])
        metadata[pid] = {"title": title}

    synth = {"overlap": [], "feasibility": 0.0, "applications": []}
    
    if texts:
        clean_texts = [re.sub(r'[^a-zA-Z\s]', '', doc.lower()) for doc in texts]
        doc_word_sets = [
            set(word for word in doc.split() if word not in ENGLISH_STOP_WORDS and word)
            for doc in clean_texts
        ]

        overlap_words = set()
        if doc_word_sets:
            word_doc_counts = Counter()
            for word_set in doc_word_sets:
                word_doc_counts.update(word_set)
            
            multi_doc_words = {word for word, count in word_doc_counts.items() if count > 1}
            total_word_counts = Counter(word for doc in clean_texts for word in doc.split())
            
            sorted_multi_doc_words = sorted(
                multi_doc_words, 
                key=lambda w: total_word_counts.get(w, 0), 
                reverse=True
            )
            overlap_words.update(sorted_multi_doc_words)

        synth["overlap"] = list(overlap_words)[:10]
        doc_lengths = [len(t) for t in texts]
        synth["feasibility"] = round(min(10.0, sum(1 for dl in doc_lengths if dl > 1000) / max(1, len(doc_lengths)) * 10), 2)
        
        if synth["overlap"]:
            synth["applications"] = [f"Use {synth['overlap'][:3]} for optimization workflows"]

    result_key = synthesis_key or f"synthesis:{','.join(paper_ids)}"
    redis_client.set_with_ttl(result_key, json.dumps(synth), 3600)
    redis_client.publish_message("agent:activity", json.dumps({"agent": "planning", "status": "synthesized", "key": result_key}))
    return synth

root_agent = LlmAgent(
    name="planning",
    instruction="You are a planning agent. You can synthesize concepts from a list of papers.",
    tools=[
        FunctionTool(
            func=synthesize,
            description="Synthesizes concepts from a list of parsed papers.",
        )
    ]
)
