from django.http import HttpResponse
from django.contrib.auth import logout
from django.shortcuts import render, redirect

def index(request):
    return render(request, "notes_app/home.html")

def logout_view(request):
    logout(request)
    return redirect("") #go back to home page
