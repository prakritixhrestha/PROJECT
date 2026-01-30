from django.urls import path
from . import views

urlpatterns = [
    path('user/', views.user, name='user'),
    path('', views.home, name='home'), #customer homepage
    path('list/', views.product_list, name='product_list'), # for staffs
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff-orders/', views.staff_orders, name='staff_orders'),
    
    # Admin Dashboard (Superuser Only)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    
    # Staff Panel Actions
    path('staff/update-order/<int:order_id>/', views.staff_update_order, name='staff_update_order'),
 
    path('login/', views.user, name='user'),
    path('register/', views.register, name='register'),
    path('logout/', views.signout, name='logout'),
    
    path('bedroom/', views.bedroom, name='bedroom'),
    path('livingroom/', views.livingroom, name='livingroom'),
    path('dining/', views.dining, name='dining'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('search/', views.search_results, name='search_results'),
    path('update-stock/<int:product_id>/', views.update_stock, name='update_stock'),
    path('place-order/',views.place_order, name='place_order'),
    path('mark-notifications-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('esewa-callback/', views.esewa_callback, name='esewa_callback'),
    path('khalti-verify/', views.khalti_verify, name='khalti_verify'),
    path('payment-success/', views.payment_success, name='payment_success'),
    
    # Order Tracking
    path('track-order/', views.order_tracking, name='order_tracking'),
    path('my-orders/', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    
    # User Profile & Account
    path('profile/', views.profile, name='profile'),
    path('saved-items/', views.saved_items, name='saved_items'),
    path('saved-addresses/', views.saved_addresses, name='saved_addresses'),
    path('account-settings/', views.account_settings, name='account_settings'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Content Pages
    path('about/', views.about, name='about'),
    path('gallery/', views.gallery, name='gallery'),
    
    # Nepal Post Tracking
    path('nepal-post-track/', views.nepal_post_tracking, name='nepal_post_tracking'),
    path('add-tracking-event/<int:tracking_id>/', views.add_tracking_event, name='add_tracking_event'),
    path('subscribe/', views.subscribe, name='subscribe'),
]

