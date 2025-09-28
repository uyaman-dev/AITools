"""
A simple script to list all available Google Generative AI models.
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

def list_available_models():
    """List all available models from Google Generative AI API."""
    # Load environment variables
    load_dotenv()
    
    # Configure the API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    
    # Configure the API
    genai.configure(api_key=api_key)
    
    try:
        # List all models
        print("Fetching available models...")
        models = genai.list_models()
        
        if not models:
            print("No models found.")
            return
            
        print("\nAvailable models:")
        print("-" * 50)
        for model in models:
            print(f"Name: {model.name}")
            print(f"Description: {model.description}")
            print(f"Supported methods: {model.supported_generation_methods}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    list_available_models()
