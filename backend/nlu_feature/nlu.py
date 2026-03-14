import pandas as pd
import numpy as np
import string

#Lecture du fichier (dataset) 
def charger_dataset():
    try: 
        with open ('dataset.csv', 'r', encoding='utf-8') as f:
            data = f.read()       
        print("Fichier chargé avec succès")
        print(data)
        return data

    except FileNotFoundError: 
        print("Erreur, fichier non trouvé")

    except Exception as e:
        print("Une erreur est survenue")   



#Nettoyage des données 
def nettoyer_donnees(brute):
    if brute is None:
        return 
    
    dataset_entrainement = [] # ex: couple [Sokafy chrome, ouvrir_chrome()]
    stop_words = ["mba", "indrindra", "koa", "ny", "azafady"]
    dictionnaire_mots = [] # liste de tous les mots uniques

    # Separation par lignes du dataset.csv
    lignes = brute.split("\n")
    for ligne in lignes: 
        if not ligne or ',' not in ligne:
            continue

        # Separation de l'action et commande
        ligne_nettoye = ligne.lower().strip()
        
        # Apres division du texte    
        colonnes = ligne_nettoye.split(",")

        ordre_nettoye = colonnes[0].lower().strip()

        # Enlever ponctuation
        ponctuation = string.punctuation
        for symbole in ponctuation:
            ordre_nettoye = ordre_nettoye.replace(symbole, "")
        
        # Transformation phrase en liste de mots
        tokens = ordre_nettoye.split(" ")

        # Mots inutile ou mots filrés
        features = [mot for mot in tokens if mot not in stop_words]

        # Ajout 1 par 1 de tous les mots existants
        dictionnaire_mots.extend(features)
        dataset_entrainement.append([features, colonnes[1].strip()])
        
    # Creer une liste sans doublons
    vocabulaire_globale = list(set(dictionnaire_mots))
    print("Nettoyage terminé")
    print(dataset_entrainement)

    # Retourner Intentions et liste de mots uniques 
    return dataset_entrainement, dictionnaire_mots 

dataset_brute = charger_dataset()
nettoyer_donnees(dataset_brute)