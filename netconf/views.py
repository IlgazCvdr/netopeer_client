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
from dotenv import load_dotenv
import os
import copy
# Define a global variable for the manager connection
global_manager = None
global_dict = None
global_dict_iterate = None
global_current = None
global_mark_parent_list = []
# Define the new name value
new_name = "ahmet"
new_phone = "31313"
# Define the edit-config XML
edit_config_xml = f"""
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
    <people xmlns="test1">
        <person>
            <name>{new_name}</name>
            <phone>{new_phone}</phone>
        </person>
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
        <person>
            <name>John Doe</name>
        </person>
    </people>
</filter>
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

                response = global_manager.edit_config(target='running', config=edit_config_xml)
                
                print(response)

                if method == 'all':
                    # Fetch all configurations
                    config_filter = '<config><all/></config>'
                    #config = global_manager.get().data_xml
                    config = global_manager.get_config(source='running').data_xml
                    config_type = 'all_configurations'
                else:
                    # Get static filter for the selected method
                    config_filter = get_config_filter(method)
                    if config_filter is None    :
                        raise ValueError(f"Invalid method: {method}")

                    # Fetch configuration data based on the selected method
                    config = global_manager.get(config_filter).data_xml
                    config_type = method

                config_dict = xmltodict.parse(config)
                print(config_dict)
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

def replace_leaf(leaf):
    temp = dict()
    temp["isleaf"] = True
    temp["value"] = leaf
    return temp 
def replace_leaves(dict1):
    for key, value in dict1.items():
        if isinstance(value, dict):
            replace_leaves(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    replace_leaves(item)
        elif key!="@xmlns" and key != "@xmlns:ct":
            dict1[key] = replace_leaf(value)
    return dict1

def print_marked(root):
    if type(root) == dict:
        if not "isleaf" in set(root.keys()):
            if "marked" in set(root.keys()):
                print(root)
            for key, value in root.items():
                print_marked(value)  
        else:
            if "marked" in set(root.keys()):
                print(root) 
    elif type(root) == list:
        if "marked" in set(root[-1].keys()):
            print(root)
        for item in root:
            mark_Children(item)
    else:
        pass

def mark_Children(root):
    if type(root) == dict:
        if not "isleaf" in set(root.keys()):
            for key, value in root.items():
                mark_Children(value)
        root["marked"] = True    
    elif type(root) == list:
        for item in root:
            mark_Children(item)
        root.append({"marked":True})
    else:
        pass

def find_ancestor(root, target):
    print(root,target)
    if type(root) is dict:
        return root[target]
    else:
        for i in root:
            if str(i) == target:
                return i
def mark_Parents():
    global global_mark_parent_list
    global global_dict
    temp = copy.deepcopy(global_dict)
    #print("asdsadsad:"+str(global_mark_parent_list))
    for i in global_mark_parent_list:
        temp = find_ancestor(temp, i)
        if type(temp) is dict:
            temp["marked"] = True
        else:
            temp.append({"marked":True})
    global_mark_parent_list = []
def mark(root):
    mark_Children(root)
    mark_Parents()

def create_xml(request):
    global global_manager
    global global_dict
    global global_current
    global global_mark_parent_list
    global global_dict_iterate
    load_dotenv()
    # Retrieve connection data from session
    connection_data = request.session.get('netopeer_connection')

    if not connection_data:
        return HttpResponse("Connection data not found in session.", status=400)

    host = connection_data['host']
    port = connection_data['port']
    username = connection_data['username']
    password = connection_data['password']


    action = request.POST.get('action')

    if global_dict is None or action == "reset" or action == "add":
        dict_content = dict()
        with open(os.getenv("XML_FILE"), 'r') as file:
            xml_content = file.read()
            dict_content = xmltodict.parse(xml_content)
        current_element = [i for i in dict_content.keys()][0]
        dict_content = replace_leaves(dict_content)
        if action == "reset" or global_dict is None:
            global_dict = copy.deepcopy(dict_content)
        global_dict_iterate = copy.deepcopy(global_dict)
        if action == "add":
            mark(global_current)
            #print(global_dict)
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")
        print_marked(global_dict[current_element])
    else:
        current_element = request.POST.get('method')
    if not(type(global_dict_iterate) == dict):
        #print(global_mark_parent_list)
        return render(request, 'create_xml.html',{'current':global_current, 'children':global_dict_iterate,'error_message':"You already selected the leaf"})
    children = global_dict_iterate[current_element]
    name = current_element
    children_names = []
    #print(global_mark_parent_list)
    global_current = current_element
    if type(children) == dict:
        if "isleaf" in set(children.keys()):
            global_mark_parent_list.append(current_element)
            global_dict_iterate = list()
            global_dict_iterate.append(children["value"])
            #print(global_dict)
            return render(request, 'create_xml.html',{'current':current_element, 'children':global_dict_iterate})
        for i in children.keys():
            if i != "@xmlns" and i != "@xmlns:ct":
                children_names.append(i)
            else:
                name = current_element + " xmlns:" + children[i]
        global_dict_iterate = children
    else:
        temp = dict()
        for i in children:
            children_names.append(i)
            temp[str(i)] = i
        global_dict_iterate = temp
    global_mark_parent_list.append(current_element)
    return render(request, 'create_xml.html',{'current':name, 'children':children_names})