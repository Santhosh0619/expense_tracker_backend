import json
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token

def me(request):
    if request.user.is_authenticated:
        return JsonResponse({'username': request.user.username})
    return JsonResponse({'username': None}, status=401)

@csrf_exempt
def register(request):
    if request.method != 'POST':
        return JsonResponse({'error':'POST only'}, status=405)
    data = json.loads(request.body.decode())
    username = data.get('username'); email = data.get('email'); password = data.get('password')
    if not all([username, email, password]):
        return JsonResponse({'error':'Missing fields'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error':'Username taken'}, status=400)
    user = User.objects.create_user(username=username, email=email, password=password)
    return JsonResponse({'message':'Registered successfully'})

@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({'error':'POST only'}, status=405)
    # ensure CSRF cookie exists for frontend
    get_token(request)
    data = json.loads(request.body.decode())
    user = authenticate(request, username=data.get('username'), password=data.get('password'))
    if user:
        login(request, user)
        return JsonResponse({'message':'Logged in'})
    return JsonResponse({'error':'Invalid credentials'}, status=400)

def logout_view(request):
    logout(request)
    return JsonResponse({'message':'Logged out'})
