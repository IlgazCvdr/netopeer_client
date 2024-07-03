

from django.shortcuts import render, redirect
from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from .forms import ConnectForm

def connect(request):
    if request.method == 'POST':
        form = ConnectForm(request.POST)
        if form.is_valid():
            host = form.cleaned_data['host']
            port = form.cleaned_data['port']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            try:
                with manager.connect(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        hostkey_verify=False,  # Disable SSH host key verification
                        device_params={'name': 'default'}) as m:
                    
                    server_capabilities = m.server_capabilities

                    # Redirect to connect success page
                    return redirect('connect_success')
            
            except TimeoutExpiredError as e:
                error_message = f"Connection to {host}:{port} timed out."
                return render(request, 'connect.html', {'form': form, 'error_message': error_message})

            except Exception as e:
                error_message = f"Error connecting to {host}:{port}: {str(e)}"
                return render(request, 'connect.html', {'form': form, 'error_message': error_message})
    
    else:
        form = ConnectForm()
    
    return render(request, 'connect.html', {'form': form})


def connect_success(request):
    # You can perform any additional logic here if needed
    return render(request, 'connect_success.html')

