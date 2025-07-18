from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Creates a superuser for the application'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get credentials from environment variables or use defaults
        username = os.getenv('ADMIN_USERNAME', 'admin')
        email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        password = os.getenv('ADMIN_PASSWORD', 'adminpass123')
        
        try:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username, email, password)
                self.stdout.write(
                    f"✓ Admin user '{username}' created successfully"
                )
            else:
                self.stdout.write(
                    f"⚠ Admin user '{username}' already exists"
                )
        except Exception as e:
            self.stdout.write(
                f"✗ Error creating admin user: {str(e)}"
            )
