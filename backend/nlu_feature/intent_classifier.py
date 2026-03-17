import math
import numpy as np
from preprocessing import nettoyer_phrase, nettoyer_dataset, charger_dataset

K_value = 3 #Pour l'algo KNN

#on appelle le resulat du chargement des données
#contenu = charger_dataset()


mon_vocabulaire = ["meteo", "chrome", "envoye", "mail"]
ma_phrase = "envoye mail"

def vectoriser(intent,vocabulaire):
    vecteur = np.zeros(len(mon_vocabulaire), dtype=int)
    clean = nettoyer_phrase(ma_phrase)

    for word in mon_vocabulaire:
        if word in clean:
            indice = mon_vocabulaire.index(word)
            vecteur[indice] = 1
    print(vecteur)
    return vecteur


vectoriser(ma_phrase,mon_vocabulaire)

