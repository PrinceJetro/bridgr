import decimal

from django.db.models import Sum

from .models import Institution, Transaction

CURRENCY_SYMBOLS = {
    'GBP': '£',
    'USD': '$',
    'NGN': '₦',
    'GHS': '₵',
}

CURRENCY_LABELS = {
    'GBP': 'British Pound',
    'USD': 'US Dollar',
    'NGN': 'Nigerian Naira',
    'GHS': 'Ghanaian Cedi',
}


def user_display_name(user):
    name = user.get_full_name().strip()
    if name:
        return name
    return user.username


def get_currency_summary(user):
    """Total completed send volume per currency for the user."""
    rows = (
        Transaction.objects.filter(sender=user, status='completed')
        .values('send_currency')
        .annotate(total=Sum('send_amount'))
        .order_by('send_currency')
    )
    summary = []
    for row in rows:
        code = row['send_currency']
        summary.append({
            'code': code,
            'label': CURRENCY_LABELS.get(code, code),
            'symbol': CURRENCY_SYMBOLS.get(code, ''),
            'total': row['total'] or decimal.Decimal('0.00'),
        })
    return summary


def get_dashboard_rates(get_live_rate, supported_pairs):
    rates = []
    for from_c, to_c in sorted(supported_pairs):
        rate, is_fallback = get_live_rate(from_c, to_c)
        rates.append({
            'from_currency': from_c,
            'to_currency': to_c,
            'label': f'{from_c} → {to_c}',
            'rate': rate,
            'is_fallback': is_fallback,
        })
    return rates


def get_recent_institution(user):
    txn = (
        Transaction.objects.filter(sender=user, institution__isnull=False, institution__is_verified=True)
        .select_related('institution')
        .order_by('-created_at')
        .first()
    )
    return txn.institution if txn else None
