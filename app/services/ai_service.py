"""
Service Ollama - appels HTTP au modèle local
"""

import requests
from typing import Optional
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Sur Docker, utiliser host.docker.internal pour accéder à la machine hôte
# Sur localhost, utiliser directement localhost
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL = "mistral:7b"
REQUEST_TIMEOUT = 180  # Augmenté pour Ollama (génération peut être lente)


def is_ollama_running() -> bool:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama not running: {e}")
        return False


def generate_summary(content: str, model: str = DEFAULT_MODEL) -> tuple[str, int, int]:
    if not is_ollama_running():
        raise Exception("Ollama not running")
    
    prompt = f"""Résume le texte en 2-3 phrases:

{content}

Résumé:"""
    
    try:
        start_time = datetime.utcnow()
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=REQUEST_TIMEOUT
        )
        
        response.raise_for_status()
        data = response.json()
        
        summary = data.get("response", "").strip()
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return summary, tokens, elapsed_ms
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


def extract_actions(content: str, model: str = DEFAULT_MODEL) -> tuple[list[str], int, int]:
    if not is_ollama_running():
        raise Exception("Ollama not running")
    
    prompt = f"""Extrait les actions du texte, une par ligne:

{content}

Actions:"""
    
    try:
        start_time = datetime.utcnow()
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=REQUEST_TIMEOUT
        )
        
        response.raise_for_status()
        data = response.json()
        
        text = data.get("response", "").strip()
        actions = [line.strip() for line in text.split('\n') if line.strip()]
        
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return actions, tokens, elapsed_ms
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


def analyze_sentiment(content: str, model: str = DEFAULT_MODEL) -> tuple[str, int, int]:
    if not is_ollama_running():
        raise Exception("Ollama not running")
    
    prompt = f"""Analyse le sentiment (positive/negative/neutral):

{content}

Sentiment:"""
    
    try:
        start_time = datetime.utcnow()
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=REQUEST_TIMEOUT
        )
        
        response.raise_for_status()
        data = response.json()
        
        result = data.get("response", "").strip().lower()
        
        if result not in ("positive", "negative", "neutral"):
            result = "neutral"
        
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return result, tokens, elapsed_ms
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
