import requests
import json
import os
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import time

# --- OpenRouter API Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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") # IMPORTANT: Replace with your key or set ENV VAR
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL_NAME = "deepseek/deepseek-coder" # Or your preferred DeepSeek V2 model - DEPRECATED
DEEPSEEK_MODEL_NAME_DEFAULT = os.getenv("DEEPSEEK_MODEL_NAME_DEFAULT", "deepseek/deepseek-chat-v3-0324:free") # Updated default model

# --- Embedding Model and ChromaDB Configuration ---
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' # Small and fast, good for general purpose
CHROMA_DB_PATH = Path(__file__).resolve().parent.parent / "vector_db"
COLLECTION_NAME = "asic_verification_kb"

# Global ChromaDB client and collection (initialized when needed)
chroma_client = None
kb_collection = None # This is the global we want to update and access
sentence_transformer_ef = None

def initialize_chromadb_client_and_collection():
    """
    Initializes the ChromaDB client and the specified collection.
    Ensures that kb_collection is assigned the global collection object.
    """
    global chroma_client, kb_collection, sentence_transformer_ef # Declare we're using/modifying these globals

    # Check if already initialized to prevent redundant operations
    if kb_collection is not None and chroma_client is not None:
        print("ChromaDB client and collection already initialized.")
        return

    print(f"Initializing ChromaDB client at: {CHROMA_DB_PATH}")
    if not CHROMA_DB_PATH.exists():
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    
    # Initialize client if not already done
    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    
    # Initialize embedding function if not already done
    if sentence_transformer_ef is None:
        print(f"Initializing Sentence Transformer embedding function: {EMBEDDING_MODEL_NAME}")
        sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)

    print(f"Getting or creating ChromaDB collection: {COLLECTION_NAME}")
    # Assign to the global kb_collection
    try:
        kb_collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=sentence_transformer_ef
        )
        print("ChromaDB client and collection successfully initialized/retrieved.")
    except Exception as e:
        print(f"ERROR: Failed to get or create ChromaDB collection '{COLLECTION_NAME}'. Exception: {e}")
        # Reset kb_collection to None if initialization failed to allow retry or signal error
        kb_collection = None
        # Optionally, re-raise the exception if this is critical and should halt execution
        # raise

def get_embedding_for_rag(text_chunk: str):
    """
    Generates an embedding for a given text chunk using the configured sentence transformer.
    Mainly for utility if direct embedding is needed outside ChromaDB's auto-embedding.
    """
    initialize_chromadb_client_and_collection() # Ensure embedding function is ready
    if sentence_transformer_ef is None or not text_chunk or not isinstance(text_chunk, str):
        print("Warning: Embedding function not ready or invalid input for get_embedding_for_rag.")
        return []
    return sentence_transformer_ef([text_chunk])[0]


def call_deepseek_api(prompt_text: str, model_name: str = DEEPSEEK_MODEL_NAME_DEFAULT, temperature: float = 0.5, max_tokens: int = 3000):
    if not OPENROUTER_API_KEY or len(OPENROUTER_API_KEY.strip()) < 10:
        print("ERROR: OPENROUTER_API_KEY is not set or appears to be invalid. Please set your valid API key.")
        return "Error: API Key not configured. Please check common_utils.py or environment variables."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    print(f"\n--- Sending request to OpenRouter (Model: {model_name}) ---")
    max_retries = 3
    retry_delay = 5 # seconds
    for attempt in range(max_retries):
        try:
            response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(data), timeout=180)
            response.raise_for_status()
            response_json = response.json()
            
            if response_json.get("choices") and len(response_json["choices"]) > 0:
                content = response_json["choices"][0].get("message", {}).get("content")
                if content:
                    print("--- Successfully received response from OpenRouter ---")
                    return content.strip()
            
            print(f"Unexpected API response structure on attempt {attempt + 1}: {response_json}")
            # Consider this a non-retryable error if structure is wrong
            raise ValueError("API response did not contain expected content format or content was empty.")

        except requests.exceptions.Timeout as e:
            print(f"Error: API request timed out on attempt {attempt + 1}/{max_retries}. Details: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Error during API request on attempt {attempt + 1}/{max_retries}. Details: {e}")
            if e.response is not None:
                print(f"Response status code: {e.response.status_code}")
                try:
                    print(f"Response content: {e.response.json()}")
                except json.JSONDecodeError:
                    print(f"Response content (not JSON): {e.response.text}")
        except ValueError as e: # Handles our custom ValueError for content issues
            print(f"Error processing API response: {e}")
            break # Break retry loop for ValueError

        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("Max retries reached. API call failed.")
            # Re-raise the last exception or a generic one
            if 'e' in locals(): # if an exception was caught
                 raise e
            else: # if loop completed due to structure error not raising requests exception
                 raise Exception("API call failed after multiple retries or due to response structure.")
    return "Error: API call failed after multiple retries."


def retrieve_relevant_chunks(query_text: str, top_k: int = 3, doc_type_filter: str = None):
    initialize_chromadb_client_and_collection() # Crucial: ensures kb_collection is initialized
    
    print(f"\n--- Retrieving relevant chunks for query (first 50 chars): '{query_text[:50]}...' with filter: '{doc_type_filter}' ---")
    
    if kb_collection is None: # Check if the global kb_collection is properly set
        print("Error: KB Collection not initialized (kb_collection is None in common_utils). RAG retrieval cannot proceed.")
        return []

    if not query_text:
        print("Warning: Empty query text for RAG retrieval.")
        return []

    try:
        where_filter = None
        if doc_type_filter:
            where_filter = {"doc_type": doc_type_filter}

        # query_embeddings are not needed if using an embedding_function with the collection
        results = kb_collection.query(
            query_texts=[query_text], 
            n_results=top_k,
            where=where_filter
        )
        
        retrieved_docs = results.get('documents', [[]])[0]
        if retrieved_docs:
            print(f"Retrieved {len(retrieved_docs)} chunks. First chunk (first 100 chars): '{retrieved_docs[0][:100]}...'")
        else:
            print("No chunks retrieved for the query.")
        return retrieved_docs
    except Exception as e:
        print(f"Error during ChromaDB RAG retrieval: {e}")
        return []

def load_prompt_template(template_filename: str) -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / template_filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt template file not found at {prompt_path}")
        return ""

if __name__ == '__main__':
    print("Testing common_utils.py...")
    # This call will attempt to initialize and print status
    initialize_chromadb_client_and_collection() 
    
    if kb_collection is not None:
        print(f"Test: Collection '{kb_collection.name}' count: {kb_collection.count()}")
    else:
        print("Test: kb_collection is None after initialization attempt.")

    # Test API call (BE MINDFUL OF API USAGE/COSTS if you uncomment)
    # try:
    #     test_prompt = "Write a short Python function that returns 'hello world from Morocco'."
    #     api_response = call_deepseek_api(test_prompt, max_tokens=60)
    #     print("\n--- Test API Response ---")
    #     print(api_response)
    # except Exception as e:
    #     print(f"Test API call failed: {e}")
    
    print("\nFinished testing common_utils.py. Ensure your API key is correctly set for API calls.")