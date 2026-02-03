import re
from django.db import models
from django.contrib.auth.models import User #built-in system for staff
from django.utils import timezone
from datetime import timedelta

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, unique=True)
    is_approved = models.BooleanField(default=False) # For staff approval
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number} ({'Approved' if self.is_approved else 'Pending'})"

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Processing', 'Processing'),
        ('Ready', 'Ready for Delivery'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Delayed', 'Delayed'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    items_summary = models.TextField() #stores cart detail
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(default=timezone.now() + timedelta(days=3))
    status = models.CharField(max_length=20, default='Pending', choices=STATUS_CHOICES)
    payment_method = models.CharField(max_length=20, default='COD', choices=[('eSewa', 'eSewa'), ('Khalti', 'Khalti'), ('COD', 'Cash on Delivery')])
    payment_status = models.CharField(max_length=20, default='Pending')
    
    # Delivery Information
    delivery_address = models.TextField(blank=True, null=True)
    delivery_phone = models.CharField(max_length=15, blank=True, null=True)
    delivery_instructions = models.TextField(blank=True, null=True)
    
    # Tracking
    tracking_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    estimated_delivery_date = models.DateTimeField(blank=True, null=True)
    
    assigned_staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_staff': True},
        related_name='staff_orders'
    )
    
    def save(self, *args, **kwargs):
        # Generate tracking number if not exists
        if not self.tracking_number:
            import uuid
            self.tracking_number = f"FNQ-{uuid.uuid4().hex[:8].upper()}"
        
        # Set estimated delivery date if not set
        if not self.estimated_delivery_date:
            self.estimated_delivery_date = timezone.now() + timedelta(days=5)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order #{self.id} - {self.tracking_number} by {self.customer.username}"

class OrderStatusHistory(models.Model):
    """Track all status changes for orders"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = 'Order Status Histories'
    
    def __str__(self):
        return f"Order #{self.order.id}: {self.old_status} → {self.new_status}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Bedroom', 'Bedroom'),
        ('Living Room', 'Living Room'),
        ('Dining', 'Dining'),
    ]
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.IntegerField(default=0)
    
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Living Room')
    
    assigned_staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_staff': True}
    )
    
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False, verbose_name='Popular (Best Seller)')
    is_special_offer = models.BooleanField(default=False, verbose_name='Special Offer')
    available_for_order = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, verbose_name='Active (Show on website)')
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.category}"

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('eSewa', 'eSewa'),
        ('Khalti', 'Khalti'),
        ('COD', 'Cash on Delivery'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    response_data = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.payment_method} - {self.amount} - {self.status}"

class Address(models.Model):
    """User saved addresses for delivery"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, default='Home')  # Home, Office, etc.
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.label} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        # If this is set as default, unset all other defaults for this user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class Subscriber(models.Model):
    """Newsletter subscribers"""
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.email

class ShipmentTracking(models.Model):
    """Nepal Post shipment tracking for orders"""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='nepal_post_tracking')
    nepal_post_tracking_number = models.CharField(max_length=20, unique=True)  # NP-XXXXXXXXXX
    current_location = models.CharField(max_length=200, default='Processing')
    current_status = models.CharField(max_length=50, default='Package Received')
    last_update = models.DateTimeField(auto_now=True)
    tracking_history = models.JSONField(default=list)  # List of tracking events
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Nepal Post Tracking'
        verbose_name_plural = 'Nepal Post Trackings'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nepal_post_tracking_number} - {self.order.tracking_number}"
    
    def add_tracking_event(self, location, status, description):
        """Add a new tracking event to history"""
        from django.utils import timezone
        event = {
            'timestamp': timezone.now().isoformat(),
            'location': location,
            'status': status,
            'description': description
        }
        if not isinstance(self.tracking_history, list):
            self.tracking_history = []
        self.tracking_history.append(event)
        self.current_location = location
        self.current_status = status
        self.save()
    
    @staticmethod
    def generate_tracking_number():
        """Generate unique Nepal Post tracking number"""
        import random
        import string
        while True:
            number = 'NP-' + ''.join(random.choices(string.digits, k=10))
            if not ShipmentTracking.objects.filter(nepal_post_tracking_number=number).exists():
                return number

class SavedItem(models.Model):
    """User saved/wishlist items"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-saved_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class WebsiteContent(models.Model):
    """Dynamically manage website global content"""
    # Header & Footer
    header_title = models.CharField(max_length=100, default='FurniQ')
    footer_text = models.TextField(default='Premium Furniture for your home.')
    footer_address = models.CharField(max_length=255, default='Kathmandu, Nepal')
    contact_email = models.EmailField(default='info@furniq.com')
    contact_phone = models.CharField(max_length=20, default='+977 12345678')
    
    # Featured Image
    featured_title = models.CharField(max_length=200, default='Lush Collection 2026')
    featured_subtitle = models.CharField(max_length=200, default='Discover the Art of Living')
    featured_image = models.ImageField(upload_to='site_assets/', null=True, blank=True)
    
    # About Page
    about_title = models.CharField(max_length=100, default='Our Story')
    about_content = models.TextField(default='We craft furniture with love and precision.')
    about_image = models.ImageField(upload_to='site_assets/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Website Content Settings ({self.created_at})"
