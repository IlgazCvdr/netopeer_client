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

from dotenv import load_dotenv
import os
import copy
import xml.etree.ElementTree as et
# Define a global variable for the manager connection
global_manager = None
def getFilters(folderPath):
    config_methods = []
    for filename in os.listdir(folderPath):
        if filename.endswith(".xml"):
            method_name = os.path.splitext(filename)[0]  # Extract method name without extension
            config_methods.append((method_name, method_name))  # Add tuple for choice field
    return config_methods

global_tree = None
global_varible_num_for_edit = None
global_current = None
global_mark_parent_list = set()
global_mark_parent_temp = set()
global_identifier = 0   
global_leaves = []
# Define the new name value
new_name = "ahmet"
new_phone = "31313"
# Define the edit-config XML
edit_config_xml2 = f"""
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" >
  <people xmlns="test1">
    <person>
      <name>aaaa</name>
      <phone>99999</phone>
    </person>
    <person>
      <name>bbbbbb</name>
      <phone>88888</phone>
    </person>
  </people>
</config>
"""
edit_config_xml = f"""
<ns0:config xmlns:ns0="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:ns1="test1">
  <ns1:people>
    <ns1:person>
      <ns1:name>$0</ns1:name>
      <ns1:phone>11111</ns1:phone>
    </ns1:person>
    <ns1:person>
      <ns1:name>$2</ns1:name>
      <ns1:phone>22222</ns1:phone>
    </ns1:person>
    <ns1:person>
      <ns1:name>$4</ns1:name>
      <ns1:phone>44444</ns1:phone>
    </ns1:person>
    <ns1:person>
      <ns1:name>$6</ns1:name>
      <ns1:phone>66666</ns1:phone>
    </ns1:person>
  </ns1:people>
</ns0:config>
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
<ns0:filter xmlns:ns0="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:ns1="test1">
  <ns1:people>
    <ns1:person>
      <ns1:name>John Doe</ns1:name>
      <ns1:phone>12345</ns1:phone>
    </ns1:person>
    <ns1:person>
      <ns1:name>aaaa</ns1:name>
      <ns1:phone>99999</ns1:phone>
    </ns1:person>
    <ns1:person>
      <ns1:name>ahmet</ns1:name>
      <ns1:phone>31313</ns1:phone>
    </ns1:person>
    <ns1:person>
      <ns1:name>bbbbbb</ns1:name>
      <ns1:phone>88888</ns1:phone>
    </ns1:person>
  </ns1:people>
</ns0:filter>
"""
    elif config_type == "test1":
        return """
<filter>
    <data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
        <people xmlns="test1">
            <person>
                <name>John Doe</name>
             </person>
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
        # response = global_manager.edit_config(target='running', config=edit_config_xml)
                
        # print(response)

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
import re

def replace_variable_values_in_xml(xml_string, variables):
    """
    Replace variable placeholders in XML with their corresponding values.

    Args:
    - xml_string (str): Original XML string with variable placeholders.
    - variables (dict): Dictionary where keys are variable names and values are their replacements.

    Returns:
    - str: XML string with variables replaced by values.
    """
    for var_name, var_value in variables.items():
        # Escape special characters in variable name for regex
        var_name_escaped = re.escape(var_name)
        # Replace variable placeholder in XML with new value
        xml_string = re.sub(r'\{\s*' + var_name_escaped + r'\s*\}', var_value, xml_string)

    return xml_string
def edit_filter(request):
    global global_manager

    config_folder = "filters/edit_filters/"

    if request.method == 'POST':
        method = request.POST.get('method')
        filter_file_path = os.path.join(config_folder, f"{method}.xml")

        # Read the XML filter template
        with open(filter_file_path, 'r') as file:
            filter_xml = file.read()

        # Extract variables and values from POST data
        variables = {}
        values = {}
        for key, value in request.POST.items():
            if key.startswith('variable_'):
                variable_number = key.split('_')[1]
                variables[variable_number] = value
            elif key.startswith('value_'):
                value_number = key.split('_')[1]
                values[value_number] = value

        # Replace placeholders in the XML template
        updated_filter_xml = filter_xml
        for variable_number, value in values.items():
            placeholder = f'{{${variable_number}}}'
            updated_filter_xml = updated_filter_xml.replace(placeholder, value)

        try:
            # Send edit_config request to the NETCONF server
            if not global_manager:
                # Initialize ncclient manager if not already connected
                global_manager = manager.connect(
                    # Add your connection parameters here
                )

            # Send edit request
            print(updated_filter_xml)
            xml_obj = ET.fromstring(updated_filter_xml)

            response = global_manager.edit_config(target='running', config=xml_obj)

            # Handle success response
            response_message = f"Edit request for method {method} sent successfully.<br>Response: {response}"
            return HttpResponse(response_message)

        except RPCError as e:
            error_message = f"RPC Error: {str(e)}"
            return render(request, 'edit_filter.html', {
                'error_message': error_message,
            })

        except Exception as e:
            error_message = f"Error sending edit request: {str(e)}"
            return render(request, 'edit_filter.html', {
                'error_message': error_message,
            })

    else:
        # Handle GET request or initial form display
        config_methods = getFilters(config_folder)
        method = config_methods[0][0] if config_methods else ''
        filter_file_path = os.path.join(config_folder, f"{method}.xml")

        # Read the XML filter template
        with open(filter_file_path, 'r') as file:
            filter_xml = file.read()

        # Extract variables from XML for display in the form
        variables = extract_variables_from_xml(filter_xml)
        variable_value_form = VariableValueForm(variables=variables)
        config_type_form = ConfigTypeForm(choices=config_methods, initial={'method': method})

        return render(request, 'edit_filter.html', {
            'config_type_form': config_type_form,
            'variable_value_form': variable_value_form,
            'config_methods': config_methods,
        })
        return render(request, 'select_config.html', {'form': ConfigTypeForm(), 'error_message': error_message})

def mark_children(root):
    global global_mark_parent_temp
    global global_leaves
    if len(root) == 0:
        text = root.tag+" {$"+root.attrib["id"]+"}"
        if not text in global_leaves:
            global_leaves.append(text)
    for i in root[:]:
        mark_children(i)
    global_mark_parent_temp.add(root.attrib['id'])

 
def enumerate_func(root):
    global global_identifier
    global_identifier = global_identifier + 1 
    root.set("id",str(global_identifier))
    for i in root:
        enumerate_func(i)

def build_xml(root,isEdit):
    global global_mark_parent_list 
    global global_varible_num_for_edit
    if len(root) == 0:
        if isEdit:
            root.text = f'{"{"}${global_varible_num_for_edit}{"}"}'
            global_varible_num_for_edit = global_varible_num_for_edit + 1
        return
    for i in root[:]:
        if i.attrib["id"] in global_mark_parent_list:
            global_mark_parent_list.remove(i.attrib["id"])
            i.attrib.pop("id")
            build_xml(i,isEdit)
        else:
            root.remove(i)
    root.attrib.pop("id", None)

def create_xml(request):
    global global_manager
    global global_tree
    global global_current
    global global_mark_parent_list
    global global_mark_parent_temp
    global global_leaves
    global global_varible_num_for_edit
    load_dotenv()
    # Retrieve connection data from session
    connection_data = request.session.get('netopeer_connection')

    if not connection_data:
        return HttpResponse("Connection data not found in session.", status=400)

    host = connection_data['host']
    port = connection_data['port']
    username = connection_data['username']
    password = connection_data['password']

    try:
        action = request.POST.get('action')
        type = request.POST.get('option')
        filename = request.POST.get('filename')
        if action == "create":
            if not global_tree.getroot() is None:
                global_varible_num_for_edit = 0
                if type == "get":
                    new_tag = str(global_tree.getroot().tag).split("}")[0]+"}filter"
                    global_tree.getroot().tag = new_tag
                    build_xml(global_tree.getroot(),False)
                    #print(et.tostring(global_tree.getroot(), encoding='utf-8', method='xml').decode())    
                    with open(f'./filters/{filename}_get.xml', 'w') as f:
                        global_tree.write(f, encoding='unicode')
                    global_leaves = []
                elif type == "edit":
                    new_tag = str(global_tree.getroot().tag).split("}")[0]+"}config"
                    global_tree.getroot().tag = new_tag
                    build_xml(global_tree.getroot(),True)
                    #print(et.tostring(global_tree.getroot(), encoding='utf-8', method='xml').decode())    
                    with open(f'./filters/{filename}_get.xml', 'w') as f:
                        global_tree.write(f, encoding='unicode')
                    global_leaves = []
        if global_current is None or action == "reset" or action == "add" or action == "create":
            tree = et.parse('./saves/all_configurations_config.xml')
            root = tree.getroot()
            global_tree = tree
            global global_identifier 
            print(global_tree.getroot().tag)
            global_identifier = 0
            enumerate_func(root)
            #print(et.tostring(root, encoding='utf-8', method='xml').decode())
            if action == "add":
                if len(global_current) != 0:
                    mark_children(global_current)
                global_mark_parent_list = global_mark_parent_list.union(global_mark_parent_temp)
                global_mark_parent_temp = set()
                #for i in global_mark_parent_list:
                #    print("parent:"+i)
                #print(et.tostring(root, encoding='utf-8', method='xml').decode())
            global_current = root
            global_mark_parent_temp.add(global_current.attrib["id"])
            return render(request, 'create_xml.html',{'current':global_current.tag+"$"+global_current.attrib["id"], 'children':[i.tag+"$"+i.attrib["id"] for i in global_current],'leaves':global_leaves})
        if len(global_current) == 0:
            return render(request, 'create_xml.html',{'current':global_current.tag+"$"+global_current.attrib["id"], 'children':[global_current.text],'error_message':"You already selected the leaf",'leaves':global_leaves})
        else:
            tmp = request.POST.get('method')
            tmp2 = tmp.split("$")[1]
            #print(global_current.attrib['id'])
            for i in global_current:
                if i.attrib["id"] == tmp2:
                    global_current = i
                    break
            lst = []
            for i in global_current:
                lst.append(i.tag+"$"+i.attrib["id"])
            global_mark_parent_temp.add(global_current.attrib["id"])
            if len(global_current) == 0:
                return render(request, 'create_xml.html',{'current':global_current.tag+"$"+global_current.attrib["id"], 'children':[global_current.text],'leaves':global_leaves})
            return render(request, 'create_xml.html',{'current':global_current.tag+"$"+global_current.attrib["id"], 'children':lst,'leaves':global_leaves})
    except Exception as e:
        error_message = f"Error: {str(e)}"
        return render(request, 'create_xml.html',{'current':"", 'children':[],'leaves':""})
