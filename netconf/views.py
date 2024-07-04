import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import AuthenticationError as AuthenticationError
from ncclient.operations.rpc import RPCError 
from .forms import ConnectForm, ConfigTypeForm

# Define a global variable for the manager connection
global_manager = None
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

            except AuthenticationError:
                error_message = f"Authentication failed for {username} on {host}:{port}."
                return render(request, 'connect.html', {'form': form, 'error_message': error_message})

            except Exception as e:
                error_message = f"Error connecting to {host}:{port}: {str(e)}"
                return render(request, 'connect.html', {'form': form, 'error_message': error_message})

    else:
        form = ConnectForm()

    return render(request, 'connect.html', {'form': form})
# Define a global variable for the manager connection
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
            method = request.POST.get('method')

            try:
                if method == 'all':
                    # Fetch all configurations
                    config_filter = '<config><all/></config>'
                    config = global_manager.get_config(source='running').data_xml
                    config_type = 'all_configurations'
                else:
                    # Get static filter for the selected method
                    config_filter = get_config_filter(method)
                    if config_filter is None    :
                        raise ValueError(f"Invalid method: {method}")

                    # Fetch configuration data based on the selected method
                    config = global_manager.get_config(source='running', filter=('subtree', config_filter)).data_xml
                    config_type = method

                # Save configuration data to a file
                file_name = "saves/"+f"{config_type}_config.xml"
                file_path = os.path.join(settings.MEDIA_ROOT, file_name)
                
                with open(file_path, 'w') as f:
                    f.write(config)

            
                return render(request, 'select_config.html', {'form': ConfigTypeForm(server_capabilities), 'config_data': config, 'config_type': config_type})

            except RPCError as e:
                error_message = f"RPC Error fetching configuration: {str(e)}"
                return render(request, 'select_config.html', {'form': ConfigTypeForm(server_capabilities), 'error_message': error_message})

            except Exception as e:
                error_message = f"Error fetching or saving configuration: {str(e)}"
                return render(request, 'select_config.html', {'form': ConfigTypeForm(server_capabilities), 'error_message': error_message})

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