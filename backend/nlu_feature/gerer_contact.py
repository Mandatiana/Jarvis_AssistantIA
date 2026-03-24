import json


def charger_contact(contact):
    try:
        with open ('contact.json', 'r', encoding='utf-8') as f:
            repertoire = json.load(f)
        return repertoire
    except FileNotFoundError as e:
        print("Erreur lors de du chargement du fichier")
        return {}
    
