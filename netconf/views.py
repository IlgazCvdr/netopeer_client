import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import AuthenticationError as AuthenticationError
from ncclient.operations.rpc import RPCError 
from .forms import ConnectForm, ConfigTypeForm, VariableValueForm
import xmltodict 
from lxml import etree as ET

# Define a global variable for the manager connection
global_manager = None
def getFilters(folderPath):
    config_methods = []
    for filename in os.listdir(folderPath):
        if filename.endswith(".xml"):
            method_name = os.path.splitext(filename)[0]  # Extract method name without extension
            config_methods.append((method_name, method_name))  # Add tuple for choice field
    return config_methods

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

        config_folder = "filters/get_filters/"
        # Get list of configuration methods from XML files
        config_methods = getFilters(config_folder) # Adjust this to your actual folder structure

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
                file_path = os.path.join("saves/get_saves/", file_name)
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

def extract_variables_from_xml(xml_string):
    root = ET.fromstring(xml_string)
    
    variables = []
    
    for elem in root.iter():
        if elem.text and "$" in elem.text:
            variable_name = elem.text.strip('{}')
            path = get_xpath(root, elem)  # Get the real XPath path
            variables.append((path, variable_name))
    
    return variables

def get_xpath(root, elem):
    path_elements = [elem.tag]
    for parent in elem.iterancestors():
        path_elements.insert(0, parent.tag)
    return '/'.join(path_elements)

def edit_filter(request):
    config_folder = "filters/edit_filters/"
    config_methods = getFilters(config_folder)

    if request.method == 'POST':
        method = request.POST.get('method')
        filter_file_path = os.path.join(config_folder, f"{method}.xml")
        with open(filter_file_path, 'r') as file:
            filter_xml = file.read()
        variables = extract_variables_from_xml(filter_xml)
        
        variable_value_form = VariableValueForm(request.POST, variables=variables)

        if variable_value_form.is_valid():
            variables = {key: value for key, value in variable_value_form.cleaned_data.items() if key.startswith('variable_')}
            values = {key: value for key, value in variable_value_form.cleaned_data.items() if key.startswith('value_')}
            response_message = f"Edit request for method {method} sent successfully.<br>Variables: {variables}<br>Values: {values}"
            return HttpResponse(response_message)

    else:
        method = config_methods[0][0] if config_methods else ''
        filter_file_path = os.path.join(config_folder, f"{method}.xml")
        with open(filter_file_path, 'r') as file:
            filter_xml = file.read()
        variables = extract_variables_from_xml(filter_xml)
        variable_value_form = VariableValueForm(variables=variables)
    
    config_type_form = ConfigTypeForm(choices=config_methods, initial={'method': method})

    return render(request, 'edit_filter.html', {
        'config_type_form': config_type_form,
        'variable_value_form': variable_value_form,
        'config_methods': config_methods,
    })