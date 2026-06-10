from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q
import requests
import decimal

from .models import (
    CustomUser, Transaction, Institution,
    ExchangeVendor, VendorRate, Notification
)
from .forms import RegisterForm, SendMoneyForm, RecipientForm
from .view_helpers import (
    user_display_name,
    get_currency_summary,
    get_dashboard_rates,
    get_recent_institution,
)


# ─── Constants ────────────────────────────────────────────────────────────────

SUPPORTED_PAIRS = {
    ('GBP', 'NGN'), ('USD', 'NGN'),
    ('GBP', 'GHS'), ('USD', 'GHS'),
}

FEE_PERCENTAGE  = decimal.Decimal('0.015')   # 1.5% base fee
SHIELD_THRESHOLD = decimal.Decimal('0.02')   # 2% rate change triggers Fair Fee Shield


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_live_rate(from_currency, to_currency):
    """
    Fetch live exchange rate from ExchangeRate-API (free tier).
    Falls back to hardcoded rates for demo if API is unavailable.
    """
    FALLBACK_RATES = {
        ('GBP', 'NGN'): decimal.Decimal('2050.00'),
        ('USD', 'NGN'): decimal.Decimal('1620.00'),
        ('GBP', 'GHS'): decimal.Decimal('18.50'),
        ('USD', 'GHS'): decimal.Decimal('14.80'),
    }
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        rate = data['rates'].get(to_currency)
        if rate:
            return decimal.Decimal(str(rate)), False   # (rate, is_fallback)
    except Exception:
        pass
    return FALLBACK_RATES.get((from_currency, to_currency), decimal.Decimal('1.00')), True


def calculate_fees(amount, fee_type):
    """
    Fee Optimization Engine.
    Returns (total_fee, sender_fee, recipient_fee)
    """
    total_fee = (amount * FEE_PERCENTAGE).quantize(decimal.Decimal('0.01'))

    if fee_type == 'sender':
        return total_fee, total_fee, decimal.Decimal('0.00')
    elif fee_type == 'recipient':
        return total_fee, decimal.Decimal('0.00'), total_fee
    elif fee_type == 'split':
        half = (total_fee / 2).quantize(decimal.Decimal('0.01'))
        return total_fee, half, total_fee - half
    return total_fee, total_fee, decimal.Decimal('0.00')


def check_shield(current_rate, locked_rate):
    """Fair Fee Shield — returns True if rate moved more than threshold."""
    if not locked_rate:
        return False
    change = abs(current_rate - locked_rate) / locked_rate
    return change >= SHIELD_THRESHOLD


# ─── Public Pages ─────────────────────────────────────────────────────────────

def home(request):
    context = {
        'total_transactions': Transaction.objects.filter(status='completed').count(),
        'institutions': Institution.objects.filter(is_verified=True)[:6],
        'vendors': ExchangeVendor.objects.filter(is_verified=True)[:4],
    }
    return render(request, 'home.html', context)


def how_it_works(request):
    return render(request, 'howitworks.html')


def vendor_marketplace(request):
    """Public page — lists all verified exchange vendors and their rates."""
    vendors = ExchangeVendor.objects.filter(is_verified=True).prefetch_related('rates')
    currency_pair = request.GET.get('pair', '')
    if currency_pair:
        vendors = vendors.filter(rates__currency_pair=currency_pair)
    return render(request, 'vendors.html', {'vendors': vendors, 'selected_pair': currency_pair})


def institution_directory(request):
    """Public page — browse verified institutions."""
    institutions = Institution.objects.filter(is_verified=True)
    category = request.GET.get('category', '')
    country  = request.GET.get('country', '')
    if category:
        institutions = institutions.filter(category=category)
    if country:
        institutions = institutions.filter(country=country)
    return render(request, 'institutions.html', {
        'institutions': institutions,
        'selected_category': category,
        'selected_country': country,
    })


def static_page(request, page):
    pages = {
        'about': {
            'page_title': 'About Bridgr',
            'heading': 'About Bridgr',
            'message': 'Bridgr is the most transparent way to send money across borders. We connect verified institutions and individuals with the best available exchange rates, low fees, and bank-grade compliance.',
        },
        'blog': {
            'page_title': 'Bridgr Blog',
            'heading': 'Insights & Updates',
            'message': 'Read the latest news, market insights, and product updates from Bridgr. We share practical tips for sending money internationally with confidence.',
        },
        'contact': {
            'page_title': 'Contact Bridgr',
            'heading': 'Contact Us',
            'message': 'Need help? Reach out to our support team for assistance with payments, accounts, or compliance questions.',
        },
        'privacy': {
            'page_title': 'Privacy Policy',
            'heading': 'Privacy Policy',
            'message': 'Your privacy is important to us. Bridgr only collects the minimum data required to securely process transactions and maintain account safety.',
        },
        'terms': {
            'page_title': 'Terms of Service',
            'heading': 'Terms of Service',
            'message': 'By using Bridgr, you agree to our terms, including payment processing rules, usage policies, and service commitments.',
        },
        'security': {
            'page_title': 'Security',
            'heading': 'Security & Compliance',
            'message': 'We use bank-grade encryption, multi-factor authentication, and strict compliance controls to protect your funds and data.',
        },
    }
    page_data = pages.get(page)
    if not page_data:
        raise Http404('Page not found')
    return render(request, 'static_page.html', page_data)


# ─── Auth ─────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        # TODO: send verification email with token; set is_email_verified after confirm
        messages.success(request, "Check your email to verify your Bridgr account.")
        return redirect('verify_email')

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not user.is_email_verified:
                messages.info(request, "Your email is not verified yet. You can still use your account.")
            return redirect(request.POST.get('next') or request.GET.get('next') or 'dashboard')
        messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def verify_email(request):
    return render(request, 'verifyemail.html')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    recent_txns = Transaction.objects.filter(sender=user).order_by('-created_at')[:5]
    context = {
        'recent_transactions': recent_txns,
        'unread_count': Notification.objects.filter(user=user, is_read=False).count(),
        'total_sent': Transaction.objects.filter(sender=user, status='completed').count(),
        'display_name': user_display_name(user),
        'currency_summary': get_currency_summary(user),
        'exchange_rates': get_dashboard_rates(get_live_rate, SUPPORTED_PAIRS),
        'recent_institution': get_recent_institution(user),
        'active_nav': 'dashboard',
    }
    return render(request, 'dashboard.html', context)


# ─── Send Money Flow ──────────────────────────────────────────────────────────
# Step 1 → Step 2 → Step 3 → Confirm → Receipt

@login_required
def send_step1(request):
    """Step 1: Choose amount, currencies, and recipient type."""
    if request.method == 'POST':
        send_amount   = request.POST.get('send_amount')
        send_currency = request.POST.get('send_currency')
        recv_currency = request.POST.get('receive_currency')
        recipient_type = request.POST.get('recipient_type')

        # Validate corridor
        if (send_currency, recv_currency) not in SUPPORTED_PAIRS:
            messages.error(request, "This currency corridor is not supported yet.")
            return redirect('send_step1')

        # Store in session
        request.session['send_data'] = {
            'send_amount':    send_amount,
            'send_currency':  send_currency,
            'recv_currency':  recv_currency,
            'recipient_type': recipient_type,
        }
        return redirect('send_step2')

    return render(request, 'send_step1.html', {
        'supported_pairs': SUPPORTED_PAIRS,
        'active_nav': 'send',
    })


@login_required
def send_step2(request):
    """Step 2: Recipient details (person or institution)."""
    send_data = request.session.get('send_data')
    if not send_data:
        return redirect('send_step1')

    recipient_type = send_data.get('recipient_type', 'person')
    institutions   = Institution.objects.filter(
        is_verified=True,
        country='NG' if send_data['recv_currency'] == 'NGN' else 'GH'
    ) if recipient_type == 'institution' else None

    if request.method == 'POST':
        if recipient_type == 'institution':
            institution_id = request.POST.get('institution_id')
            send_data['institution_id'] = institution_id
            send_data['recipient_name'] = Institution.objects.get(pk=institution_id).name
        else:
            send_data['recipient_name']    = request.POST.get('recipient_name')
            send_data['recipient_email']   = request.POST.get('recipient_email')
            send_data['recipient_account'] = request.POST.get('recipient_account')
            send_data['recipient_bank']    = request.POST.get('recipient_bank')

        send_data['purpose'] = request.POST.get('purpose', '')
        request.session['send_data'] = send_data
        return redirect('send_step3')

    return render(request, 'send_step2.html', {
        'send_data': send_data,
        'institutions': institutions,
        'recipient_type': recipient_type,
    })


@login_required
def send_step3(request):
    """Step 3: Fee Optimization Engine — user picks how fees are handled."""
    send_data = request.session.get('send_data')
    if not send_data:
        return redirect('send_step1')

    amount = decimal.Decimal(send_data['send_amount'])
    rate, is_fallback = get_live_rate(send_data['send_currency'], send_data['recv_currency'])

    # Calculate all three fee options for display
    sender_option    = calculate_fees(amount, 'sender')
    recipient_option = calculate_fees(amount, 'recipient')
    split_option     = calculate_fees(amount, 'split')

    receive_amount = (amount * rate).quantize(decimal.Decimal('0.01'))

    # Store rate in session for shield check at confirm
    send_data['rate_at_quote'] = str(rate)
    request.session['send_data'] = send_data

    if request.method == 'POST':
        fee_type = request.POST.get('fee_type', 'sender')
        send_data['fee_type'] = fee_type
        request.session['send_data'] = send_data
        return redirect('send_confirm')

    return render(request, 'send_step3.html', {
        'send_data':        send_data,
        'rate':             rate,
        'is_fallback':      is_fallback,
        'receive_amount':   receive_amount,
        'sender_option':    sender_option,
        'recipient_option': recipient_option,
        'split_option':     split_option,
        'amount':           amount,
    })


@login_required
def send_confirm(request):
    """Confirmation screen — locks rate, applies Fair Fee Shield if needed."""
    send_data = request.session.get('send_data')
    if not send_data:
        return redirect('send_step1')

    amount       = decimal.Decimal(send_data['send_amount'])
    fee_type     = send_data.get('fee_type', 'sender')
    quoted_rate  = decimal.Decimal(send_data['rate_at_quote'])

    # Get fresh rate and check shield
    current_rate, _ = get_live_rate(send_data['send_currency'], send_data['recv_currency'])
    shield_applied  = check_shield(current_rate, quoted_rate)

    # Lock the rate — if shield applies, use quoted rate to protect user
    locked_rate    = quoted_rate if shield_applied else current_rate
    receive_amount = (amount * locked_rate).quantize(decimal.Decimal('0.01'))
    total_fee, sender_fee, recipient_fee = calculate_fees(amount, fee_type)

    if request.method == 'POST':
        # Create the transaction
        institution = None
        if send_data.get('institution_id'):
            institution = Institution.objects.get(pk=send_data['institution_id'])

        txn = Transaction.objects.create(
            sender           = request.user,
            recipient_type   = send_data.get('recipient_type', 'person'),
            recipient_name   = send_data.get('recipient_name', ''),
            recipient_email  = send_data.get('recipient_email', ''),
            recipient_account= send_data.get('recipient_account', ''),
            recipient_bank   = send_data.get('recipient_bank', ''),
            institution      = institution,
            send_amount      = amount,
            send_currency    = send_data['send_currency'],
            receive_amount   = receive_amount,
            receive_currency = send_data['recv_currency'],
            exchange_rate    = locked_rate,
            fee_type         = fee_type,
            fee_amount       = total_fee,
            sender_fee       = sender_fee,
            recipient_fee    = recipient_fee,
            shield_applied   = shield_applied,
            rate_at_confirm  = locked_rate,
            purpose          = send_data.get('purpose', ''),
            status           = 'processing',
        )

        # Notify user
        Notification.objects.create(
            user        = request.user,
            transaction = txn,
            message     = f"Your transfer of {send_data['send_currency']} {amount} is being processed. Ref: {str(txn.reference)[:8].upper()}"
        )

        # Clear session
        del request.session['send_data']

        return redirect('receipt', pk=txn.pk)

    return render(request, 'send_confirm.html', {
        'send_data':      send_data,
        'locked_rate':    locked_rate,
        'receive_amount': receive_amount,
        'total_fee':      total_fee,
        'sender_fee':     sender_fee,
        'recipient_fee':  recipient_fee,
        'shield_applied': shield_applied,
        'fee_type':       fee_type,
        'amount':         amount,
    })


@login_required
def receipt(request, pk):
    """Transaction receipt page."""
    txn = get_object_or_404(Transaction, pk=pk, sender=request.user)
    return render(request, 'receipt.html', {'transaction': txn})


# ─── Transaction History ──────────────────────────────────────────────────────

@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(sender=request.user)

    status   = request.GET.get('status')
    currency = request.GET.get('currency')
    if status:
        transactions = transactions.filter(status=status)
    if currency:
        transactions = transactions.filter(send_currency=currency)

    return render(request, 'history.html', {
        'transactions': transactions,
        'active_nav': 'history',
    })


# ─── Notifications ────────────────────────────────────────────────────────────

@login_required
def notifications(request):
    notifs = Notification.objects.filter(user=request.user)
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {
        'notifications': notifs,
        'active_nav': 'notifications',
    })


# ─── AJAX: Live Rate ──────────────────────────────────────────────────────────

@require_GET
def get_rate(request):
    """AJAX endpoint — returns live rate for a currency pair."""
    from_c = request.GET.get('from', '').upper()
    to_c   = request.GET.get('to', '').upper()

    if (from_c, to_c) not in SUPPORTED_PAIRS:
        return JsonResponse({'error': 'Unsupported corridor.'}, status=400)

    rate, is_fallback = get_live_rate(from_c, to_c)
    return JsonResponse({
        'rate':        str(rate),
        'from':        from_c,
        'to':          to_c,
        'is_fallback': is_fallback,
    })


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.country      = request.POST.get('country', user.country)
        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']
        user.save()
        messages.success(request, "Profile updated.")
        return redirect('profile')

    return render(request, 'profile.html', {
        'user': request.user,
        'active_nav': 'profile',
    })