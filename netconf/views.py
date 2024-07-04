import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse
from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import AuthenticationError as AuthenticationError
from ncclient.operations.rpc import RPCError 
from .forms import ConnectForm, ConfigTypeForm

# Define a global variable for the manager connection
global_manager = None

def connect(request):
    global global_manager

    if request.method == 'POST':
        form = ConnectForm(request.POST)
        if form.is_valid():
            host = form.cleaned_data['host']
            port = form.cleaned_data['port']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            try:
                # Establish the connection using ncclient
                global_manager = manager.connect(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    hostkey_verify=False,
                    allow_agent=False,
                    look_for_keys=False,
                    device_params={'name': 'default'}
                )

                # Store necessary data in session
                request.session['netopeer_connection'] = {
                    'host': host,
                    'port': port,
                    'username': username,
                    'password': password
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
    global global_manager

    # Retrieve connection data from session
    connection_data = request.session.get('netopeer_connection')

    if not connection_data:
        return HttpResponse("Connection data not found in session.", status=400)

    host = connection_data['host']
    port = connection_data['port']
    username = connection_data['username']
    password = connection_data['password']

    try:
        # Check if global_manager is initialized
        if not global_manager:
            # Establish the connection using ncclient
            global_manager = manager.connect(
                host=host,
                port=port,
                username=username,
                password=password,
                hostkey_verify=False,
                allow_agent=False,
                look_for_keys=False,
                device_params={'name': 'default'}
            )

        # Fetch server capabilities using the global_manager
        server_capabilities = list(global_manager.server_capabilities)

        if request.method == 'POST':
            form = ConfigTypeForm(server_capabilities, request.POST)
            if form.is_valid():
                config_type = form.cleaned_data['config_type']

                # Fetch configuration data based on the selected config_type
                try:
                    # Example filter creation, adjust as needed
                    config_filter = f'<{config_type}/>'
                    config = global_manager.get_config(source='running', filter=('subtree', config_filter)).data_xml

                    # Render the template with configuration data
                    return render(request, 'select_config.html', {'form': form, 'config_data': config, 'config_type': config_type})

                except RPCError as e:
                    error_message = f"RPC Error fetching configuration: {str(e)}"
                    return render(request, 'select_config.html', {'form': form, 'error_message': error_message})

                except Exception as e:
                    error_message = f"Error fetching or saving configuration: {str(e)}"
                    return render(request, 'select_config.html', {'form': form, 'error_message': error_message})

        else:
            # Initialize form with the first capability (or default)
            initial_capability = server_capabilities[0] if server_capabilities else ''
            form = ConfigTypeForm(server_capabilities, initial={'config_type': initial_capability})

        return render(request, 'select_config.html', {'form': form})

    except TimeoutExpiredError:
        error_message = f"Connection to {host}:{port} timed out."
        return render(request, 'select_config.html', {'form': ConfigTypeForm(), 'error_message': error_message})

    except AuthenticationError:
        error_message = f"Authentication failed for {username} on {host}:{port}."
        return render(request, 'select_config.html', {'form': ConfigTypeForm(), 'error_message': error_message})

    except Exception as e:
        error_message = f"Error connecting or fetching server capabilities: {str(e)}"
        return render(request, 'select_config.html', {'form': ConfigTypeForm(), 'error_message': error_message})


def save_config_to_file(config_data, host, port, config_type):
    # Create a directory if it doesn't exist to store configuration files
    save_dir = os.path.join(os.getcwd(), 'configurations')
    os.makedirs(save_dir, exist_ok=True)

    # Generate a unique file name based on host, port, and config type
    file_name = f"{host}_{port}_{config_type}.xml"
    file_path = os.path.join(save_dir, file_name)

    # Write configuration data to file
    with open(file_path, 'w') as f:
        f.write(config_data)

    return file_path

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
            password = connection_data['password']

            global netopeer_manager

            try:
                # Reuse the existing manager connection if it is still active
                if netopeer_manager is None or not netopeer_manager.connected:
                    netopeer_manager = manager.connect(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        hostkey_verify=False,
                        allow_agent=False,
                        look_for_keys=False,
                        device_params={'name': 'default'}
                    )

                config_filter = get_config_filter(config_type)

                if config_filter:
                    config = netopeer_manager.get_config(source='running', filter=('subtree', config_filter)).data_xml
                else:
                    config = netopeer_manager.get_config(source='running').data_xml

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
    # Define the filter based on the type of configuration requested
    if config_type == 'interfaces':
        return '''
        <filter>
            <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
        </filter>
        '''
    elif config_type == 'system':
        return '''
        <filter>
            <system xmlns="urn:ietf:params:xml:ns:yang:ietf-system"/>
        </filter>
        '''
    else:
        return None

def get_config_file_path(host, port, config_type):
    # Return the file path of the saved configuration
    media_dir = os.path.join(settings.MEDIA_ROOT, 'netopeer_configs')
    file_name = f"{config_type}_config_{host}_{port}.xml"
    return os.path.join(media_dir, file_name)

def connect_success(request):
    connection_data = request.session.get('netopeer_connection')

    if connection_data is None:
        return HttpResponse("Error: Netopeer connection data not found in session.")

    server_capabilities = connection_data.get('server_capabilities', [])

    return render(request, 'connect_success.html', {'server_capabilities': server_capabilities})
