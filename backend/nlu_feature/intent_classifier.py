import math

from preprocessing import nettoyer_dataset, charger_dataset, nettoyer_phrase

K_value = 3 #Pour l'algo KNN

#on appelle le resulat du chargement des données
contenu = charger_dataset()
data, vocabulaire = nettoyer_dataset(contenu)

# data va contenir les intentions, et vocabluaire les mots uniques

