from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib.auth.models import User
from inventory.models import Product, Profile, Order, Notification, Payment, OrderStatusHistory, Address, Subscriber, WebsiteContent

# Access Decorators
def is_admin(user):
    return user.is_authenticated and user.is_staff

class AdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        # Admin is staff + (is_superuser or is_approved)
        u = self.request.user
        if not u.is_authenticated or not u.is_staff:
            return False
        if u.is_superuser:
            return True
        return hasattr(u, 'profile') and u.profile.is_approved
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['unread_count'] = Notification.objects.filter(is_read=False).count()
        return ctx

# 0. Auth & Dashboard
def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin-custom:dashboard')
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user and user.is_staff:
            if not user.is_superuser:
                # Check staff approval
                if not hasattr(user, 'profile') or not user.profile.is_approved:
                    messages.error(request, 'Your staff account is pending admin approval.')
                    return redirect('admin-custom:login')
            
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('admin-custom:dashboard')
        messages.error(request, 'Invalid admin credentials')
    return render(request, 'custom_admin/login.html')

@login_required
@user_passes_test(is_admin)
def admin_logout(request):
    logout(request)
    return redirect('admin-custom:login')

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    # Sales trend
    today = timezone.now().date()
    yesterday = today - timezone.timedelta(days=1)
    labels = []
    sales = []
    for i in range(6, -1, -1):
        date = today - timezone.timedelta(days=i)
        labels.append(date.strftime('%b %d')) 
        rev = Order.objects.filter(payment_status='Completed', order_date__date=date).aggregate(Sum('total_price'))['total_price__sum'] or 0
        sales.append(float(rev))

    # Revenue Today vs Yesterday for progress
    rev_today = Order.objects.filter(payment_status='Completed', order_date__date=today).aggregate(Sum('total_price'))['total_price__sum'] or 0
    rev_yesterday = Order.objects.filter(payment_status='Completed', order_date__date=yesterday).aggregate(Sum('total_price'))['total_price__sum'] or 0
    rev_progress = 100 if rev_yesterday == 0 else min(100, int((rev_today / rev_yesterday) * 100))

    # Stats for Admin layout
    total_sales_count = Order.objects.count()
    pending_payments_count = Order.objects.filter(payment_status='Pending').count()
    daily_sales_target = 500  # Mock target for UI
    sales_progress = min(100, int((total_sales_count / daily_sales_target) * 100))

    # Team Members (Latest Profiles)
    team_members = Profile.objects.select_related('user').order_by('-user__date_joined')[:4]

    # Order Activity Counts (Grouping confirmed/shipped/delivered as Completed)
    pending_count = Order.objects.filter(status='Pending').count()
    cancelled_count = Order.objects.filter(status='Cancelled').count()
    completed_count = Order.objects.exclude(status__in=['Pending', 'Cancelled']).count()
    
    # Success Rate (Completed / Total)
    total_orders_count = Order.objects.count()
    success_rate = min(100, int((completed_count / total_orders_count) * 100)) if total_orders_count > 0 else 0

    context = {
        'total_revenue': float(Order.objects.filter(payment_status='Completed').aggregate(Sum('total_price'))['total_price__sum'] or 0),
        'total_orders': total_sales_count,
        'pending_payments': pending_payments_count,
        'total_products': Product.objects.count(),
        'total_users': User.objects.count(),
        'recent_orders': Order.objects.select_related('customer').order_by('-order_date')[:5],
        # Adminto Chart Data
        'chart_labels': labels,
        'chart_sales': sales,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'cancelled_count': cancelled_count,
        'success_rate': success_rate,
        'rev_progress': rev_progress,
        'sales_progress': sales_progress,
        'team_members': team_members,
        'unread_count': Notification.objects.filter(is_read=False).count(),
    }
    return render(request, 'custom_admin/dashboard.html', context)

# 1. Orders
class OrderListView(AdminMixin, ListView):
    model = Order
    template_name = 'custom_admin/orders.html'
    context_object_name = 'orders'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_count'] = Order.objects.count()
        ctx['new_orders'] = Order.objects.filter(status='Pending').count()
        return ctx

class OrderUpdateView(AdminMixin, UpdateView):
    model = Order
    fields = ['status', 'payment_status']
    template_name = 'custom_admin/order_form.html'
    success_url = reverse_lazy('admin-custom:orders-list')

    def form_valid(self, form):
        # Record history if status changed
        old_order = Order.objects.get(pk=self.object.pk)
        new_status = form.cleaned_data['status']
        new_payment_status = form.cleaned_data['payment_status']
        
        if old_order.status != new_status:
            OrderStatusHistory.objects.create(
                order=self.object,
                old_status=old_order.status,
                new_status=new_status,
                changed_by=self.request.user
            )
            
            # Notify Customer
            Notification.objects.create(
                user=self.object.customer,
                message=f"Your Order #{self.object.tracking_number} status has been updated to: {new_status}."
            )

        # Sync Payment Model if payment status updated to Completed
        if old_order.payment_status != new_payment_status:
            # Update or create Payment record
            payment, created = Payment.objects.get_or_create(
                order=self.object,
                defaults={
                    'payment_method': self.object.payment_method,
                    'amount': self.object.total_price,
                    'status': new_payment_status
                }
            )
            if not created:
                payment.status = new_payment_status
                payment.save()

        return super().form_valid(form)


@login_required
@user_passes_test(is_admin)
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        old_status = order.status
        new_status = request.POST.get('status')
        
        if old_status != new_status:
            order.status = new_status
            order.save()
            
            # Record change in history
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user
            )
            
            # Notify Customer
            Notification.objects.create(
                user=order.customer,
                message=f"Your Order #{order.tracking_number} status has been updated to: {new_status}."
            )

            
            messages.success(request, f'Order #{pk} status updated to {new_status}')
    return redirect('admin-custom:orders-list')

@login_required
@user_passes_test(is_admin)
def export_orders_csv(request):
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="furniq_orders_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Tracking Number', 'Customer', 'Email', 'Items Summary', 'Total Price', 'Status', 'Date', 'Delivery Phone', 'Delivery Address'])

    orders = Order.objects.select_related('customer').all().order_by('-order_date')
    for o in orders:
        writer.writerow([
            o.id,
            o.tracking_number,
            o.customer.username,
            o.customer.email,
            o.items_summary,
            o.total_price,
            o.status,
            o.order_date.strftime('%Y-%m-%d %H:%M'),
            o.delivery_phone,
            o.delivery_address
        ])

    return response

# 2. Products
class ProductListView(AdminMixin, ListView):
    model = Product
    template_name = 'custom_admin/products.html'
    context_object_name = 'products'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_count'] = Product.objects.filter(is_active=True).count()
        ctx['out_of_stock'] = Product.objects.filter(stock=0).count()
        return ctx

class ProductCreateView(AdminMixin, CreateView):
    model = Product
    fields = ['name', 'category', 'price', 'stock', 'image', 'is_active', 'description']
    template_name = 'custom_admin/product_form.html'
    success_url = reverse_lazy('admin-custom:products-list')

class ProductUpdateView(AdminMixin, UpdateView):
    model = Product
    fields = ['name', 'category', 'price', 'stock', 'image', 'is_active', 'description']
    template_name = 'custom_admin/product_form.html'
    success_url = reverse_lazy('admin-custom:products-list')

@login_required
@user_passes_test(is_admin)
def toggle_product_active(request, pk):
    p = get_object_or_404(Product, pk=pk)
    p.is_active = not p.is_active
    p.save()
    return redirect('admin-custom:products-list')

# 3. Profiles
class ProfileListView(AdminMixin, ListView):
    model = Profile
    template_name = 'custom_admin/profiles.html'
    context_object_name = 'profiles'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_profiles'] = Profile.objects.count()
        ctx['pending_approval'] = Profile.objects.filter(is_approved=False).count()
        return ctx

@login_required
@user_passes_test(is_admin)
def approve_profile(request, pk):
    p = get_object_or_404(Profile, pk=pk)
    p.is_approved = True
    p.save()
    
    # Notify User
    Notification.objects.create(
        user=p.user,
        message="Your account has been approved! You can now access all features."
    )
    
    messages.success(request, f'Profile for {p.user.username} approved')
    return redirect('admin-custom:profiles-list')


@login_required
@user_passes_test(is_admin)
def reject_profile(request, pk):
    p = get_object_or_404(Profile, pk=pk)
    p.is_approved = False
    p.save()
    messages.warning(request, f'Profile for {p.user.username} rejected')
    return redirect('admin-custom:profiles-list')

# 4. Users
class UserListView(AdminMixin, ListView):
    model = User
    template_name = 'custom_admin/users.html'
    context_object_name = 'users'

class UserCreateView(AdminMixin, CreateView):
    model = User
    fields = ['username', 'email', 'password', 'first_name', 'last_name', 'is_staff']
    template_name = 'custom_admin/user_form.html'
    success_url = reverse_lazy('admin-custom:users-list')
    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        return super().form_valid(form)

class UserUpdateView(AdminMixin, UpdateView):
    model = User
    fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    template_name = 'custom_admin/user_form.html'
    success_url = reverse_lazy('admin-custom:users-list')

class UserDeleteView(AdminMixin, DeleteView):
    model = User
    template_name = 'custom_admin/user_confirm_delete.html'
    success_url = reverse_lazy('admin-custom:users-list')

@login_required
@user_passes_test(is_admin)
def toggle_staff_status(request, pk):
    u = get_object_or_404(User, pk=pk)
    if u == request.user:
        messages.error(request, "You cannot change your own staff status.")
        return redirect('admin-custom:users-list')
        
    u.is_staff = not u.is_staff
    u.save()
    status = "enabled" if u.is_staff else "disabled"
    messages.success(request, f"Staff status for {u.username} has been {status}.")
    return redirect('admin-custom:users-list')

# 5. Payments
class PaymentListView(AdminMixin, ListView):
    model = Order
    template_name = 'custom_admin/payments.html'
    context_object_name = 'orders'
    ordering = ['-order_date']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_rev'] = Order.objects.filter(payment_status='Completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
        ctx['pending_pay'] = Order.objects.filter(payment_status='Pending').count()
        return ctx

# 6. Order History
class OrderHistoryListView(AdminMixin, ListView):
    model = OrderStatusHistory
    template_name = 'custom_admin/order_history.html'
    context_object_name = 'history'

# 7. Notifications
class NotificationListView(AdminMixin, ListView):
    model = Notification
    template_name = 'custom_admin/notifications.html'
    context_object_name = 'notifications'

@login_required
@user_passes_test(is_admin)
def mark_notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk)
    n.is_read = True
    n.save()
    return redirect('admin-custom:notifications-list')

@login_required
@user_passes_test(is_admin)
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('admin-custom:notifications-list')


# 8. Subscribers
class SubscriberListView(AdminMixin, ListView):
    model = Subscriber
    template_name = 'custom_admin/subscribers.html'
    context_object_name = 'subscribers'

# 9. Address
class AddressListView(AdminMixin, ListView):
    model = Address
    template_name = 'custom_admin/addresses.html'
    context_object_name = 'addresses'

# 10. Website Content Settings
@login_required
@user_passes_test(is_admin)
def website_settings(request):
    content, created = WebsiteContent.objects.get_or_create(id=1)
    if request.method == 'POST':
        content.header_title = request.POST.get('header_title', content.header_title)
        content.footer_text = request.POST.get('footer_text', content.footer_text)
        content.footer_address = request.POST.get('footer_address', content.footer_address)
        content.contact_email = request.POST.get('contact_email', content.contact_email)
        content.contact_phone = request.POST.get('contact_phone', content.contact_phone)
        content.featured_title = request.POST.get('featured_title', content.featured_title)
        content.featured_subtitle = request.POST.get('featured_subtitle', content.featured_subtitle)
        content.about_title = request.POST.get('about_title', content.about_title)
        content.about_content = request.POST.get('about_content', content.about_content)
        
        if 'featured_image' in request.FILES:
            content.featured_image = request.FILES['featured_image']
        if 'about_image' in request.FILES:
            content.about_image = request.FILES['about_image']
            
        content.save()
        messages.success(request, "Website content updated successfully!")
        return redirect('admin-custom:website-settings')
        
    return render(request, 'custom_admin/website_settings.html', {'content': content})
