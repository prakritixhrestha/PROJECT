from django.core.management.base import BaseCommand
from inventory.models import Product, Order, Subscriber
from django.contrib.auth.models import User
import json

class Command(BaseCommand):
    help = 'Adds sample data to database if tables are empty'

    def handle(self, *args, **kwargs):
        # Check and add sample products if none exist
        if Product.objects.count() == 0:
            self.stdout.write('Adding sample products...')
            
            products_data = [
                {
                    'name': 'Modern Sofa Set',
                    'price': 45000,
                    'old_price': 55000,
                    'stock': 15,
                    'category': 'Living Room',
                    'is_featured': True,
                    'is_popular': True,
                    'description': 'Comfortable modern sofa set for your living room'
                },
                {
                    'name': 'Wooden Dining Table',
                    'price': 35000,
                    'old_price': 42000,
                    'stock': 8,
                    'category': 'Dining',
                    'is_featured': True,
                    'description': 'Elegant wooden dining table for 6 people'
                },
                {
                    'name': 'King Size Bed',
                    'price': 55000,
                    'stock': 12,
                    'category': 'Bedroom',
                    'is_popular': True,
                    'description': 'Luxurious king size bed with storage'
                },
            ]
            
            for product_data in products_data:
                Product.objects.create(**product_data)
            
            self.stdout.write(self.style.SUCCESS(f'Created {len(products_data)} sample products'))
        else:
            self.stdout.write(f'Products already exist ({Product.objects.count()} products)')
        
        # Check and add sample orders if none exist
        if Order.objects.count() == 0:
            self.stdout.write('Adding sample orders...')
            
            # Get admin user
            admin_user = User.objects.filter(is_superuser=True).first()
            
            if admin_user:
                orders_data = [
                    {
                        'customer': admin_user,
                        'items_summary': json.dumps([
                            {'name': 'Modern Sofa Set', 'quantity': 1, 'price': 45000}
                        ]),
                        'total_price': 45000,
                        'status': 'Delivered',
                        'payment_method': 'COD',
                        'payment_status': 'Completed',
                        'delivery_address': 'Kathmandu, Nepal',
                        'delivery_phone': '9800000000'
                    },
                    {
                        'customer': admin_user,
                        'items_summary': json.dumps([
                            {'name': 'Wooden Dining Table', 'quantity': 1, 'price': 35000}
                        ]),
                        'total_price': 35000,
                        'status': 'Processing',
                        'payment_method': 'eSewa',
                        'payment_status': 'Completed',
                        'delivery_address': 'Pokhara, Nepal',
                        'delivery_phone': '9811111111'
                    },
                ]
                
                for order_data in orders_data:
                    Order.objects.create(**order_data)
                
                self.stdout.write(self.style.SUCCESS(f'Created {len(orders_data)} sample orders'))
            else:
                self.stdout.write(self.style.WARNING('No admin user found to create sample orders'))
        else:
            self.stdout.write(f'Orders already exist ({Order.objects.count()} orders)')
        
        self.stdout.write(self.style.SUCCESS('Sample data setup complete!'))
