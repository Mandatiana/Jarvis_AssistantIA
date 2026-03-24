import os 
import webbrowser
import urllib.parse


from intent_classifier import interpreter_commande
def executer_commande(prediction, phrase_user):
    if prediction == "ouvrir_chrome":
        webbrowser.open("https://www.google.com")
        print("J'ai ouvert chrome pour vous")
    
    elif prediction == 'play_song':
        verbes_musique = ["jouer","lancer", "chanson", "morceau", "playlist", "musique", "lancer","mettre","mets","diffuser","ecouter"]
        recherche = [m for m in phrase_user if m not in verbes_musique]

        #Espace dans le titre
        requete = " ".join(recherche)
        if requete:
            print(f"Recherche de {requete} sur Youtube")

            #transformer les espaces en %20 ou +
            query_encode = urllib.parse.quote(requete)
            webbrowser.open(f"https://www.google.com/search?q={query_encode}+youtube&btnI")
        else:
            print("Quel musique veux tu ecouter? ")

