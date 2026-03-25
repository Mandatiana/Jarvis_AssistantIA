import os 
import webbrowser
import urllib.parse
from gerer_contact import charger_contact
from mail_service import envoyer_mail
from audio_service import jouer_audio_aleatoire



def executer_commande(prediction, phrase_user):
    if prediction == "ouvrir_chrome":
        webbrowser.open("https://www.google.com")
        jouer_audio_aleatoire("chrome")

    elif prediction == "envoyer_mail":

        jouer_audio_aleatoire("filler")

        #preparation 
        destinataire = None
        message = None
        index_a = -1

        #Recuperer le nom du destinataire de l'email
        if "à" in phrase_user:
            index_a = phrase_user.index("à")
        elif "a" in phrase_user:
            index_a = phrase_user.index("a")
        
        if index_a != -1 and  index_a+1 < len(phrase_user):
            destinataire = phrase_user[index_a+1]
            print(f"Préparation du mail pour {destinataire}...")

        #Corps du message apres le "pour"
        if "pour" in phrase_user:
                index_pour = phrase_user.index("pour")
                message = " ".join(phrase_user[index_pour + 1:])
                print(f"Message à envoyé", {message})
        else:
            print("Quel est le contenu du mail? ")

        if destinataire and message:
                #Chercher dans les contacts
                repertoire = charger_contact('dataset.csv')  
                email_cible = repertoire.get(destinataire.lower())

                if email_cible: 
                    print(f"J'ai trouvé l'email de {destinataire}: {email_cible}")
                    succes = envoyer_mail(email_cible, message)

                    if succes:
                        print("Jarvis: Monsieur, le mail a été envoyé avec succès")
                        jouer_audio_aleatoire("mail")
                    else: 
                        print("Une erreur est survenue")
                        jouer_audio_aleatoire("confused")

            
    
    if prediction == 'play_song':
        verbes_musique = ["jouer","lancer", "chanson", "morceau", "playlist", "musique", "lancer","mettre","mets","diffuser","ecouter"]
        recherche = [m for m in phrase_user if m not in verbes_musique]
        jouer_audio_aleatoire("music")
        #Espace dans le titre
        requete = " ".join(recherche)
        if requete:
            print(f"Recherche de {requete} sur Youtube")

            #transformer les espaces en %20 ou +
            query_encode = urllib.parse.quote(requete)
            webbrowser.open(f"https://www.google.com/search?q={query_encode}+youtube&btnI")
        else:
            print("Quel musique veux tu ecouter? ")
    
    elif prediction == "presentation_jarvis":
        jouer_audio_aleatoire("intro", "intro 1.wav")


