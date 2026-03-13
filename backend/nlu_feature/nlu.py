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

#Preprocessing, data cleaning

"""def nettoyer_phrase():  #lowercase puis supprimer ponctuation, et enfin split la phrase
    ponctuation = string.punctuation
    phrase = str(input("Entrez une commande:\n")).lower()
    for symbole in ponctuation:
        phrase = phrase.replace(symbole,"")
    resultat = phrase.split()
    print(resultat)
    
nettoyer_phrase()

"""



#fonction de nettoyage
def nettoyer_donnees(dataset_brute):
    if dataset_brute is None:
        return
    
    #separation des donnees par lignes
    lignes = dataset_brute.split("\n")
    print("Nb de lignes: ", {len(lignes)})
    

    #separation action et commande
    for ligne in lignes:
        if not ligne or ',' not in ligne: #s il n'y a pas de ligne ou la virgule n'est pas dans une ligne
            continue
        action = ligne.split(",")
        clean_action = action[0].lower().strip()
        ponctuation = string.punctuation
        for symbole in ponctuation:
            clean_action = clean_action.replace(symbole, "")
        print(clean_action, action[1])


donnees_brute = charger_dataset()
nettoyer_donnees(donnees_brute)