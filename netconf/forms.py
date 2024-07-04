from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

class ConnectForm(forms.Form):
    host = forms.CharField(label='Host', max_length=100, initial="ilgaz-ThinkCentre-neo-50t-Gen-4")
    port = forms.IntegerField(label='Port', initial="830")
    username = forms.CharField(label='Username', max_length=100, initial="ilgaz")
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