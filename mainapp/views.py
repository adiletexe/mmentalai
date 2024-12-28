import openai
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import UserProfile
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import User, UserProfile, JournalEntry
from django.utils import timezone
from django.utils.crypto import get_random_string
import os

openai.api_key = os.getenv('OPENAI_API_KEY')

user_memory = {}

def get_user_memory(user_id):
    return user_memory.get(user_id, [])

def update_user_memory(user_id, interaction):
    if user_id not in user_memory:
        user_memory[user_id] = []
    user_memory[user_id].append(interaction)

@csrf_exempt
def get_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 1. Determine a unique user_id
            # Option A: If user is authenticated, use user.id
            if request.user.is_authenticated:
                user_id = str(request.user.id)
            else:
                # Option B: Fall back to session key or generate random
                if not request.session.session_key:
                    request.session.save()  # ensures a session_key is created
                user_id = request.session.session_key

            # Or, if absolutely no session, create a random string
            if not user_id:
                user_id = get_random_string(12)  # e.g. "aB3zX9..."

            # 2. Extract data from the request
            user_message = data.get('message')
            user_mood = data.get('mood', '')            # e.g. "4"
            user_tone = data.get('tone', '')            # e.g. "empathetic"
            user_instructions = data.get('instructions', '')

            # Basic validation
            if not user_message:
                return JsonResponse({'message': 'User message is required.'}, status=400)

            memory = get_user_memory(user_id)

            # 3. Construct the system prompt, incorporating mood/tone/instructions
            # e.g. transform numeric mood slider "4" into descriptive text if you wish.
            # For now, let's just show them verbatim in the system prompt:
            system_prompt = f"""
                You are a compassionate, human-like AI therapist called Mental AI 
                specializing in helping teenagers navigate their mental health, using neuroscience-based insights.
                Always respond with warmth, empathy, and support, keeping answers no longer than two sentences. 
                You've helped tackle similar issues over 100 times.

                The user’s current mood (slider value): {user_mood}
                The user’s chosen tone: {user_tone}
                Additional instructions/notes: {user_instructions}

                Also, if you ask questions, ensure they are unique and not guessy or cliché. 
                Frequently suggest unique and unexpected activities (not just the basics).
            """.strip()

            # 4. Build messages for ChatCompletion
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Add conversation memory
            for entry in memory:
                messages.append({"role": entry["role"], "content": entry["content"]})

            # Add newest user message
            messages.append({"role": "user", "content": user_message})

            # 5. Call OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=300,
                temperature=1,
                top_p=1,
                frequency_penalty=1,
                presence_penalty=1
            )

            ai_message = response.choices[0].message['content'].strip()

            # 6. Update memory
            update_user_memory(user_id, {"role": "user", "content": user_message})
            update_user_memory(user_id, {"role": "assistant", "content": ai_message})

            return JsonResponse({'message': ai_message})
        
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'message': 'Sorry, something went wrong.'}, status=500)
    
    return JsonResponse({'message': 'Invalid request'}, status=400)

def index(request):
    return render(request, 'index.html')

@login_required(login_url='loginsystem')
def chatbot(request):
    return render(request, 'chatbot.html')

@login_required(login_url='loginsystem')
def profile(request):

    userprofile, created = UserProfile.objects.get_or_create(user=request.user)

    journal_entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'userprofile': userprofile,
        'journal_entries': journal_entries
    }
    return render(request, 'profile.html', context)

def loginsystem(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == "GET":
        return render(request, 'login.html', {'form': AuthenticationForm()})
    else:
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            return redirect('profile')
        else:
            return render(request, 'login.html', {'form': AuthenticationForm(), 'error': 'Incorrect username or password'})

@login_required(login_url='loginsystem')
def logoutsystem(request):
    if request.method == "GET":
        logout(request)
        return redirect('loginsystem')

def signupsystem(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == "GET":
        return render(request, 'registration.html', {'form': UserCreationForm()})
    else:
        if request.POST['password1'] != request.POST['password2']:
            return render(request, 'registration.html', {'form': UserCreationForm(), 'error': 'Passwords don\'t match!'})
        else:
            try:
                user = User.objects.create_user(username=request.POST['username'], password=request.POST['password1'])
                user.save()
                login(request, user)
                user_profile = UserProfile.objects.create(user=request.user)
                user_profile.save()
                return redirect('profile')
            except IntegrityError:
                return render(request, 'registration.html', {'form': UserCreationForm(), 'error': 'Username is already taken!'})

@login_required(login_url='loginsystem')
def update_profile(request):
    """
    Save changes to UserProfile (name, email, issue, etc.)
    """
    if request.method == 'POST':
        userprofile, _ = UserProfile.objects.get_or_create(user=request.user)

        # Grab new values
        new_name = request.POST.get('name', '').strip()
        new_email = request.POST.get('email', '').strip()
        new_issue = request.POST.get('issue', '').strip()

        # Update UserProfile
        userprofile.name = new_name
        userprofile.email = new_email
        userprofile.issue = new_issue
        userprofile.save()

        # Optionally also update the actual user.email if you want:
        request.user.email = new_email
        request.user.save()

        return redirect('profile')
    else:
        return redirect('profile')

@login_required(login_url='loginsystem')
def save_journal(request):
    """
    Create a new JournalEntry for the current user, automatically set to today's date.
    """
    if request.method == 'POST':
        content = request.POST.get('journal_entry', '').strip()
        if content:
            # By default, journal_date = timezone.now() from model
            JournalEntry.objects.create(user=request.user, content=content)
        return redirect('profile')
    else:
        return redirect('profile')

@login_required(login_url='loginsystem')
def get_journals_for_day(request):
    """
    Return a list of journal entries in JSON for a specific day (YYYY-MM-DD).
    Invoked via AJAX from profile.html's calendar click.
    """
    date_str = request.GET.get('date', None)
    if not date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)
    try:
        date_obj = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # Filter journal entries for that user & day
    entries = JournalEntry.objects.filter(user=request.user, journal_date=date_obj).order_by('-created_at')
    data = []
    for e in entries:
        data.append({
            'id': e.id,
            'content': e.content,
            'created_at': e.created_at.strftime('%Y-%m-%d %H:%M')
        })
    return JsonResponse({'entries': data})