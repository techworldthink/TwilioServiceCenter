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
    
    MATCH_TYPE_CHOICES = [
        ('starts_with', 'Starts with'),
        ('exact', 'Exact match'),
        ('regex', 'Advanced Regex'),
    ]

    match_type = forms.ChoiceField(
        choices=MATCH_TYPE_CHOICES,
        initial='starts_with',
        widget=forms.Select(attrs={'class': 'admin-form-control', 'id': 'id_match_type'}),
        help_text='Choose how to match the phone number'
    )

    simple_pattern = forms.CharField(
        required=False,
        label='Recipient Phone Number / Prefix',
        widget=forms.TextInput(attrs={
            'class': 'admin-form-control',
            'placeholder': '+1',
            'id': 'id_simple_pattern'
        }),
        help_text='Enter the destination number or prefix (e.g., +1 for US) to route through this account.'
    )

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
                'id': 'id_pattern'
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make pattern not required since we might generate it
        self.fields['pattern'].required = False
        
        # If editing, try to deduce match type
        if self.instance.pk and self.instance.pattern:
            pattern = self.instance.pattern
            if pattern.startswith('^') and pattern.endswith('.*') and '\\' in pattern:
                # Likely "starts_with" -> ^\+1.*
                raw = pattern[2:-2].replace('\\', '')
                self.fields['match_type'].initial = 'starts_with'
                self.fields['simple_pattern'].initial = raw
            elif pattern.startswith('^') and pattern.endswith('$') and '\\' in pattern:
                # Likely "exact" -> ^\+12345$
                raw = pattern[1:-1].replace('\\', '')
                self.fields['match_type'].initial = 'exact'
                self.fields['simple_pattern'].initial = raw
            else:
                self.fields['match_type'].initial = 'regex'

    def clean(self):
        cleaned_data = super().clean()
        match_type = cleaned_data.get('match_type')
        simple_pattern = cleaned_data.get('simple_pattern')
        pattern = cleaned_data.get('pattern')

        if match_type == 'regex':
            if not pattern:
                self.add_error('pattern', 'This field is required when using Advanced Regex.')
            # Validate regex
            try:
                if pattern:
                    re.compile(pattern)
            except re.error as e:
                self.add_error('pattern', f'Invalid regex pattern: {e}')
        else:
            if not simple_pattern:
                self.add_error('simple_pattern', 'This field is required.')
            else:
                # Escape special regex characters in the user input
                safe_input = re.escape(simple_pattern)
                
                if match_type == 'starts_with':
                    cleaned_data['pattern'] = f'^{safe_input}.*'
                elif match_type == 'exact':
                    cleaned_data['pattern'] = f'^{safe_input}$'
        
        return cleaned_data



class APIKeyUpdateForm(forms.ModelForm):
    """Form for editing existing API keys"""
    
    class Meta:
        model = APIKey
        fields = ['client', 'forced_account', 'allow_sms', 'allow_voice', 'allow_whatsapp', 'is_active']
        widgets = {
            'client': forms.Select(attrs={'class': 'admin-form-control'}),
            'forced_account': forms.Select(attrs={'class': 'admin-form-control'}),
            'allow_sms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_voice': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_whatsapp': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'client': 'Client associated with this key',
            'forced_account': 'Force this key to route via specific account (Overrides routing rules)',
            'is_active': 'Uncheck to temporarily disable this key',
        }


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
