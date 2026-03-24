from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import Jarvis.state as state
import os

def Hello(request):
    return HttpResponse("Let's goo")

def AskJarvis(request):
    return HttpResponse("Ask Jarvis")

IA_TXT_PATH = os.path.join(
    os.path.dirname(__file__),
    "services", "reponse_ia", "ia.txt"
)

@csrf_exempt
def LireIA(request):
    with open(IA_TXT_PATH, "r", encoding="utf-8") as f:
        state.derniere_reponse_ia = f.read().strip()

    print("[IA]", state.derniere_reponse_ia)

    async_to_sync(get_channel_layer().group_send)(
        "tts_user1",
        {"type": "tts.speak", "tau": 0.8, "speed": 1.0}
    )

    return JsonResponse({"response": state.derniere_reponse_ia})


@csrf_exempt  
def VerifierIA(request):
    with open(IA_TXT_PATH, "rb") as f:
        raw = f.read()
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        texte = raw.decode("utf-16")
    else:
        texte = raw.decode("utf-8")
    texte = texte.strip()
    return JsonResponse({"has_content": bool(texte), "response": texte})

@csrf_exempt
def Vider_ia(request):
    with open(IA_TXT_PATH, "w", encoding="utf-8") as f:
        f.write("")
    return JsonResponse({"status": "cleared"})