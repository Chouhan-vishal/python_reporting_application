from django.contrib import admin

from .models import  User
# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'emp_code', 'first_name', 'last_name', 'email', 'phone_number','team_name', 'manager_name', 'is_active', 'is_admin', 'last_login', 'created_at']


