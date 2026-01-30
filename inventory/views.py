import json
import re
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required #This gives access to staffs only
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User, Group
from .models import Product, Profile, Order, Notification, OrderStatusHistory, Address, SavedItem, Subscriber, ShipmentTracking, WebsiteContent
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
# This part gets your data from your database and sends to the screen.

#Customer homepage
def home(request):
    products = Product.objects.filter(is_featured=True)[:6]
    site_content = WebsiteContent.objects.first()
    return render(request, 'inventory/index.html', {
        'products': products,
        'content': site_content
    })

def bedroom(request):
    products = Product.objects.filter(category='Bedroom')
    return render(request, 'inventory/bedroom.html', {'products': products})

def livingroom(request):
    products = Product.objects.filter(category='Living Room')
    return render(request, 'inventory/livingroom.html', {'products': products})

def dining(request):
    products = Product.objects.filter(category='Dining')
    return render(request, 'inventory/dining.html',{'products':products})




def user(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        role = request.POST.get('role')
        
        user_obj = authenticate(request, username=u, password=p)
        
        if user_obj is not None:
            # Check if user is superuser (admin)
            if user_obj.is_superuser:
                # Create profile if missing for superusers
                if not hasattr(user_obj, 'profile'):
                    Profile.objects.create(user=user_obj, phone_number=f"{user_obj.id}0000000000"[:15], is_approved=True)
                
                login(request, user_obj)
                messages.success(request, f"Welcome back, Admin {user_obj.get_full_name() or user_obj.username}!")
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('admin-custom:dashboard')
            
            # Check if user is staff (but not superuser)
            elif user_obj.is_staff:
                # Check directly if profile exists to avoid RelatedObjectDoesNotExist exception
                if hasattr(user_obj, 'profile'):
                    if not user_obj.profile.is_approved:
                        messages.error(request, "Your account is pending admin approval.")
                        return redirect('user')
                else:
                    # Create profile if missing
                    Profile.objects.create(user=user_obj, phone_number=f"{user_obj.id}0000000000"[:15], is_approved=True)
                
                login(request, user_obj)
                messages.success(request, f"Welcome, {user_obj.get_full_name() or user_obj.username}!")
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('staff_dashboard')
            
            # Regular customer
            else:
                login(request, user_obj)
                messages.success(request, f"Welcome back, {user_obj.get_full_name() or user_obj.username}!")
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('home')
        else:
            messages.error(request, "Invalid username or password!")
    return render(request, 'inventory/user.html')
    
def signout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('user')

def register(request):
    if request.method == 'POST':
        full_name = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone') # This captures the country code + number
        role = request.POST.get('role')

        if User.objects.filter(username=email).exists():
            messages.error(request, "This email is already registered.")
            return redirect('register')
            
        if Profile.objects.filter(phone_number=phone).exists():
            messages.error(request, "This phone number is already registered.")
            return redirect('register')

        # 1. Create the User (visible in Admin)
        user = User.objects.create_user(
            username=email, 
            email=email, 
            password=password,
            first_name=full_name
        )
        
        # 2. Assign Staff Role
        is_approved = True
        if role == 'staff':
            user.is_staff = True
            user.save()
            is_approved = False # Staff requires approval

        # 3. Create the Profile
        Profile.objects.create(user=user, phone_number=phone, is_approved=is_approved)

        if role == 'staff':
            # Notify Super Admins
            superadmins = User.objects.filter(is_superuser=True)
            for sa in superadmins:
                Notification.objects.create(
                    user=sa,
                    message=f"New staff registration: {full_name} ({email}). Approval required."
                )
            messages.info(request, "Account created! Please wait for admin approval before logging in.")
            return redirect('user')

        else:
            login(request, user) # Auto-login for customers
            messages.success(request, f"Welcome {full_name}! Your FurniQ account is ready.")
            return redirect('home') 

    return render(request, 'register.html') # Ensure this path matches your folder
    
def search_results(request):
    query = request.GET.get('q')
    if query:
        results = Product.objects.filter(name__icontains=query)
    else:
        results = Product.objects.none()
    return render(request, 'inventory/search_results.html', {
        'results': results,
        'query': query
    })

#for staffs
@login_required (login_url='user') #This "locks" the page


def mark_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
@login_required(login_url='user')
def staff_orders(request):
    return redirect('profile')

from .payment_gateway import EsewaGateway, KhaltiGateway
from .models import Payment

@csrf_exempt
def place_order(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Please login to place an order.'}, status=401)
        
        try:
            data = json.loads(request.body)
            items_summary = data.get('items')
            total_price = float(data.get('total'))
            payment_method = data.get('payment_method', 'COD')
            
            # Get delivery details
            delivery_address = data.get('delivery_address', '')
            delivery_phone = data.get('delivery_phone', '')
            delivery_instructions = data.get('delivery_instructions', '')
            delivery_date = data.get('delivery_date', None)
            
            # Use atomic transaction to ensure data integrity
            from django.db import transaction
            
            with transaction.atomic():
                # 1. Validate Stock first
                cart_items = data.get('cart_items', [])
                items_to_update = []
                
                # 1. Decrement Stock & Validate Products
                # We do this FIRST or inside the transaction to ensure we don't create an order for out-of-stock items
                
                # Create Order with delivery details
                new_order = Order.objects.create(
                    customer=request.user,
                    items_summary=items_summary,
                    total_price=total_price,
                    status='Pending',
                    payment_method=payment_method,
                    payment_status='Pending',
                    delivery_address=delivery_address,
                    delivery_phone=delivery_phone,
                    delivery_instructions=delivery_instructions
                )
                
                # Set delivery date if provided
                if delivery_date:
                    from datetime import datetime
                    new_order.estimated_delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d')
                    new_order.save()
            
                cart_items = data.get('cart_items', [])
                for item in cart_items:
                    product_name = item.get('name', '').strip()
                    quantity = int(item.get('qty', 0))
                    
                    # Find product strictly
                    product = Product.objects.filter(name__iexact=product_name).select_for_update().first()
                    
                    if not product:
                        # Product not found - Rollback and error
                        raise Exception(f"Product '{product_name}' not found. It may have been removed.")
                        
                    if product.stock < quantity:
                        # Insufficient stock - Rollback and error
                        raise Exception(f"Insufficient stock for {product.name}. Available: {product.stock}")
                    
                    # Decrement stock
                    product.stock -= quantity
                    product.save()
                
                # 2. Save Address for User (Auto-save)
                if request.user.is_authenticated and delivery_address:
                    # Check if this exact address already exists to avoid duplicates
                    address_exists = Address.objects.filter(
                        user=request.user,
                        address_line1=delivery_address.split(',')[0], # Basic check on first part
                        city__icontains=delivery_address.split(',')[1].strip() if ',' in delivery_address else ''
                    ).exists()
                    
                    if not address_exists:
                        Address.objects.create(
                            user=request.user,
                            label='Delivery',
                            full_name=request.user.get_full_name(),
                            phone=delivery_phone,
                            address_line1=delivery_address, # Storing full string for now as logic in checkout constructs it
                            city='-', # Already included in address_line1 in this simplistic setup
                            state='-', 
                            is_default=False
                        )

                # Create Notification for the user
                Notification.objects.create(
                    user=request.user,
                    message=f"Order #{new_order.tracking_number} placed successfully! Status: Pending."
                )
                
                # Create Notification for Admins/Staff (Optional: but good for visibility)
                admins = User.objects.filter(is_staff=True)
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        message=f"ACTION REQUIRED: Pending Order #{new_order.tracking_number} - Deliver to {new_order.delivery_address}."
                    )
            
            # Transaction Committed Successfully - Proceed to Payment Gateway
            
            # Handle Payment Methods
            if payment_method == 'eSewa':
                esewa = EsewaGateway()
                success_url = request.build_absolute_uri('/esewa-callback/')
                failure_url = request.build_absolute_uri('/esewa-callback/?status=failed')
                payment_data = esewa.get_payment_data(new_order.id, total_price, success_url, failure_url)
                return JsonResponse({
                    'status': 'success',
                    'order_id': new_order.id,
                    'payment_method': 'eSewa',
                    'payment_data': payment_data
                })
                
            elif payment_method == 'Khalti':
                khalti = KhaltiGateway()
                return_url = request.build_absolute_uri('/khalti-verify/')
                
                init_response = khalti.initiate_payment(new_order.id, total_price, return_url)
                
                if 'pidx' in init_response and not init_response.get('error'):
                    return JsonResponse({
                        'status': 'success', 
                        'order_id': new_order.id,
                        'payment_method': 'Khalti',
                        'payment_url': init_response['payment_url'],
                        'pidx': init_response['pidx']
                    })
                else:
                    # Note: Order is already created. For real-world, might want to set status to 'Payment Failed'
                    return JsonResponse({'status': 'error', 'message': 'Khalti initiation failed', 'debug': init_response}, status=400)

            else: # COD
                return JsonResponse({
                    'status': 'success', 
                    'order_id': new_order.id, 
                    'tracking_number': new_order.tracking_number,
                    'payment_method': 'COD'
                })
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@csrf_exempt
def esewa_callback(request):
    """
    Handle eSewa payment callback
    eSewa redirects here after payment with GET parameters
    """
    # Check if this is a failure callback
    if request.GET.get('status') == 'failed':
        return render(request, 'inventory/payment_failed.html', {'message': 'eSewa Payment Failed or Cancelled'})
    
    # Get parameters from eSewa callback
    transaction_uuid = request.GET.get('transaction_uuid')
    
    if not transaction_uuid:
        return render(request, 'inventory/payment_failed.html', {'message': 'Invalid callback data'})
    
    try:
        # Extract order ID from transaction UUID (format: orderid-randomhash)
        order_id = transaction_uuid.split('-')[0]
        order = Order.objects.get(id=order_id)
        
        # Verify payment with eSewa
        esewa = EsewaGateway()
        verification = esewa.verify_payment(
            product_code='EPAYTEST',
            total_amount=str(int(order.total_price)),
            transaction_uuid=transaction_uuid
        )
        
        if verification.get('success'):
            # Payment verified successfully
            order.payment_status = 'Completed'
            order.save()
            
            # Create Payment Record
            Payment.objects.create(
                order=order,
                payment_method='eSewa',
                amount=order.total_price,
                status='Completed',
                transaction_id=verification['data'].get('ref_id', transaction_uuid),
                response_data=json.dumps(verification['data'])
            )
            
            return redirect(f'/payment-success/?order_id={order.id}')
        else:
            return render(request, 'inventory/payment_failed.html', {
                'message': verification.get('message', 'Payment verification failed')
            })
            
    except Order.DoesNotExist:
        return render(request, 'inventory/payment_failed.html', {'message': 'Order not found'})
    except Exception as e:
        return render(request, 'inventory/payment_failed.html', {'message': f'Error: {str(e)}'})

@csrf_exempt
def khalti_verify(request):
    """
    Handle Khalti payment callback and verification
    Khalti redirects here after payment with GET parameters
    """
    pidx = request.GET.get('pidx')
    
    if not pidx:
        return render(request, 'inventory/payment_failed.html', {'message': 'Invalid callback data'})
    
    try:
        # Verify payment with Khalti
        khalti = KhaltiGateway()
        response = khalti.verify_payment(pidx)
        
        # Check for errors
        if response.get('error'):
            return render(request, 'inventory/payment_failed.html', {
                'message': response.get('message', 'Khalti verification failed')
            })
        
        # Check if payment is completed
        if response.get('status') == 'Completed':
            # Get order ID from response
            order_id = response.get('purchase_order_id')
            
            if not order_id:
                return render(request, 'inventory/payment_failed.html', {'message': 'Order ID not found in response'})
            
            try:
                order = Order.objects.get(id=order_id)
                order.payment_status = 'Completed'
                order.save()
                
                # Create Payment Record
                Payment.objects.create(
                    order=order,
                    payment_method='Khalti',
                    amount=order.total_price,
                    status='Completed',
                    transaction_id=response.get('transaction_id', pidx),
                    response_data=json.dumps(response)
                )
                
                return redirect(f'/payment-success/?order_id={order.id}')
                
            except Order.DoesNotExist:
                return render(request, 'inventory/payment_failed.html', {'message': 'Order not found'})
        else:
            return render(request, 'inventory/payment_failed.html', {
                'message': f"Payment status: {response.get('status', 'Unknown')}"
            })
            
    except Exception as e:
        return render(request, 'inventory/payment_failed.html', {'message': f'Error: {str(e)}'})

def payment_success(request):
    order_id = request.GET.get('order_id')
    order = None
    if order_id:
        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            pass
    return render(request, 'inventory/payment_success.html', {'order': order})

@login_required(login_url='user')
def update_stock(request, product_id):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id) # Allow any staff to update
        
        # Check if direct stock update provided
        new_stock = request.POST.get('stock')
        if new_stock is not None:
            try:
                val = int(new_stock)
                if val >= 0:
                    product.stock = val
                    product.save()
                    messages.success(request, f"Stock updated for {product.name}.")
                else:
                    messages.error(request, "Stock cannot be negative.")
            except ValueError:
                messages.error(request, "Invalid stock value.")
        else:
            # Fallback to increment/decrement logic if needed
            action = request.POST.get('action')
            if action == 'increase':
                product.stock += 1
                product.save()
            elif action == 'decrease' and product.stock > 0:
                product.stock -= 1
                product.save()
            
    return redirect('/profile/?tab=inventory')

# ... (Previous code) ...


def cart(request):
    return render(request, 'inventory/cart.html')

@login_required(login_url='user')
def checkout(request):
    """Checkout page with delivery details form"""
    return render(request, 'inventory/checkout.html')

def product_list(request):
    return redirect('profile')

# Order Tracking Views
def order_tracking(request):
    """Customer order tracking page"""
    order = None
    error_message = None
    
    if request.method == 'POST':
        tracking_number = request.POST.get('tracking_number', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        
        if tracking_number and phone_number:
            try:
                # Find order by tracking number and phone
                order = Order.objects.get(
                    tracking_number=tracking_number,
                    delivery_phone=phone_number
                )
                # Get status history
                order.history = order.status_history.all()
            except Order.DoesNotExist:
                error_message = "Order not found. Please check your tracking number and phone number."
        else:
            error_message = "Please provide both tracking number and phone number."
    
    return render(request, 'inventory/order_tracking.html', {
        'order': order,
        'error_message': error_message
    })

@login_required(login_url='user')
def order_history(request):
    """Customer order history page"""
    orders = Order.objects.filter(customer=request.user).order_by('-order_date')
    
    # Add status history to each order
    for order in orders:
        order.history = order.status_history.all()[:3]  # Last 3 status changes
    
    return render(request, 'inventory/order_history.html', {
        'orders': orders
    })

@login_required(login_url='user')
def order_detail(request, order_id):
    """Detailed view of a specific order"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    status_history = order.status_history.all()
    
    return render(request, 'inventory/order_detail.html', {
        'order': order,
        'status_history': status_history
    })

def download_invoice(request, order_id):
    """Generate and download PDF invoice"""
    from .invoice_utils import download_invoice as generate_invoice
    return generate_invoice(request, order_id)

# User Profile & Account Views
@login_required(login_url='user')
def profile(request):
    """User profile page"""
    profile, created = Profile.objects.get_or_create(user=request.user)
    saved_count = SavedItem.objects.filter(user=request.user).count()

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        if first_name:
            request.user.first_name = first_name
        
        if email:
            if email != request.user.email and not User.objects.filter(email=email).exists():
                request.user.email = email
                request.user.username = email
            elif email != request.user.email:
                messages.error(request, "Email already exists.")
        
        request.user.save()
        
        if phone:
            profile.phone_number = phone
            profile.save()
            
        messages.success(request, "Profile updated successfully.")
        return redirect('profile')

    # Check if user is staff (including superuser)
    if request.user.is_staff:
        from django.utils import timezone
        
        # Staff Context
        # Staff Context - Show Pending Orders
        all_pending = Order.objects.filter(status='Pending')
        assigned_count = all_pending.count()
        
        # Tasks Handled by this staff (Any status update they made)
        tasks_handled = OrderStatusHistory.objects.filter(changed_by=request.user).values('order').distinct().count()
        
        recent_tasks = all_pending.order_by('-order_date')
        
        # Activity Log
        activities = OrderStatusHistory.objects.filter(changed_by=request.user).select_related('order').order_by('-changed_at')[:20]
        
        # Inventory List
        products = Product.objects.all().order_by('category', 'name')
        
        active_tab = request.GET.get('tab', 'dashboard')
        
        context = {
            'profile': profile,
            'assigned_count': assigned_count,
            'tasks_handled': tasks_handled,
            'recent_tasks': recent_tasks,
            'activities': activities,
            'products': products,
            'today': timezone.now(),
            'active_tab': active_tab
        }
        return render(request, 'inventory/staff_profile.html', context)
    
    # Customer Context
    return render(request, 'inventory/profile.html', {
        'profile': profile,
        'saved_count': saved_count
    })

@login_required(login_url='user')
def saved_items(request):
    """User saved/wishlist items"""
    saved = SavedItem.objects.filter(user=request.user).select_related('product')
    saved_count = saved.count()
    
    return render(request, 'inventory/saved_items.html', {
        'saved_items': saved,
        'saved_count': saved_count
    })

@login_required(login_url='user')
def saved_addresses(request):
    """Manage saved addresses"""
    addresses = Address.objects.filter(user=request.user)
    saved_count = SavedItem.objects.filter(user=request.user).count()
    
    if request.method == 'POST':
        # Handle address creation/update
        address_id = request.POST.get('address_id')
        if address_id:
            address = get_object_or_404(Address, id=address_id, user=request.user)
        else:
            address = Address(user=request.user)
        
        address.label = request.POST.get('label', 'Home')
        address.full_name = request.POST.get('full_name')
        address.phone = request.POST.get('phone')
        address.address_line1 = request.POST.get('address_line1')
        address.address_line2 = request.POST.get('address_line2', '')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code', '')
        address.is_default = request.POST.get('is_default') == 'on'
        address.save()
        
        messages.success(request, 'Address saved successfully!')
        return redirect('saved_addresses')
    
    return render(request, 'inventory/saved_addresses.html', {
        'addresses': addresses,
        'saved_count': saved_count
    })

@login_required(login_url='user')
def account_settings(request):
    """Account privacy and settings"""
    saved_count = SavedItem.objects.filter(user=request.user).count()
    
    if request.method == 'POST':
        # Handle password change or other settings
        pass
    
    return render(request, 'inventory/account_settings.html', {
        'saved_count': saved_count
    })

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

@login_required(login_url='user')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep the user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            for error in form.errors.values():
                messages.error(request, error)
            return redirect('/profile/?tab=security')
    return redirect('profile')

# Content Pages
def about(request):
    """About Us page"""
    site_content = WebsiteContent.objects.first()
    return render(request, 'inventory/about.html', {'content': site_content})

def help_center(request):
    """Help Center page"""
    return render(request, 'inventory/help_center.html')

def features(request):
    """Features page"""
    return render(request, 'inventory/features.html')

def gallery(request):
    """Gallery page"""
    return render(request, 'inventory/gallery.html')

# Nepal Post Tracking System
def nepal_post_tracking(request):
    """Public Nepal Post tracking page"""
    tracking_result = None
    error_message = None
    
    if request.method == 'POST':
        tracking_number = request.POST.get('tracking_number', '').strip()
        
        if tracking_number:
            try:
                # Try to find by Nepal Post tracking number
                shipment = ShipmentTracking.objects.select_related('order').get(
                    nepal_post_tracking_number=tracking_number
                )
                tracking_result = {
                    'shipment': shipment,
                    'order': shipment.order,
                    'history': reversed(shipment.tracking_history) if shipment.tracking_history else []
                }
            except ShipmentTracking.DoesNotExist:
                # Try to find by FurniQ order tracking number
                try:
                    order = Order.objects.get(tracking_number=tracking_number)
                    if hasattr(order, 'nepal_post_tracking'):
                        shipment = order.nepal_post_tracking
                        tracking_result = {
                            'shipment': shipment,
                            'order': order,
                            'history': reversed(shipment.tracking_history) if shipment.tracking_history else []
                        }
                    else:
                        error_message = "This order has not been assigned to Nepal Post yet."
                except Order.DoesNotExist:
                    error_message = "Tracking number not found. Please check and try again."
        else:
            error_message = "Please enter a tracking number."
    
    return render(request, 'inventory/nepal_post_tracking.html', {
        'tracking_result': tracking_result,
        'error_message': error_message
    })

@login_required(login_url='user')
def add_tracking_event(request, tracking_id):
    """Admin view to add tracking event"""
    if not request.user.is_staff:
        return redirect('home')
    
    shipment = get_object_or_404(ShipmentTracking, id=tracking_id)
    
    if request.method == 'POST':
        location = request.POST.get('location')
        status = request.POST.get('status')
        description = request.POST.get('description')
        
        if location and status and description:
            shipment.add_tracking_event(location, status, description)
            messages.success(request, 'Tracking event added successfully!')
            return redirect('admin:inventory_shipmenttracking_change', shipment.id)
    
    return redirect('admin:inventory_shipmenttracking_changelist')

@login_required(login_url='user')
def staff_dashboard(request):
    """Staff Dashboard - Operational Overview (Redirect to Profile as Unified Dashboard)"""
    return redirect('profile')

@login_required(login_url='user')
def staff_update_order(request, order_id):
    """Granular Order Update View for Staff"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    order = get_object_or_404(Order, id=order_id)
    
    # Safety Check: Allow any staff to update for now to enable "Pick Up" workflow
    # if order.assigned_staff != request.user and not request.user.is_superuser:
    #     messages.error(request, "This task is not assigned to you.")
    #     return redirect('profile')
        
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            
            # Auto-assign if not assigned
            if not order.assigned_staff:
                order.assigned_staff = request.user
            
            order.save()
            
            # Audit Trail
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                notes=notes
            )
            
            messages.success(request, f"Order #{order.tracking_number} updated to {new_status}")
        else:
            messages.error(request, "Invalid status selection.")
            
    return redirect('/profile/?tab=tasks')

# Admin Dashboard View (Superuser Only)
@login_required(login_url='user')
def admin_dashboard(request):
    """Admin Dashboard with Charts and Analytics"""
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admins only.")
        return redirect('home')
    
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Calculate KPIs
    total_revenue = Payment.objects.filter(status='Completed').aggregate(Sum('amount'))['amount__sum'] or 0
    total_orders = Order.objects.count()
    total_users = User.objects.count()
    pending_orders = Order.objects.filter(status='Pending').count()
    total_stock = Product.objects.aggregate(Sum('stock'))['stock__sum'] or 0
    staff_count = User.objects.filter(is_staff=True).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('customer').order_by('-order_date')[:10]
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_users': total_users,
        'pending_orders': pending_orders,
        'total_stock': total_stock,
        'staff_count': staff_count,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'inventory/admin_dashboard.html', context)

# API endpoint for dashboard chart data
@login_required(login_url='user')
def dashboard_stats_api(request):
    """API endpoint to fetch dashboard statistics for charts"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    from django.db.models import Sum, Count
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # 1. Payment trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    payment_data = Payment.objects.filter(
        created_at__gte=thirty_days_ago,
        status='Completed'
    ).extra(
        select={'date': 'DATE(created_at)'}
    ).values('date').annotate(
        total=Sum('amount')
    ).order_by('date')
    
    payment_labels = [item['date'].strftime('%Y-%m-%d') if isinstance(item['date'], datetime) else str(item['date']) for item in payment_data]
    payment_values = [float(item['total']) for item in payment_data]
    
    # 2. Orders per day (last 14 days)
    fourteen_days_ago = timezone.now() - timedelta(days=14)
    order_data = Order.objects.filter(
        order_date__gte=fourteen_days_ago
    ).extra(
        select={'date': 'DATE(order_date)'}
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    order_labels = [item['date'].strftime('%Y-%m-%d') if isinstance(item['date'], datetime) else str(item['date']) for item in order_data]
    order_values = [item['count'] for item in order_data]
    
    # 3. Category vs Stock Levels (Furniture Specific)
    category_data = Product.objects.values('category').annotate(
        total_stock=Sum('stock')
    ).order_by('-total_stock')
    
    category_labels = [item['category'] for item in category_data]
    category_values = [item['total_stock'] for item in category_data]

    # 4. Payment Platform Distribution (eSewa vs Khalti vs COD)
    platform_data = Payment.objects.values('payment_method').annotate(
        count=Count('id')
    ).order_by('count')
    
    platform_labels = [item['payment_method'] for item in platform_data]
    platform_values = [item['count'] for item in platform_data]
    
    # 5. User Growth (Last 60 Days)
    sixty_days_ago = timezone.now() - timedelta(days=60)
    user_data = User.objects.filter(
        date_joined__gte=sixty_days_ago
    ).extra(
        select={'date': 'DATE(date_joined)'}
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    cumulative_count = User.objects.filter(date_joined__lt=sixty_days_ago).count()
    user_labels = []
    user_values = []
    
    for item in user_data:
        cumulative_count += item['count']
        user_labels.append(item['date'].strftime('%Y-%m-%d') if isinstance(item['date'], datetime) else str(item['date']))
        user_values.append(cumulative_count)
    
    return JsonResponse({
        'payment_trends': {
            'labels': payment_labels,
            'data': payment_values
        },
        'orders_per_day': {
            'labels': order_labels,
            'data': order_values
        },
        'category_stock': {
            'labels': category_labels,
            'data': category_values
        },
        'payment_platforms': {
            'labels': platform_labels,
            'data': platform_values
        },
        'user_growth': {
            'labels': user_labels,
            'data': user_values
        }
    })

def subscribe(request):
    """Handle newsletter subscriptions"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            if Subscriber.objects.filter(email=email).exists():
                messages.info(request, "You are already subscribed!")
            else:
                Subscriber.objects.create(email=email)
                messages.success(request, "Thank you for subscribing to our newsletter!")
        else:
            messages.error(request, "Please provide a valid email address.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))
