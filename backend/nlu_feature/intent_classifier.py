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

X_train = entrainer_modele(dataset_entrainement, vocabulaire_globale)
print(X_train)

def prompt_user():
    sentence = input("Que voulez vous faire? \n")
    clean_sentence = nettoyer_phrase(sentence)
    resultat = [m for m in clean_sentence if m in vocabulaire_globale]
    if len(resultat) == 0:
        print("Désolé, je ne connais aucun mot de ta phrase")
        return 
    resultat_final = vectoriser(resultat, vocabulaire_globale)
    return resultat_final


vecteur_user = prompt_user()


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


def intrepreter_commande(distances, dataset, seuil=1.8):
    
    index_du_minimale = np.argmin(distances)
    score = distances[index_du_minimale]
    if np.sum(vecteur_user) < 2:
        print("Erreur, commande trop courte")
        return


    commande_a_executer = dataset[index_du_minimale][1]
    if score <= seuil:
        print(f"La ligne la plus proche se situe à la ligne: {index_du_minimale}, score({score})")
        print("Jarvis a l'intention de", commande_a_executer)
    else: 
        print("Commande introuvable, veuillez ressayer Monsieur ", score)

#Alefa anaty variable vaovao manjary tsy afaka antsoina
if vecteur_user is not None:
    tous_les_scores = calcul_des_distances(vecteur_user, X_train)
    intrepreter_commande(tous_les_scores, dataset_entrainement)
else :
    print("J'attends une commande valide")

