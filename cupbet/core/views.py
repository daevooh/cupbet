from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from .models import Team, Match, Bet, BetClaim
import json
import requests
from decimal import Decimal
from django.conf import settings

def home(request):
    """Home page with tournament info and upcoming matches"""
    # Get current time
    now = timezone.now()
    
    # Upcoming matches: future matches that are active for betting
    upcoming_matches = Match.objects.filter(
        start_time__gte=now,
        is_active=True
    ).order_by('start_time')[:10]  # Show next 10 matches
    
    # Recent matches: past matches (regardless of active status)
    recent_matches = Match.objects.filter(
        start_time__lt=now
    ).order_by('-start_time')[:5]  # Show last 5 completed matches
    
    context = {
        'upcoming_matches': upcoming_matches,
        'recent_matches': recent_matches,
        'total_teams': Team.objects.count(),
        'total_matches': Match.objects.count(),
    }
    return render(request, 'core/home.html', context)

def check_bet(request):
    """Check bet status by bet code"""
    bet = None
    error_message = None
    
    if request.method == 'POST':
        bet_code = request.POST.get('bet_code', '').strip()
        if bet_code:
            try:
                bet = Bet.objects.get(bet_code=bet_code.upper())
            except Bet.DoesNotExist:
                error_message = "Bet code not found. Please check and try again."
        else:
            error_message = "Please enter a bet code."
    
    context = {
        'bet': bet,
        'error_message': error_message,
    }
    return render(request, 'core/check_bet.html', context)

def get_paystack_banks(request):
    url = "https://api.paystack.co/bank?currency=NGN"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if response.status_code == 200 and data.get('status'):
            banks = data['data']
            seen = set()
            unique_banks = []
            for bank in banks:
                bank_name = bank.get('name')
                bank_code = bank.get('code')
                if bank_name and bank_name not in seen:
                    seen.add(bank_name)
                    unique_banks.append({
                        'name': bank_name,
                        'code': bank_code
                    })
            return JsonResponse({'success':True, 'banks':unique_banks})
        else:
            return JsonResponse({'success': False, 'message': 'Failed to fetch from Paystack'})
    except Exception as e:
        return JsonResponse({'success':False, 'message':str(e)})

def intiate_paystack_transfer(account_number, bank_code, amount, name):
    PAYSTACK_SECRET_KEY = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
    if not PAYSTACK_SECRET_KEY:
        return False, 'Paystack secret key not configured.'
    # 1. Create transfer recipient
    recipient_url = 'https://api.paystack.co/transferrecipient'
    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    recipient_data = {
        'type': 'nuban',
        'name': name,
        'account_number': account_number,
        'bank_code': bank_code,
        'currency': 'NGN',
    }
    resp = requests.post(recipient_url, json=recipient_data, headers=headers)
    resp_data = resp.json()
    if not resp_data.get('status'):
        return False, resp_data.get('message', 'Failed to create recipient')
    recipient_code = resp_data['data']['recipient_code']

    # 2. Initiate transfer
    transfer_url = 'https://api.paystack.co/transfer'
    transfer_data = {
        'source': 'balance',
        'amount': int(amount * 100),  # Paystack expects amount in kobo
        'recipient': recipient_code,
        'reason': 'IWEHA Cup Bet Payout',
    }
    resp = requests.post(transfer_url, json=transfer_data, headers=headers)
    resp_data = resp.json()
    if not resp_data.get('status'):
        return False, resp_data.get('message', 'Failed to initiate transfer')
    return True, resp_data['data']
@csrf_exempt
def get_bank_name_from_code(bank_code):
    """Get bank name from bank code using cached bank data"""
    # Cache bank data to avoid repeated API calls
    if not hasattr(get_bank_name_from_code, '_bank_cache'):
        get_bank_name_from_code._bank_cache = {}
        try:
            url = "https://api.paystack.co/bank?currency=NGN"
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            response = requests.get(url, headers=headers)
            data = response.json()
            if response.status_code == 200 and data.get('status'):
                for bank in data['data']:
                    get_bank_name_from_code._bank_cache[bank.get('code')] = bank.get('name')
        except:
            pass
    
    return get_bank_name_from_code._bank_cache.get(bank_code, f"Bank {bank_code}")

def resolve_account_name(request):
    account_number = request.GET.get('account_number')
    bank_code = request.GET.get('bank_code')

    url = f"https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if response.status_code == 200 and data.get('status'):
            return JsonResponse({'success': True, 'account_name': data['data']['account_name']})
        else:
            return JsonResponse({'success': False, 'message': data.get('message', 'Unable to resolve account')})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def claim_payout(request):
    """Claim payout for winning bets"""
    bet_code_value = request.GET.get('bet_code') or request.POST.get('bet_code', '').strip()
    error_message = None
    success_message = None
    bet = None

    if request.method == 'POST':
        account_number = request.POST.get('account_number', '').strip()
        account_name = request.POST.get('account_name', '').strip()  # Optional
        bank_code = request.POST.get('bank_code', '').strip()
        bet_code = bet_code_value.upper() if bet_code_value else ''
        
        if not all([bet_code, account_number, bank_code]): #banl_code>> taking that out for nw 
            error_message = "Please fill in all required fields."
        else:
            try:
                bet = Bet.objects.get(bet_code=bet_code)

                if not bet.is_winner:
                    error_message = "This bet is not a winning bet."
                elif bet.is_paid_out:
                    error_message = "This bet has already been paid out."
                elif BetClaim.objects.filter(bet=bet).exists():
                    error_message = "Payout has already been claimed for this bet."
                elif bet.payout <= 0:
                    error_message = "No payout available for this bet."
                else:
                    # Get bank name from the bank code
                    bank_name = get_bank_name_from_code(bank_code)
                    
                    # Save the claim manually instead of sending to Paystack
                    BetClaim.objects.create(
                        bet=bet,
                        account_number=account_number,
                        account_name=account_name,
                        bank_name=bank_name,
                        bank_code=bank_code,
                        payout_amount=bet.payout
                    )
                    success_message = f"Payout of ₦{bet.payout} has been claimed. Your details will be verified and processed."
            except Bet.DoesNotExist:
                error_message = "Bet code not found. Please check and try again."
    else:
        # GET request: show bet details if bet_code is provided
        if bet_code_value:
            bet = Bet.objects.filter(bet_code=bet_code_value.upper()).first()
            if not bet:
                error_message = "Bet not found or invalid bet code."

    context = {
        'bet': bet,
        'bet_code_value': bet_code_value,
        'error_message': error_message,
        'success_message': success_message,
    }
    return render(request, 'core/claim_payout.html', context)

def payment_success(request):
    """Handle successful payment and show bet code"""
    if request.method == 'POST':
        # Handle payment success from Paystack
        try:
            data = json.loads(request.body)
            paystack_reference = data.get('paystack_reference')
            bettor_name = data.get('bettor_name')
            bettor_email = data.get('bettor_email', '').strip()  # Handle empty email
            match_id = data.get('match_id')
            amount = data.get('amount')
            bet_choice = data.get('bet_choice')
            
            # Validate required fields
            if not all([bettor_name, match_id, amount, bet_choice]):
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required fields'
                })
            
            # Create the bet
            match = Match.objects.get(id=match_id)
            
            # Handle empty email - set to None if empty
            if not bettor_email:
                bettor_email = None
                
            bet = Bet.objects.create(
                bettor_name=bettor_name,
                bettor_email=bettor_email,
                match=match,
                bet_choice=bet_choice,
                amount=amount,
                paystack_reference=paystack_reference
            )
            
            return JsonResponse({
                'success': True,
                'bet_code': bet.bet_code
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    # GET request - show bet details
    bet_code = request.GET.get('bet_code')
    bet = None
    
    if bet_code:
        try:
            bet = Bet.objects.get(bet_code=bet_code)
        except Bet.DoesNotExist:
            pass
    
    context = {
        'bet': bet,
    }
    return render(request, 'core/payment_success.html', context)

@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook for payment verification"""
    if request.method == 'POST':
        try:
            # Get the webhook data
            webhook_data = json.loads(request.body)
            
            # Verify the webhook signature (TODO: implement proper verification)
            
            # Extract payment details
            reference = webhook_data.get('data', {}).get('reference')
            status = webhook_data.get('data', {}).get('status')
            
            if status == 'success' and reference:
                # Find the bet with this reference
                try:
                    bet = Bet.objects.get(paystack_reference=reference)
                    
                    # Update bet status
                    bet.is_winner = False  # Will be updated when match result is set
                    bet.save()
                    
                    return HttpResponse(status=200)
                except Bet.DoesNotExist:
                    return HttpResponse(status=404)
            
        except json.JSONDecodeError:
            return HttpResponse(status=400)
    
    return HttpResponse(status=405)

