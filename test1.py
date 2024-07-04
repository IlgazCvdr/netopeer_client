import warnings
from ncclient import manager

warnings.simplefilter("ignore", DeprecationWarning)

def demo(host, user, passwd):
    try:
        with manager.connect(host=host, port=830, username=user, password=passwd, hostkey_verify=False, allow_agent = False, look_for_keys=False, device_params={'name':'default'}) as m:
            for c in m.server_capabilities:
                print(c)
    except Exception as e:
        print(f"Failed to connect to {host}: {str(e)}")

if __name__ == '__main__':
    hostname = 'ilgaz-ThinkCentre-neo-50t-Gen-4'
    username = "ilgaz"
    password = "H2Oiswater!" 
    demo(hostname, username, password)
