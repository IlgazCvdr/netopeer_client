import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import AuthenticationError as AuthenticationError
from ncclient.operations.rpc import RPCError 
from .forms import ConnectForm, ConfigTypeForm
import xmltodict 
import xml.etree.ElementTree 
# Define a global variable for the manager connection
global_manager = None

# Define the new name value
new_name = "ahmet"

# Define the edit-config XML
edit_config_xml = f"""
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
    <people xmlns="test1">
        <name>{new_name}</name>
    </people>
</config>
"""



def get_config_filter(config_type):
    # Define the filter based on the type of configuration requested
    if config_type == 'interfaces':
        return """
<filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" type="subtree">
    <keystore xmlns="urn:ietf:params:xml:ns:yang:ietf-keystore">
        <asymmetric-keys>
            <asymmetric-key>
                <private-key-format xmlns:ct="urn:ietf:params:xml:ns:yang:ietf-crypto-types"/>
            </asymmetric-key>
        </asymmetric-keys>
    </keystore>
</filter>
"""
    elif config_type == 'system':
        return """
<filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" type="subtree">
    <people xmlns="test1">
        <name/>
    </people>
</filter>
"""
    elif config_type == "test1":
        return """
<filter>
    <data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
        <people xmlns="test1">
            <name>Ilgaz</name>
        </people>
    </data>
</filter>
"""
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
# views.py

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

        # Path to folder where configuration files will be saved
        config_folder = "filters/get_filters/"  # Adjust this to your actual folder structure

        # Get list of configuration methods from XML files
        config_methods = []
        for filename in os.listdir(config_folder):
            if filename.endswith(".xml"):
                method_name = os.path.splitext(filename)[0]  # Extract method name without extension
                config_methods.append((method_name, method_name))  # Add tuple for choice field

        if request.method == 'POST':
            method = request.POST.get('method')

            try:
                # Validate selected method
                if method not in [name for name, _ in config_methods]:
                    raise ValueError(f"Invalid method: {method}")

                # Read filter XML from file
                filter_file = os.path.join(config_folder, f"{method}.xml")
                with open(filter_file, 'r') as f:
                    config_filter = f.read()

                # Retrieve configuration data
                config = global_manager.get(config_filter).data_xml
                config_type = method

                # Parse XML to dictionary
                config_dict = xmltodict.parse(config)

                # Save configuration data to a file
                file_name = f"{config_type}_config.xml"
                file_path = os.path.join(config_folder, file_name)
                with open(file_path, 'w') as f:
                    f.write(config)

                # Render template with form and configuration data
                return render(request, 'select_config.html', {
                    'form': ConfigTypeForm(choices = config_methods, initial={'method': method}),
                    'config_data': config,
                    'config_type': config_type,
                    'file_path': file_path,  # Pass file path to template for download link
                    'server_capabilities': server_capabilities
                })

            except RPCError as e:
                error_message = f"RPC Error fetching configuration: {str(e)}"
                return render(request, 'select_config.html', {
                    'form': ConfigTypeForm(choices=config_methods, initial={'method': method}),
                    'error_message': error_message,
                    'server_capabilities': server_capabilities
                })

            except Exception as e:
                error_message = f"Error fetching or saving configuration: {str(e)}"
                return render(request, 'select_config.html', {
                    'form': ConfigTypeForm(choices=config_methods, initial={'method': method}),
                    'error_message': error_message,
                    'server_capabilities': server_capabilities
                })

        else:
            # Initialize form with options fetched from XML file names
            form = ConfigTypeForm(choices=config_methods, initial={'method': config_methods[0][0] if config_methods else ''})

        return render(request, 'select_config.html', {
            'form': form,
            'server_capabilities': server_capabilities
        })

    except Exception as e:
        error_message = f"Error connecting or fetching server capabilities: {str(e)}"
        return render(request, 'select_config.html', {
            'form': ConfigTypeForm(),
            'error_message': error_message,
            'server_capabilities': []
        })
