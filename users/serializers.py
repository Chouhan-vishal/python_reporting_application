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
    password = serializers.CharField(write_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    reports_permission = serializers.JSONField(required=False)

    class Meta:
        model = User
        fields = ['id', 'emp_code', 'full_name', 'team_name', 'manager_name', 'password', 'is_active', 'is_admin', 'created_at', 'last_login',
                  'email', 'hierarchy', "role", 'phone_number', 'reports_permission']
        read_only_fields = ['created_at', 'last_login']

    def create(self, validated_data):
        with transaction.atomic():
            role = validated_data.pop('role', None)
            hierarchy_obj = Hierarchy.objects.filter(name=role).first()
            reports_permission = validated_data.pop('reports_permission', None)
            is_admin = validated_data.get('is_admin', False)            
            if not hierarchy_obj:
                raise serializers.ValidationError(f"No hierarchy found for role '{role}'")
            validated_data['hierarchy'] = hierarchy_obj
            user = User.objects.create_user(**validated_data)
            if user.is_admin:
                TwoFactorAuthentication.objects.create(user=user)
            if reports_permission:
                report_permission_obj = ReportPermission.objects.filter(user=user).first()
                report_permission_obj.reports_permission.update(reports_permission)
                report_permission_obj.save()
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
            instance.emp_code = validated_data.get('emp_code', instance.emp_code)
            instance.email = validated_data.get('email', instance.email)
            instance.full_name = validated_data.get('full_name', instance.full_name)
            instance.team_name = validated_data.get('team_name', instance.team_name)
            instance.manager_name = validated_data.get('team_name', instance.manager_name)
            instance.phone_number = validated_data.get('phone_number', instance.phone_number)
            instance.is_active = validated_data.get('is_active', instance.is_active)
            instance.is_admin = validated_data.get('is_admin', instance.is_admin)
            reports_permission = validated_data.pop('reports_permission', None)
            if reports_permission is not None:
                if hasattr(instance, 'report_permissions'):
                    instance.report_permissions.reports_permission.update(reports_permission)
                    instance.report_permissions.save()
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
            user_representation = {
                'id': user_representation.get('id'),
                'emp_code': user_representation.get('emp'),
                'full_name': user_representation.get('full_name'),
                'email': user_representation.get('email'),
                'team_name': user_representation.get('team_name'),
                'manager_name': user_representation.get('manager_name')
            }
            representation['user'] = user_representation
        return representation
    
class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, data):
        """
        Check if email and password are provided.
        """
        email = data.get('email')
        password = data.get('password')
        if not (email and password):
            raise serializers.ValidationError("email and password are required")
        return data
    
class TwoFactorAuthenticationSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, max_length=6)
    secret_key = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, data):
        """
        Validate the input data.
        """
        otp = data.get('otp')
        secret_key = data.get('secret_key')
        email = data.get('email')
        password = data.get('password')
        if not otp.isdigit() or len(otp) != 6:
            raise serializers.ValidationError("Invalid OTP format. OTP must be a 6-digit number.")

        return data


class UserSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=255)

    def validate_query(self, value):
        if not value:
            raise serializers.ValidationError("Query cannot be empty.")
        return value