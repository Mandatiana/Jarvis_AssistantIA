import os 
import webbrowser
import urllib.parse


from intent_classifier import interpreter_commande

# Recuperer input user et commande demandé venant de la classification
#Pour eviter qu il execute une deuxieme fois
if __name__ == "__main__":
    resulat_knn, phrase_user = interpreter_commande()


def executer_commande(prediction):
    if prediction == "ouvrir_chrome":
        webbrowser.open("https://www.google.com")
        print("J'ai ouvert chrome pour vous")
        
executer_commande(resulat_knn)

    
def lancer_musique(prediction, phrase_brute):
    if prediction == 'play_song':
        verbes_musique = ["jouer","lancer", "chanson", "morceau", "playlist", "musique", "lancer","mettre","mets","diffuser","ecouter"]
        recherche = [m for m in phrase_brute if m not in verbes_musique]

        #Espace dans le titre
        requete = " ".join(recherche)
        if requete:
            print(f"Recherche de {requete} sur Youtube")

            #transforme les espaces en %20 ou +
            query_encode = urllib.parse.quote(requete)
            webbrowser.open(f"https://www.google.com/search?q={query_encode}+youtube&btnI")
        else:
            print("Quel musique veux tu ecouter? ")


lancer_musique(resulat_knn,phrase_user)