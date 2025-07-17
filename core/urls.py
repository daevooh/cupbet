from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('check-bet/', views.check_bet, name='check_bet'),
    path('claim-payout/', views.claim_payout, name='claim_payout'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    path('api/bank/', views.get_paystack_banks, name='get_banks'),
    path('resolve-account/', views.resolve_account_name, name='resolve_account_name'),
]