import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def envoyer_mail(destinaire_email, corps_message):

    username = "apikey"  # On ne change jamais ce mot
    password = os.getenv("KEY_MAIL")

    message = MIMEMultipart()
    message["From"] = "aaronrmjk@gmail.com" # Ton adresse vérifiée
    message["To"] = destinaire_email
    message["Subject"] = "Message de l'assistant JARVIS"

    # On nettoie le message pour enlever les accolades {' '} du terminal
    contenu_propre = str(corps_message).replace('{', '').replace('}', '').replace("'", "")
    message.attach(MIMEText(contenu_propre, "plain"))

    try:
        print(f"Jarvis : Connexion au serveur sécurisé...")
        with smtplib.SMTP("smtp.sendgrid.net", 587) as serveur:
            serveur.starttls()
            serveur.login(username, password)
            serveur.send_message(message)
            print("Jarvis : Monsieur, le mail a été envoyé avec succès !")
            return True
    except Exception as e:
        print(f"[ERREUR] Impossible d'envoyer le mail : {e}")
        return False