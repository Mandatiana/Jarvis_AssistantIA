import os
import winsound
import random

# 1. On trouve le chemin du fichier actuel (audio_service.py)
# 2. On remonte de DEUX niveaux pour arriver à la racine du projet
# (Si audio_service.py est dans backend/nlu_feature/ ou backend/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 3. On définit le chemin vers static/audio à partir de la racine
# Si ton dossier s'appelle 'backend/static/audio', on l'écrit comme ça :
BASE_AUDIO_DIR = os.path.join(BASE_DIR, "static", "audio")


def jouer_audio_aleatoire(categorie, force_premier=False): # Ajout de l'argument
    chemin_dossier = os.path.join(BASE_AUDIO_DIR, categorie)
    if not os.path.exists(chemin_dossier): return

    fichiers = sorted([f for f in os.listdir(chemin_dossier) if f.endswith('.wav')])

    if fichiers:
        # Si force_premier est Vrai, on prend le 1er, sinon on prend au hasard
        son_choisi = fichiers[0] if force_premier else random.choice(fichiers)
        
        chemin_final = os.path.join(chemin_dossier, son_choisi)
        winsound.PlaySound(chemin_final, winsound.SND_FILENAME | winsound.SND_ASYNC)