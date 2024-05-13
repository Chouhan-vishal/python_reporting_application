from rest_framework import serializers
from .models import User, Hierarchy, TwoFactorAuthentication, ReportPermission, UserActivityLog
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
        fields = ['id', 'username', 'first_name', 'last_name', 'team_name', 'manager_name', 'is_active', 'is_admin', 'created_at', 'last_login',
                  'email', 'hierarchy', "role", 'phone_number']
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
            instance.team_name = validated_data.get('team_name', instance.team_name)
            instance.manager_name = validated_data.get('team_name', instance.manager_name)
            instance.last_name = validated_data.get('last_name', instance.last_name)
            instance.phone_number = validated_data.get('phone_number', instance.phone_number)
            instance.is_active = validated_data.get('is_active', instance.is_active)
            instance.is_admin = validated_data.get('is_admin', instance.is_admin)
            instance.save()
            return instance



class UserActivityLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = UserActivityLog
        fields = ['id', 'created_at', 'report', 'log', 'user']
        

    def to_representation(self, instance):
        """
        Custom representation of UserActivityLog instance
        """
        representation = super().to_representation(instance)
        user_representation = representation.get('user')
        if user_representation:
            # Filter the fields you want to return from the nested UserSerializer
            user_representation = {
                'id': user_representation.get('id'),
                'username': user_representation.get('username'),
                'team_name': user_representation.get('team_name'),
                'manager_name': user_representation.get('manager_name')
            }
            representation['user'] = user_representation
        return representation
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, data):
        """
        Check if username and password are provided.
        """
        username = data.get('username')
        password = data.get('password')
        if not (username and password):
            raise serializers.ValidationError("Username and password are required")
        return data
    
class TwoFactorAuthenticationSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, max_length=6)
    secret_key = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, data):
        """
        Validate the input data.
        """
        otp = data.get('otp')
        secret_key = data.get('secret_key')
        username = data.get('username')
        password = data.get('password')

        # Your validation logic here
        # For example, you can check if the OTP is a 6-digit number
        if not otp.isdigit() or len(otp) != 6:
            raise serializers.ValidationError("Invalid OTP format. OTP must be a 6-digit number.")

        # Additional validation logic can be added as needed

        return data
