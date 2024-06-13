from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, emp_code, email, phone_number, is_active=True, team_name=None, manager_name = None,  hierarchy = None, full_name=None, password=None, is_admin=False, admin_user= None):
        """
        Creates and saves a User with the given email, emp_code, phone_number,
        full_name and password.
        """
        if not email:
            raise ValueError("Users must have an email address")
        if not phone_number:
            raise ValueError("Users must have a phone number")
        if not hierarchy:
            raise ValueError("Users must have a hierarchy")
        if not full_name:
            full_name = ""

        user = self.model(
            emp_code=emp_code,
            email=email,
            phone_number=phone_number,
            full_name=full_name,
            is_active=is_active,
            is_admin=is_admin,
            hierarchy=hierarchy,
            admin_user = admin_user,
            team_name = team_name,
            manager_name=manager_name
        )

        user.set_password(password)
        user.save(using=self._db)
        def manager_permission_set():
            return {
                "sales_summary": False,
                "product_wise_sales_summary": False,
                "sales_collection_outstanding": False,
                "weekly_summary": False,
                "collection": False,
                "customer_wise_outstanding": False,
                "cr_utilization": False,
                "team_and_product_wise": False,
                "salesman_and_product_wise": False,
                "target_and_achieved": False,
                "target_customer_sales": False,
                "all_customers_sales": False,
                "welding_electrode": False,
                "durastrong_tmt_product_sales": False,
                "review_product_wise": False,
                "sales_register": False,
                "product_wise_month_sales": False,
                "block_customers_list": False,
            }
        def salesman_permission_set():
            return { 
                "sales_collection_outstanding": False,
                "weekly_summary": False,
                "collection": False,
                "customer_wise_outstanding": False,
                "cr_utilization" : False,
                "salesman_and_product_wise": False,
                "target_and_achieved": False,
                "target_customer_sales": False,
                "all_customers_sales": False
                }
        if hierarchy.name == 'manager':
            report_permission = ReportPermission.objects.create(reports_permission=manager_permission_set())
        elif hierarchy.name == 'salesman':
            report_permission = ReportPermission.objects.create(reports_permission=salesman_permission_set())
        else:
            report_permission = ReportPermission.objects.create()

        user.permitted_reports = report_permission
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
        null=True,
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
    full_name = models.CharField(max_length=255, null=True)
    team_name = models.CharField(max_length=255, null=True, blank=True)
    manager_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    permitted_reports = models.OneToOneField('ReportPermission', on_delete=models.CASCADE, null=True, blank=True)
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
class ReportPermission(models.Model):
    reports_permission = models.JSONField(null=True)
    def __str__(self):
            return str(self.reports_permission)
        
class UserActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    report = models.CharField(max_length=255)
    log = models.TextField()

    def __str__(self):
        return self.report
