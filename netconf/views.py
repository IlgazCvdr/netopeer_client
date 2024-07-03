from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import AuthenticationError as NCAuthenticationError
import os

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
                # Establish the connection using ncclient
                with manager.connect(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        hostkey_verify=False,
                        allow_agent=False,
                        look_for_keys=False,
                        device_params={'name': 'default'}) as m:

                    # Store necessary data in session
                    request.session['netopeer_connection'] = {
                        'host': host,
                        'port': port,
                        'username': username,
                    }

                    # Retrieve the running configuration
                    config = m.get_config(source='running').data_xml

                    # Use Django's media directory for saving the file
                    media_dir = os.path.join(settings.MEDIA_ROOT, 'netopeer_configs')
                    if not os.path.exists(media_dir):
                        os.makedirs(media_dir, exist_ok=True)

                    file_name = f"config_{host}_{port}.xml"
                    file_path = os.path.join(media_dir, file_name)

                    # Save configuration to a file
                    with open(file_path, 'w') as file:
                        file.write(config)

                    # Render success page with the file path
                    return render(request, 'config_saved.html', {'file_path': file_path})

            except TimeoutExpiredError:
                error_message = f"Connection to {host}:{port} timed out."
                return render(request, 'connect.html', {'form': form, 'error_message': error_message})

            except NCAuthenticationError:
                error_message = f"Authentication failed for {username} on {host}:{port}."
                return render(request, 'connect.html', {'form': form, 'error_message': error_message})

            except Exception as e:
                error_message = f"Error connecting to {host}:{port}: {str(e)}"
                return render(request, 'connect.html', {'form': form, 'error_message': error_message})

    else:
        form = ConnectForm()

    return render(request, 'connect.html', {'form': form})

def connect_success(request):
    # Retrieve the connection data from session
    connection_data = request.session.get('netopeer_connection')

    if connection_data is None:
        # Handle case where connection data is not found in session
        return HttpResponse("Error: Netopeer connection data not found in session.")

    # Example: Extract server capabilities from the connection data
    server_capabilities = connection_data.get('server_capabilities', [])

    # Pass extracted data to template for rendering
    return render(request, 'connect_success.html', {'server_capabilities': server_capabilities})
