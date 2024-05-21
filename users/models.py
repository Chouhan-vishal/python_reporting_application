from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, emp_code, email, phone_number, team_name, manager_name,  hierarchy = None, first_name=None, last_name=None, password=None, is_admin=False, admin_user= None):
        """
        Creates and saves a User with the given email, emp_code, phone_number,
        first_name, last_name and password.
        """
        if not email:
            raise ValueError("Users must have an email address")
        if not phone_number:
            raise ValueError("Users must have a phone number")
        if not hierarchy:
            raise ValueError("Users must have a hierarchy")
        if not first_name:
            first_name = ""
        if not last_name:
            last_name = "",

        user = self.model(
            emp_code=emp_code,
            email=email,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            hierarchy=hierarchy,
            admin_user = admin_user,
            team_name = team_name,
            manager_name=manager_name
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone_number, password=None):
        """
        Creates and saves a superuser with the given email, phone_number, and password.
        """
        user = self.create_user(
            email=email,
            phone_number=phone_number,
            is_admin=True
        )
        user.set_password(password)
        user.is_admin = True
        user.save(using=self._db)
        return user

class Hierarchy(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class User(AbstractBaseUser):
    hierarchy = models.ForeignKey(
        Hierarchy,
        related_name='users',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )
    admin_user = models.ForeignKey(
        'self',
        related_name='managed_users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    emp_code = models.CharField(
        null=False,
        verbose_name="employee code",
        max_length=255,
        unique=True,
    )
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        null=False,
    )
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    team_name = models.CharField(max_length=255, null=True)
    manager_name = models.CharField(max_length=255, null=True)
    phone_number = models.CharField(max_length=255, null=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(verbose_name='created at', auto_now_add=True)
    last_login = models.DateTimeField(verbose_name='last login', auto_now=True)
    objects = UserManager()

    USERNAME_FIELD = "email"

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        self.expires_at = timezone.now() + timezone.timedelta(minutes=settings.PASSWORD_RESET_OTP_EXPIRY_MINUTES)
        super().save(*args, **kwargs)
        
    def is_valid(self):
        return self.expires_at > timezone.now()

class TwoFactorAuthentication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='multifactor_auth')
    secret_key = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=False)


def default_permission_set():
    return {
        'sales_summary': False,
        'product_sales_summary': False,
        'sales_collection_outstanding_summary': False,
        'weekly_report': False,
        'collection_report': False,
        'customer_outstanding_details': False,
        'team_product_report': False,
        'salesman_product_report': False,
        'target_achieved_report': False,
        'target_customer_sales_report': False,
        'all_customer_sales_report': False,
        'welding_electrodes_target_achieved_report': False,
        'durastrong_tmt_target_achieved_report': False,
        'product_review': False,
        'salesman_review': False,
        'product_monthly_sales': False,
        'sales_register': False,
        'loyalty_customer': False,
        'block_customer': False,
    }
class ReportPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='report_permissions')
    reports_permission = models.JSONField(dict, default=default_permission_set)
    def __str__(self):
            return str(self.reports_permission)
        
class UserActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    report = models.CharField(max_length=255)
    log = models.TextField()

    def __str__(self):
        return self.report
