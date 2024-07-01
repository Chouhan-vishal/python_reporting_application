from .models import  User
from django.contrib import admin

# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'emp_code', 'full_name', 'email', 'phone_number','team_name', 'manager_name', 'is_active', 'is_admin', 'last_login', 'created_at']
