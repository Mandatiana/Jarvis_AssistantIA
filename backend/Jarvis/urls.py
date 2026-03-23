from django.urls import path
from . import views

urlpatterns = [
    path('hello/', views.Hello),
    path('ask/', views.AskJarvis),
    path('lire/', views.LireIA),   # ← ajoute uniquement cette ligne
]