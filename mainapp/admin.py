from django.contrib import admin
from .models import UserProfile, JournalEntry

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(JournalEntry)