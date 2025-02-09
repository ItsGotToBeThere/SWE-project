from django.http import HttpResponse

def index(request):
    return HttpResponse("Basic Django Page :)")