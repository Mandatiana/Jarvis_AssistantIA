import requests
from dotenv import load_dotenv
import os

load_dotenv()  


#Modification pour l'importer dans le KNN (response non programmé)

def ask_jarvis(question):
    url = "https://models.github.ai/inference/chat/completions"
    ApiKey =os.getenv('API_KEY')

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {ApiKey}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Tu es JARVIS. Tu dois répondre EXCLUSIVEMENT en français, de manière concise et polie. Ne réponds jamais dans une autre langue"},
            {"role": "user", "content": question}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            reponse_texte = response.json()["choices"][0]["message"]["content"]
            return reponse_texte
        else:
            return "Désolé monsieur, je recontre des difficultés de connexion"
    except Exception as e:
        return f"Erreur de communication: {e}"
