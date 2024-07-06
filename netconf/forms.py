from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from dotenv import load_dotenv
import os

class ConnectForm(forms.Form):
    load_dotenv()
    host = os.getenv('HOST')
    port = os.getenv('PORT')
    username = os.getenv('USERNAME')
    host = forms.CharField(label='Host', max_length=100, initial=host)
    port = forms.IntegerField(label='Port', initial=port)
    username = forms.CharField(label='Username', max_length=100, initial=username)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Connect'))

class ConfigTypeForm(forms.Form):
    config_type = forms.ChoiceField(choices=[], required=True, label='Select Configuration Type')

    def __init__(self, capabilities, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['config_type'].choices = [(cap, cap) for cap in capabilities]