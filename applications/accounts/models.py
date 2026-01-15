from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager cho User model"""

    def create_user(self, email, password=None, **extra_fields):
        """Tạo user thường"""
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Tạo superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User Model - sử dụng email thay vì username"""

    class Role(models.TextChoices):
        """Phân quyền người dùng"""
        USER = 'user', 'User'
        STAFF = 'staff', 'Staff'  # Chỉ xem & export
        ANALYST = 'analyst', 'Analyst'  # Xem thống kê, export
        ADMIN = 'admin', 'Admin'  # Full quyền

    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name='Email'
    )
    username = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Username'
    )
    first_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='First Name'
    )
    last_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Last Name'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        verbose_name='Role'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Staff Status'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Trả về họ tên đầy đủ"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    def is_admin(self):
        return self.role == self.Role.ADMIN

    def is_analyst(self):
        return self.role in [self.Role.ANALYST, self.Role.ADMIN]

    def is_staff_member(self):
        return self.role in [self.Role.STAFF, self.Role.ANALYST, self.Role.ADMIN]