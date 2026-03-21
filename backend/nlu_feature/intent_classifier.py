import math
import numpy as np
from preprocessing import nettoyer_phrase, nettoyer_dataset, charger_dataset


#on appelle le resulat du chargement des données
contenu = charger_dataset()

#2 arguments car nettoyer dataset returne 2 valeurs
dataset_entrainement, vocabulaire_globale = nettoyer_dataset(contenu)


def vectoriser(phrase_commande, vocabulaire):
    vecteur = np.zeros(len(vocabulaire), dtype=int)
    for mot in phrase_commande:
        if mot in vocabulaire:
            indice = vocabulaire.index(mot)
            vecteur[indice] = 1

    return vecteur

#Vectoriser tous les lignes du dataset
def entrainer_modele(dataset, vocabulaire):

    #Matrice vide
    X_temp = []
    for ligne in dataset:
       mots_dataset = ligne[0]
       v_ligne = vectoriser(mots_dataset, vocabulaire)
       X_temp.append(v_ligne)
    
    return np.array(X_temp)


#Calcul de la distance eucludienne
def calcul_des_distances(v_user, v_dataset):
    distances = []

    #v_ligne represente dataset, v_dataset tous les lignes du dataset
    for v_ligne in v_dataset:

        #v_user represente vecteur de l'input user
        difference = v_user - v_ligne

        somme_carree = np.sum(difference**2)

        distance = math.sqrt(somme_carree)
        distances.append(distance)
    return distances


def interpreter_commande():

    #Demander input
    sentence = input("Que voulez vous faire Monsieur ?\n")
    clean_sentence = nettoyer_phrase(sentence)

    #Verifier si on connait les mots
    resultat = [m for m in clean_sentence if m in vocabulaire_globale]
    if len(resultat) == 0:
        return None
    
    #Vectorisation
    vecteur_user = vectoriser(resultat, vocabulaire_globale)

    X_train = entrainer_modele(dataset_entrainement, vocabulaire_globale)
    tous_les_scores = calcul_des_distances(vecteur_user, X_train)

    #Retirer indice du min
    indice_min = np.argmin(tous_les_scores)
    score = tous_les_scores[indice_min]
    seuil = 1.5

    if score <= seuil:
        return dataset_entrainement[indice_min][1]
    else:
        return None
    
