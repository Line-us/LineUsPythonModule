import socket
import shlex
import re
from zeroconf import ServiceBrowser, Zeroconf
import netifaces
import ipaddress

# python setup.py sdist
# twine upload dist/lineus-0.1.3.tar.gz


class LineUs:
    """An example class to show how to use the Line-us API"""

    __line_us = None
    __connected = False
    __hello_message = ''
    on_found_line_us_callback = None
    zeroconf = Zeroconf()
    listener = None
    browser = None
    line_us_name = ''
    info = {}
    __default_port = 1337
    __default_slow_search_timeout = 0.2

    def __init__(self):
        self.listener = LineUsListener()
        self.browser = ServiceBrowser(self.zeroconf, "_lineus._tcp.local.", self.listener)

    def connect(self, line_us_name=None, timeout=None):
        if line_us_name is None:
            line_us_name = self.listener.get_first_line_us()[2]
        self.__line_us = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if timeout is not None:
            self.__line_us.settimeout(timeout)
        try:
            self.__line_us.connect((line_us_name, self.__default_port))
        except OSError:
            return False
        self.__connected = True
        self.line_us_name = line_us_name
        self.__hello_message = self.__read_response()
        return True

    def set_timeout(self, timeout):
        self.__line_us.settimeout(timeout)

    def connected(self):
        return self.__connected

    def get_name(self):
        return self.line_us_name

    def get_line_us_list(self):
        return self.listener.get_line_us_list()

    def get_info(self):
        info = {}
        raw_info = self.send_gcode('M122', '')
        fields = shlex.split(raw_info.decode('utf-8'))
        if fields.pop(0) != 'ok':
            return None
        else:
            for field in fields:
                if field.split(':')[0] == 'mac':
                    info['mac'] = field[5:]
                else:
                    item = field.split(':')
                    info[item[0]] = item[1]
        return info

    def get_hello_string(self):
        hello_message = {}
        if self.__connected:
            hello = self.__hello_message.decode('utf-8')
            fields = shlex.split(hello)
            if fields.pop(0) != 'hello':
                return None
            for field in fields:
                split_fields = field.split(':', 1)
                hello_message[split_fields[0]] = split_fields[1]
            return hello_message
        else:
            return None

    def disconnect(self):
        """Close the connection to the Line-us"""
        self.__line_us.close()
        self.__connected = False

    def g01(self, x, y, z):
        """Send a G01 (interpolated move), and wait for the response before returning"""
        cmd = b'G01 X'
        cmd += str(x).encode()
        cmd += b' Y'
        cmd += str(y).encode()
        cmd += b' Z'
        cmd += str(z).encode()
        self.__send_command(cmd)
        self.__read_response()

    def send_gcode(self, gcode, parameters=''):
        cmd = gcode.encode()
        cmd += b' '
        cmd += parameters.encode()
        self.__send_command(cmd)
        return self.__read_response()

    def send_raw_gcode(self, gcode):
        cmd = gcode.encode()
        self.__send_command(cmd)
        return self.__read_response()

    def save_to_lineus(self, gcode, position):
        self.send_gcode('M28', f'S{position}')
        for line in gcode.splitlines():
            self.send_raw_gcode(line)
        self.send_gcode('M29')

    def list_lineus_files(self):
        info = []
        raw_info = self.send_gcode('M20')
        fields = shlex.split(raw_info.decode('utf-8'))
        if fields.pop(0) != 'ok':
            return None
        else:
            fields = re.split(':', fields[0])
            if fields.pop(0) != 'FS':
                return None
            else:
                fields = re.split(';', fields[0])
                for field in fields:
                    if field != '':
                        detail = re.split('-', field)
                        file_number = detail[0].lstrip('/')
                        file_number = file_number.lstrip('0')
                        file_number = file_number.rstrip('.txt')
                        file_size = detail[1]
                        info.append((file_number, file_size, detail[0]))
        return info

    def __read_response(self):
        """Read from the socket one byte at a time until we get a null"""
        line = b''
        while True:
            char = self.__line_us.recv(1)
            if char != b'\x00':
                line += char
            elif char == b'\x00':
                break
        return line

    def __send_command(self, command):
        """Send the command to Line-us"""
        command += b'\x00'
        self.__line_us.send(command)

    def on_found_line_us(self, callback):
        self.listener.on_found_line_us(callback)

    def slow_search(self, return_first=True, timeout=None):
        found_line_us = []
        if timeout is None:
            timeout = self.__default_slow_search_timeout
        nets = NetFinder()
        for ip in nets.get_all_ips():
            if self.connect(str(ip), timeout):
                hello = self.get_hello_string()
                line_us = (hello['NAME'], f'{hello["NAME"]}.local', str(ip), self.__default_port)
                if return_first:
                    return [line_us]
                else:
                    found_line_us.append(line_us)
        return found_line_us

    @staticmethod
    def get_network_list():
        return NetFinder().get_network_list()


class LineUsListener:

    def __init__(self):
        self.on_found_line_us_callback = None
        self.line_us_list = []

    def remove_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        line_us_name = info.server.split('.')[0]
        line_us = (line_us_name, info.server, socket.inet_ntoa(info.address), info.port)
        self.line_us_list.remove(line_us)
        print(f'Service {name} removed')

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        line_us_name = info.server.split('.')[0]
        line_us = (line_us_name, info.server, socket.inet_ntoa(info.address), info.port)
        # print(f'Found Line-us: {line_us[0]} at: {line_us[2]} port {line_us[3]}')
        self.line_us_list.append(line_us)
        if self.on_found_line_us_callback is not None:
            self.on_found_line_us_callback(line_us)

    def on_found_line_us(self, callback):
        self.on_found_line_us_callback = callback

    def get_first_line_us(self):
        if len(self.line_us_list) > 0:
            return self.line_us_list[0]
        else:
            return None

    def get_line_us(self, number):
        return self.line_us_list[number]

    def get_line_us_list(self):
        return self.line_us_list


class NetFinder:

    network_list = []

    def __init__(self):
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            if netifaces.ifaddresses(interface) is not None and netifaces.AF_INET in netifaces.ifaddresses(interface):
                this_interface = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]
                this_interface_detail = {'name': interface}
                for field in ('addr', 'netmask', 'broadcast'):
                    if field in this_interface:
                        this_interface_detail[field] = this_interface[field]
                if 'addr' in this_interface_detail and 'netmask' in this_interface_detail:
                    if 'broadcast' in this_interface_detail:
                        if not this_interface_detail['addr'].startswith('127'):
                            self.network_list.append(this_interface_detail)

    def get_network_list(self):
        return self.network_list

    def get_all_ips(self, interface=None):
        ips = []
        if interface is None:
            interface_list = self.network_list
        else:
            interface_list = self.network_list[interface]
        for interface in interface_list:
            addr = interface['addr']
            netmask_bits = self.netmask_to_cidr(interface['netmask'])
            # print(f'{addr} - {netmask_bits}')
            network = ipaddress.ip_network(f'{addr}/{netmask_bits}', strict=False)
            for host in network.hosts():
                ips.append(host)
        return ips

    @staticmethod
    def netmask_to_cidr(netmask):
        return sum([bin(int(x)).count('1') for x in netmask.split('.')])


if __name__ == '__main__':

    # found_line_us = False
    #
    # def callback_func(line_us):
    #     global found_line_us
    #     found_line_us = True
    #     print(f'callback: {line_us[0]}')

    my_line_us = LineUs()
    print(my_line_us.get_network_list())
    # line_us_list = my_line_us.slow_search(False)
    # print(line_us_list)
    # my_line_us.connect(line_us_list[0][1])
    # print(my_line_us.get_info())
    # my_line_us.on_found_line_us(callback_func)
    # while not found_line_us:
    #     pass
    # my_line_us.connect()
    # print(my_line_us.get_hello_string())
    # print(f'Found some machines: {my_line_us.get_line_us_list()}')
    # my_line_us.connect()
    # files = my_line_us.list_lineus_files()
    # print(files)
    # for i in range(80, 254):
    #     print(i)
    #     if my_line_us.connect(f'192.168.1.{i}', .3):
    #         my_line_us.set_timeout(20)
    #         print(my_line_us.get_info())
