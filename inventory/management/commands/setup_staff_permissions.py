from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from inventory.models import Product, Order, Payment, Profile, Notification

class Command(BaseCommand):
    help = 'Sets up the Staff group with appropriate permissions'

    def handle(self, *args, **kwargs):
        staff_group, created = Group.objects.get_or_create(name='Staff')
        
        # Define permissions mappings
        # Format: (Model, [list_of_actions])
        permissions_config = [
            (Product, ['add', 'change', 'view']), # Staff can manage products
            (Order, ['view', 'change']),           # Staff can view and update orders (status)
            (Payment, ['view']),                   # Staff can only view payments
            (Profile, ['view']),                   # Staff can view profiles
            (Notification, ['add', 'view']),       # Staff can send notifications
        ]

        permissions_to_add = []
        for model_class, actions in permissions_config:
            content_type = ContentType.objects.get_for_model(model_class)
            for action in actions:
                codename = f'{action}_{model_class._meta.model_name}'
                try:
                    perm = Permission.objects.get(codename=codename, content_type=content_type)
                    permissions_to_add.append(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Permission not found: {codename}'))

        # Also add permission to view users (auth.User)
        user_ctype = ContentType.objects.get(app_label='auth', model='user')
        try:
            view_user = Permission.objects.get(codename='view_user', content_type=user_ctype)
            permissions_to_add.append(view_user)
        except Permission.DoesNotExist:
            pass

        staff_group.permissions.set(permissions_to_add)
        staff_group.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated permissions for group "Staff" with {len(permissions_to_add)} permissions.'))
