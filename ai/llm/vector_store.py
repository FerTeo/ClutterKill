"""
Vector Store pentru Dynamic Few-Shot Prompting (RAG Core)

Acest modul gestionează o bază de date vectorială locală (ChromaDB) în care salvăm
deciziile anterioare de redenumire (textul brut + decizia luată).
Când vine un document nou, vom căuta documente similare în această bază de date
și le vom oferi agentului LLM ca exemple de "așa da" (Dynamic Few-Shot).
"""
import json
import logging
import uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Locația unde se va salva baza de date vectorială
_DB_PATH = Path(__file__).parent.parent / "chroma_db"
_DB_PATH.mkdir(parents=True, exist_ok=True)

class VectorStoreManager:
    """Gestionează conexiunea cu ChromaDB și operațiile RAG."""

    def __init__(self, collection_name: str = "rename_decisions"):
        """
        Inițializează ChromaDB cu un model local de embeddings ușor și rapid.
        `all-MiniLM-L6-v2` rulează 100% offline și este ideal pentru texte scurte spre medii.
        """
        logger.info(f"Inițializare ChromaDB la {_DB_PATH}")
        self._client = chromadb.PersistentClient(path=str(_DB_PATH))
        
        # Această funcție va descărca automat all-MiniLM-L6-v2 la prima rulare (~80MB)
        self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"} # cosine similarity funcționează bine pentru text
        )

    def save_decision(self, document_text: str, decision_json: dict) -> str:
        """
        Salvează textul documentului ca vector, având decizia ca metadate atașate.
        
        Args:
            document_text (str): Textul extras din fișier (trunchiat ideal).
            decision_json (dict): Decizia finală (ex: {"new_name": "...", "category": "..."})
            
        Returns:
            str: ID-ul unic al înregistrării.
        """
        record_id = str(uuid.uuid4())
        
        # ChromaDB cere ca metadatele să fie simple (str, int, float)
        # Deci serializăm dicționarul deciziei ca string JSON.
        metadata = {
            "decision": json.dumps(decision_json, ensure_ascii=False)
        }
        
        self._collection.add(
            documents=[document_text],
            metadatas=[metadata],
            ids=[record_id]
        )
        
        logger.info(f"Salvat decizie in ChromaDB cu ID: {record_id}")
        return record_id

    def get_similar_examples(self, current_text: str, k: int = 3) -> list[dict]:
        """
        Caută cele mai similare `k` documente procesate anterior pe baza textului curent.
        Acestea vor fi injectate în prompt-ul LLM-ului.
        
        Args:
            current_text (str): Textul documentului curent care trebuie evaluat.
            k (int): Numărul maxim de exemple returnate.
            
        Returns:
            list[dict]: O listă de dicționare formatate ca exemple pentru Few-Shot.
                        ex: [{"text": "...", "decision": {"new_name": "..."}}]
        """
        if self._collection.count() == 0:
            return [] # Baza de date este goală, nu avem exemple încă.

        # Limităm `k` la numărul de documente existente
        k_actual = min(k, self._collection.count())
        
        results = self._collection.query(
            query_texts=[current_text],
            n_results=k_actual
        )
        
        examples = []
        if results and results["documents"] and len(results["documents"][0]) > 0:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            
            for doc, meta in zip(docs, metadatas):
                try:
                    decision_dict = json.loads(meta["decision"])
                    examples.append({
                        "text": doc,
                        "decision": decision_dict
                    })
                except Exception as e:
                    logger.warning(f"Eroare la parsarea JSON-ului din ChromaDB: {e}")
                    
        return examples

# Singleton pentru a nu reinițializa clientul de fiecare dată
vector_store = VectorStoreManager()
