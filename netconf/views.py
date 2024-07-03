from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import AuthenticationError as NCAuthenticationError
import os
from .forms import ConnectForm, ConfigTypeForm

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

                    # Redirect to configuration selection page
                    return redirect('select_config')

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

def select_config(request):
    form = ConfigTypeForm()
    return render(request, 'select_config.html', {'form': form})

def get_config(request):
    if request.method == 'POST':
        form = ConfigTypeForm(request.POST)
        if form.is_valid():
            config_type = form.cleaned_data['config_type']

            # Retrieve connection data from session
            connection_data = request.session.get('netopeer_connection')
            if not connection_data:
                return HttpResponse("Connection data not found in session.", status=400)

            host = connection_data['host']
            port = connection_data['port']
            username = connection_data['username']
            password = 'H2Oiswater!'  # Replace with actual password

            try:
                with manager.connect(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        hostkey_verify=False,
                        allow_agent=False,
                        look_for_keys=False,
                        device_params={'name': 'default'}) as m:

                    config_filter = get_config_filter(config_type)
                        # Print server capabilities
                    print("Server Capabilities:")
                    for capability in m.server_capabilities:
                        print(capability)
                    if config_filter:
                        config = m.get_config(source='running', filter=('subtree', config_filter)).data_xml
                    else:
                        config = m.get_config(source='running').data_xml

                    save_config_to_file(config, host, port, config_type)

                    return render(request, 'config_saved.html', {'file_path': get_config_file_path(host, port, config_type)})

            except TimeoutExpiredError:
                error_message = f"Connection to {host}:{port} timed out."
                return render(request, 'select_config.html', {'form': form, 'error_message': error_message})

            except NCAuthenticationError:
                error_message = f"Authentication failed for {username} on {host}:{port}."
                return render(request, 'select_config.html', {'form': form, 'error_message': error_message})

            except Exception as e:
                error_message = f"Error connecting to {host}:{port}: {str(e)}"
                return render(request, 'select_config.html', {'form': form, 'error_message': error_message})

    return redirect('select_config')

def get_config_filter(config_type):
    if config_type == 'interfaces':
        return '''
        <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
            <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
        </filter>
        '''
    elif config_type == 'system':
        return '''
        <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
            <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system"/>
        </filter>
        '''
    else:
        return None


def save_config_to_file(config, host, port, config_type):
    media_dir = os.path.join(settings.MEDIA_ROOT, 'netopeer_configs')
    if not os.path.exists(media_dir):
        os.makedirs(media_dir, exist_ok=True)

    file_name = f"{config_type}_config_{host}_{port}.xml"
    file_path = os.path.join(media_dir, file_name)

    with open(file_path, 'w') as file:
        file.write(config)

def get_config_file_path(host, port, config_type):
    media_dir = os.path.join(settings.MEDIA_ROOT, 'netopeer_configs')
    file_name = f"{config_type}_config_{host}_{port}.xml"
    return os.path.join(media_dir, file_name)


def connect_success(request):
    connection_data = request.session.get('netopeer_connection')

    if connection_data is None:
        return HttpResponse("Error: Netopeer connection data not found in session.")

    server_capabilities = connection_data.get('server_capabilities', [])

    return render(request, 'connect_success.html', {'server_capabilities': server_capabilities})
