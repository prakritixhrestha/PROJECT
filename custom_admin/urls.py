from django.urls import path
from . import views

app_name = 'admin-custom'

urlpatterns = [
    # Auth
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    
    # 1. Orders
    path('orders/', views.OrderListView.as_view(), name='orders-list'),
    path('orders/export-csv/', views.export_orders_csv, name='orders-export-csv'),
    path('orders/<int:pk>/edit/', views.OrderUpdateView.as_view(), name='orders-edit'),
    path('orders/<int:pk>/status/', views.update_order_status, name='orders-status-update'),
    
    # 2. Products
    path('products/', views.ProductListView.as_view(), name='products-list'),
    path('products/add/', views.ProductCreateView.as_view(), name='products-add'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='products-edit'),
    path('products/<int:pk>/toggle/', views.toggle_product_active, name='products-toggle'),
    
    # 3. Profiles
    path('profiles/', views.ProfileListView.as_view(), name='profiles-list'),
    path('profiles/<int:pk>/approve/', views.approve_profile, name='profiles-approve'),
    path('profiles/<int:pk>/reject/', views.reject_profile, name='profiles-reject'),
    
    # 4. Users
    path('users/', views.UserListView.as_view(), name='users-list'),
    path('users/add/', views.UserCreateView.as_view(), name='users-add'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='users-edit'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='users-delete'),
    path('users/<int:pk>/staff-toggle/', views.toggle_staff_status, name='users-staff-toggle'),
    
    # 5. Payments
    path('payments/', views.PaymentListView.as_view(), name='payments-list'),
    
    # 6. Order History
    path('order-history/', views.OrderHistoryListView.as_view(), name='order-history'),
    
    # 7. Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notifications-list'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='notifications-read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='notifications-read-all'),

    
    # 8. Subscribers
    path('subscribers/', views.SubscriberListView.as_view(), name='subscribers-list'),
    
    # 9. Address
    path('addresses/', views.AddressListView.as_view(), name='addresses-list'),
    
    # 10. Website Settings
    path('website-settings/', views.website_settings, name='website-settings'),
]
