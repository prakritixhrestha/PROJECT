from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Profile

class Command(BaseCommand):
    help = 'Ensures admin user exists with correct credentials'

    def handle(self, *args, **kwargs):
        username = 'furniquette'
        password = 'furniqqqqqqq'
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS(f'User "{username}" already exists'))
            
            # Update password to ensure it's correct
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated user "{username}" credentials and permissions'))
            
        except User.DoesNotExist:
            # Create the user
            user = User.objects.create_superuser(
                username=username,
                email='admin@furniq.com',
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Created superuser "{username}"'))
        
        # Ensure profile exists
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'phone_number': '9800000000',
                'is_approved': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created profile for "{username}"'))
        else:
            profile.is_approved = True
            profile.save()
            self.stdout.write(self.style.SUCCESS(f'Profile for "{username}" already exists'))
        
        self.stdout.write(self.style.SUCCESS('Admin user setup complete!'))
