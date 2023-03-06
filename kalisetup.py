import json
import sys
import os
import subprocess
import random
from ansible_playbook_runner import Runner
from simple_term_menu import TerminalMenu
from ansible_playbook_runner import Runner
from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.images.domain import Image
from hcloud.locations.domain import Location
from hcloud.firewalls.domain import Firewall
from hcloud.firewalls.domain import FirewallRule
from hcloud.isos.domain import Iso

#get basic data
ds_token = input("Type in API-token:\n")
customer = input("Type in customer name:\n")

#api token
tok = ds_token

def create_vm(vmname, stype, img, loc, fw):
        # Create 1 single host
        client = Client(token=tok)
        response = client.servers.create(name=vmname, server_type=ServerType(name=stype), image=Image(name=img), location=Location(name=loc), firewalls=fw)
        server = response.server
        return response.root_password, server.public_net.ipv4.ip, server.id, server

def showMenu():
    terminal_menu = TerminalMenu(options)
    menu_entry_index = terminal_menu.show()
    print(f"Will use the following base image: {options[menu_entry_index]}")
    return options[menu_entry_index], menu_entry_index

#Create kali FW
client = Client(token=tok)
rule_ssh = FirewallRule(
	direction = 'in',
	protocol = 'tcp',
	source_ips = ['0.0.0.0/0', '::/0'],
	port = '22345',
	destination_ips = [],
)

rule_9000 = FirewallRule(
        direction = 'in',
        protocol = 'tcp',
        source_ips = ['0.0.0.0/0', '::/0'],
        port = '9123-9125',
        destination_ips = [],
)

rule_vnc = FirewallRule(
        direction = 'in',
        protocol = 'tcp',
        source_ips = ['0.0.0.0/0', '::/0'],
        port = '5901-5909',
        destination_ips = [],
)

fw_name = customer + "-fw"
vm_name = customer + "-kali"
response = client.firewalls.create(name=fw_name, rules=[rule_ssh, rule_9000, rule_vnc])
j_fw = [response.firewall]

#create jumphost and attach fw
jump1_root, jump1_ip, jump1_id, jump_server = create_vm(vm_name, "cx41", "ubuntu-20.04", "fsn1", j_fw)

#get snapshots
print("Choose base image to build from")
response = client.images.get_all(type="snapshot")
options = []

for images in response:
	options.append(images.description)

chosen_img, imgIndex = showMenu()
cskname = chosen_img
kimg = response[imgIndex]

#rebuild from image kali-base
#wait to let server startup and avoid lockup
print("Rebuilding from the following image: " + cskname + "\nWaiting 2min to avoid lockup...\n")
os.system("ping localhost -c 120 > /dev/null")
response = client.servers.rebuild(server=jump_server, image=kimg)

#wait 15min to wait for rebuild
i = 0
print("Waiting 15min to let rebuild finish\n")
while i < 14:
	print(str(i+1) + "/15: Waiting for rebuild to finish")
	os.system("ping localhost -c 60 > /dev/null")
	i += 1

#reset root pw
response = client.servers.reset_password(server=jump_server)
root_pw = response.root_password

#delete inventory.yaml
#os.remove("./inventory.ini")
os.remove("./inventory.yaml")

#write inventory file
file_inv = open("./inventory.yaml", "w")
inv_template = "virtualmachines:\n  hosts:\n    vm01:\n      ansible_host: " + jump1_ip + "\n      ansible_user: adm1\n      ansible_port: 22345\n      ansible_ssh_private_key_file: ./adm1\n"
#file_inv = open("./inventory.ini", "w")
#inv_template = "[virtualmachines]\nansible_host=" + jump1_ip + "\nansible_user=adm1\nansible_port=22345\nansible_ssh_private_key_file=./adm1\n"
file_inv.write(inv_template)
file_inv.close

#update all stuff
#print("Updating all software...")
#subprocess.call(['sh', './ansible.sh'])
#Runner(['inventory.yaml'], 'playbook_update.yaml').run()

#clear screen
#os.system("clear")
print("All done :)\n")
print("IPv4: " + jump1_ip + "\n")
print("Root PW: " + root_pw + "\n")

#run ansible
print("Now run ansible.sh!")
