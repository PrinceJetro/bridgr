from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Transaction


class RegisterForm(UserCreationForm):
    email      = forms.EmailField(required=True)
    country    = forms.ChoiceField(choices=CustomUser.COUNTRY_CHOICES)
    phone_number = forms.CharField(max_length=20, required=False)

    class Meta:
        model  = CustomUser
        fields = ['username', 'email', 'country', 'phone_number', 'password1', 'password2']


class SendMoneyForm(forms.Form):
    CURRENCY_CHOICES = [
        ('GBP', 'GBP — British Pound'),
        ('USD', 'USD — US Dollar'),
    ]
    RECEIVE_CHOICES = [
        ('NGN', 'NGN — Nigerian Naira'),
        ('GHS', 'GHS — Ghanaian Cedi'),
    ]
    RECIPIENT_TYPE = [
        ('person',      'Send to a Person'),
        ('institution', 'Pay an Institution (School / Hospital)'),
    ]

    send_amount    = forms.DecimalField(min_value=1, decimal_places=2)
    send_currency  = forms.ChoiceField(choices=CURRENCY_CHOICES)
    recv_currency  = forms.ChoiceField(choices=RECEIVE_CHOICES)
    recipient_type = forms.ChoiceField(choices=RECIPIENT_TYPE)


class RecipientForm(forms.Form):
    recipient_name    = forms.CharField(max_length=255)
    recipient_email   = forms.EmailField(required=False)
    recipient_account = forms.CharField(max_length=50)
    recipient_bank    = forms.CharField(max_length=255)
    purpose           = forms.CharField(max_length=255, required=False)