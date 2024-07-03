from django import forms

class ConnectForm(forms.Form):
    host = forms.CharField(label='Host Name', max_length=100, initial='ilgaz-ThinkCentre-neo-50t-Gen-4')
    port = forms.IntegerField(label='Port', initial=830)
    username = forms.CharField(label='Username', max_length=100, initial='ilgaz')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)


class ConfigTypeForm(forms.Form):
    CONFIG_CHOICES = [
        ('interfaces', 'Interfaces'),
        ('system', 'System Information'),
        ('full', 'Full Configuration'),
    ]
    config_type = forms.ChoiceField(choices=CONFIG_CHOICES, required=True)