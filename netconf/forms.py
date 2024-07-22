from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field
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

    def __init__(self, *args, choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if choices:
            self.fields['config_type'].choices = choices

class VariableValueForm(forms.Form):
    def __init__(self, *args, **kwargs):
        variables = kwargs.pop('variables', None)  # Retrieve variables from kwargs
        
        super().__init__(*args, **kwargs)
        
        if variables:
            for i, (path, variable_name) in enumerate(variables, start=1):
                self.fields[f'variable_{i}'] = forms.CharField(
                    label=f'{path}',
                    max_length=100,
                    required=False,
                    widget=forms.TextInput())

class NodeForm(forms.Form):
    current = ""
    Children = forms.ChoiceField(choices=[], label='')

    def __init__(self, *args, nodes=None, cur="", **kwargs):
        super().__init__(*args, **kwargs)
        self.current = cur 
        if nodes is not None:
            self.fields['Children'].choices = [(leaf, leaf) for leaf in nodes]

        self.fields['Children'].label = f'Current Element is "{self.current}". You can select a child element.'

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('method', 'Submit', css_class='btn-primary'))
                