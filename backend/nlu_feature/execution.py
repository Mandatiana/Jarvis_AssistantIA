import os 
import webbrowser

from intent_classifier import interpreter_commande
resultat_knn = interpreter_commande()


def executer_commande(prediction):
    if prediction == "ouvrir_chrome":
        webbrowser.open("https://www.google.com")
        print("J'ai ouvert chrome pour vous")
        
executer_commande(resultat_knn)