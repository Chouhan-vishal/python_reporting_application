from rest_framework import serializers
from .models import User, Hierarchy, TwoFactorAuthentication, ReportPermission
from django.db import transaction





class HierarchySerializer(serializers.ModelSerializer):
    class Meta:
        model = Hierarchy
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    hierarchy = HierarchySerializer(read_only=True)
    role = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'is_active', 'is_admin', 'created_at', 'last_login',
                  'email', 'hierarchy', "role", 'first_name', 'last_name', 'phone_number']
        read_only_fields = ['created_at', 'last_login']

    def create(self, validated_data):
        with transaction.atomic():
            role = validated_data.pop('role', None)
            hierarchy_obj = Hierarchy.objects.filter(name=role).first()
            is_admin = validated_data.get('is_admin', False)            
            if not hierarchy_obj:
                raise serializers.ValidationError(f"No hierarchy found for role '{role}'")
            validated_data['hierarchy'] = hierarchy_obj
            user = User.objects.create_user(**validated_data)
            if user.is_admin:
                TwoFactorAuthentication.objects.create(user=user)
            ReportPermission.objects.create(user=user)
            return user

    def update(self, instance, validated_data):
        with transaction.atomic():
            hierarchy_name = validated_data.pop('hierarchy', None)
            if hierarchy_name:
                hierarchy_obj = Hierarchy.objects.filter(name=hierarchy_name)
                if hierarchy_obj is None:
                    raise serializers.ValidationError(f'hierarchy with name {hierarchy_name} does not exist ')
                else:
                    instance.hierarchy = hierarchy_obj
            instance.username = validated_data.get('username', instance.username)
            instance.email = validated_data.get('email', instance.email)
            instance.first_name = validated_data.get('first_name', instance.first_name)
            instance.last_name = validated_data.get('last_name', instance.last_name)
            instance.phone_number = validated_data.get('phone_number', instance.phone_number)
            instance.is_active = validated_data.get('is_active', instance.is_active)
            instance.is_admin = validated_data.get('is_admin', instance.is_admin)
            instance.save()
            return instance


