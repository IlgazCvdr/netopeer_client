from django.shortcuts import render
from ncclient import manager

def netconf_operation(request):
    host = 'localhost'  # Change to your Netopeer server address
    port = 830  # Netopeer default port
    username = 'admin'  # Change to your username
    password = 'admin'  # Change to your password

    netconf_reply = None

    if request.method == 'POST':
        # Retrieve form data
        netconf_command = request.POST.get('command')

        # Connect to the Netopeer server
        with manager.connect(
            host=host,
            port=port,
            username=username,
            password=password,
            hostkey_verify=False,
            device_params={'name': 'default'},
            allow_agent=False,
            look_for_keys=False
        ) as m:

            # Example: Perform a get-config operation
            if netconf_command == 'get-config':
                netconf_reply = m.get_config(source='running').xml
            # Add more commands as needed

    return render(request, 'netconf/netconf_operation.html', {'reply': netconf_reply})
from django.shortcuts import render


