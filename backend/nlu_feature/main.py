import os
import sys
from pathlib import Path 
from preprocessing import nettoyer_phrase
from intent_classifier import interpreter_commande
from execution import executer_commande
from preprocessing import nettoyer_phrase


BASE_DIR = Path(__file__).resolve().parent.parent
chemin_services = BASE_DIR / "Jarvis" / "services"

sys.path.append(str(chemin_services))
from AskJarvis import ask_jarvis # type: ignore


def main():
    print("SYSTEME JARVIS ACTIVÉ")
    while True:
        try:
            resultat = interpreter_commande()
            if resultat:
                resulat_knn, phrase_user = resultat

            #Verifier si le KNN a compris la commande
            if resulat_knn is not None:
                executer_commande(resulat_knn, phrase_user)

            else:

                #Le KNN n'as pas compris
                print("Laissez-moi reflechir deux secondes...")
                
                if ask_jarvis:
                     
                     #Recoller si on a une liste pour l'envoyer a l'api
                     phrase = " ".join(phrase_user) if isinstance(phrase_user,list) else phrase_user
                     reponse_jarvis = ask_jarvis(phrase)
                     
                     if reponse_jarvis:
                          print(f"Jarvis: {reponse_jarvis}")

                else: 
                     print("Désolé, je ne connais pas la reponse à votre question.")
                     
        except KeyboardInterrupt:
            print("Jarvis mise en veille. À bientôt !")
            break
        except Exception as e:
            print(f"Une erreur est surveue",e)

if __name__ == "__main__":
        main()