import os 
import webbrowser
import urllib.parse
from gerer_contact import charger_contact
import smtplib
from mail_service import envoyer_mail



from intent_classifier import interpreter_commande
def executer_commande(prediction, phrase_user):
    if prediction == "ouvrir_chrome":
        webbrowser.open("https://www.google.com")
        print("J'ai ouvert chrome pour vous")

    elif prediction == "envoyer_mail":

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
                    else: 
                        print("Une erreur est survenue")

            
        
    else:
        print("Je n'ai pas compris à qui envoyer le mail")
    
    if prediction == 'play_song':
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
    
    elif prediction == "presentation_jarvis":
        print(f"Jarvis: "f"{phrase_user}")


