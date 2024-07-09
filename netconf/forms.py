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
                    label=f'Path of Variable {i}',
                    initial=path,
                    required=False,
                    widget=forms.TextInput(attrs={'readonly': 'readonly'})
                )
                self.fields[f'value_{i}'] = forms.CharField(
                    label=f'Text Field {i}',
                    max_length=100,
                    required=False,
                    widget=forms.TextInput()
                )