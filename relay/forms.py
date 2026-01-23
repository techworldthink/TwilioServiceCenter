from django import forms
from .models import Client, TwilioAccount, RoutingRule, APIKey
import re


class ClientForm(forms.ModelForm):
    """Form for creating and editing clients"""
    
    class Meta:
        model = Client
        fields = ['name', 'company_name', 'email', 'phone_number', 'website', 'address', 'balance', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'admin-form-control', 'placeholder': 'Full Name'}),
            'company_name': forms.TextInput(attrs={'class': 'admin-form-control', 'placeholder': 'Company Name (Optional)'}),
            'email': forms.EmailInput(attrs={'class': 'admin-form-control', 'placeholder': 'contact@example.com'}),
            'phone_number': forms.TextInput(attrs={'class': 'admin-form-control', 'placeholder': '+1 (555) 000-0000'}),
            'website': forms.URLInput(attrs={'class': 'admin-form-control', 'placeholder': 'https://example.com'}),
            'address': forms.Textarea(attrs={'class': 'admin-form-control', 'rows': 3, 'placeholder': 'Billing Address'}),
            'notes': forms.Textarea(attrs={'class': 'admin-form-control', 'rows': 3, 'placeholder': 'Internal notes...'}),
            'balance': forms.NumberInput(attrs={'class': 'admin-form-control', 'placeholder': '0.0000', 'step': '0.0001', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'Primary contact name',
            'email': 'Official contact email',
            'balance': 'Initial balance in USD',
        }


class TwilioAccountForm(forms.ModelForm):
    """Form for creating and editing Twilio accounts"""
    
    # Plain text field for token input (will be encrypted on save)
    auth_token = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'admin-form-control',
            'placeholder': 'Enter Twilio Auth Token',
        }),
        help_text='Your Twilio Auth Token (will be encrypted)',
        required=False,  # Not required for updates
    )
    
    class Meta:
        model = TwilioAccount
        fields = ['name', 'sid', 'auth_token', 'phone_number', 'description', 'capability_sms', 'capability_voice', 'capability_whatsapp']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'admin-form-control',
                'placeholder': 'Friendly Account Name',
            }),
            'sid': forms.TextInput(attrs={
                'class': 'admin-form-control',
                'placeholder': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                'maxlength': '34',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'admin-form-control',
                'placeholder': '+1 (555) 123-4567',
            }),
            'description': forms.TextInput(attrs={
                'class': 'admin-form-control',
                'placeholder': 'Internal Description / Tags',
            }),
            'capability_sms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'capability_voice': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'capability_whatsapp': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'A friendly name to identify this account easily',
            'sid': 'Your Twilio Account SID (starts with AC)',
            'phone_number': 'Primary Twilio phone number associated with this account',
        }
    
    def clean_sid(self):
        sid = self.cleaned_data.get('sid')
        if sid and not sid.startswith('AC'):
            raise forms.ValidationError('Twilio Account SID must start with "AC"')
        if sid and len(sid) != 34:
            raise forms.ValidationError('Twilio Account SID must be exactly 34 characters')
        return sid
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        auth_token = self.cleaned_data.get('auth_token')
        
        # Only update token if provided
        if auth_token:
            instance.set_token(auth_token)
        
        if commit:
            instance.save()
        return instance


class RoutingRuleForm(forms.ModelForm):
    """Form for creating and editing routing rules"""
    
    class Meta:
        model = RoutingRule
        fields = ['priority', 'pattern', 'account', 'description']
        widgets = {
            'priority': forms.NumberInput(attrs={
                'class': 'admin-form-control',
                'placeholder': '100',
                'min': '1',
            }),
            'pattern': forms.TextInput(attrs={
                'class': 'admin-form-control',
                'placeholder': r'^\+1.*',
            }),
            'account': forms.Select(attrs={
                'class': 'admin-form-control',
            }),
            'description': forms.TextInput(attrs={
                'class': 'admin-form-control',
                'placeholder': 'e.g., US/Canada numbers',
            }),
        }
        help_texts = {
            'priority': 'Lower number = higher priority',
            'pattern': 'Regex pattern to match phone numbers',
            'account': 'Twilio account to use for matching numbers',
            'description': 'Optional description for this rule',
        }
    
    def clean_pattern(self):
        pattern = self.cleaned_data.get('pattern')
        try:
            re.compile(pattern)
        except re.error as e:
            raise forms.ValidationError(f'Invalid regex pattern: {e}')
        return pattern


class APIKeyGenerateForm(forms.Form):
    """Form for generating new API keys"""
    
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        widget=forms.Select(attrs={
            'class': 'admin-form-control',
        }),
        help_text='Select the client for this API key',
    )
    
    prefix = forms.CharField(
        max_length=8,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'admin-form-control',
            'placeholder': 'Optional prefix (auto-generated if empty)',
            'maxlength': '8',
        }),
        help_text='Optional custom prefix for the key',
    )
    
    forced_account = forms.ModelChoiceField(
        queryset=TwilioAccount.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'admin-form-control',
        }),
        help_text='Optional: Force this key to use a specific Twilio Account (bypasses routing rules)',
    )
    
    allow_sms = forms.BooleanField(initial=True, required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    allow_voice = forms.BooleanField(initial=True, required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    allow_whatsapp = forms.BooleanField(initial=True, required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


class BalanceAdjustmentForm(forms.Form):
    """Form for adjusting client balance"""
    
    ADJUSTMENT_TYPES = [
        ('add', 'Add Funds'),
        ('deduct', 'Deduct Funds'),
        ('set', 'Set Balance'),
    ]
    
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_TYPES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
        initial='add',
    )
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'admin-form-control',
            'placeholder': '0.0000',
            'step': '0.0001',
        }),
        help_text='Amount in USD',
    )
    
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'admin-form-control',
            'placeholder': 'Optional note for this adjustment',
            'rows': 3,
        }),
    )
