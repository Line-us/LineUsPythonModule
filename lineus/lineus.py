import socket
import shlex
import re
import zeroconf
import netifaces
import ipaddress
import threading
import time
import statistics

# python setup.py sdist
# twine upload dist/lineus-0.1.3.tar.gz


class LineUs:
    """An example class to show how to use the Line-us API"""

    __default_port = 1337
    __default_slow_search_timeout = .5
    __default_connect_timeout = 5
    __default_thread_count = 20

    def __init__(self):
        self.__line_us = None
        self.__connected = False
        self.__hello_message = ''
        self.on_found_line_us_callback = None
        self.zeroconf = zeroconf.Zeroconf()
        self.listener = None
        self.browser = None
        self.line_us_name = ''
        self.slow_line_us_list = []
        self.info = {}
        self.timeout = 0
        self.listener = LineUsListener()
        self.browser = zeroconf.ServiceBrowser(self.zeroconf, "_lineus._tcp.local.", self.listener)

    def connect(self, line_us_name=None, wait=2, timeout=None):
        start_time = time.perf_counter()
        if line_us_name is None:
            while line_us_name is None:
                line_us_name = self.listener.get_first_line_us()
                if line_us_name is None and time.perf_counter() - start_time > wait:
                    return False
        if isinstance(line_us_name, list):
            line_us_name = line_us_name[2]
        self.__line_us = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if timeout is not None:
            self.__line_us.settimeout(timeout)
        else:
            self.__line_us.settimeout(self.__default_connect_timeout)
        try:
            self.__line_us.connect((line_us_name, self.__default_port))
        except OSError:
            # print(error)
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

    def ping(self, line_us_name, count=5):
        ping_times = []
        self.connect(line_us_name)
        # First M114 is a little slow
        self.send_gcode('M114')
        for i in range(0, count):
            start = time.perf_counter()
            self.send_gcode('M114')
            duration = (time.perf_counter() - start) * 1000
            ping_times.append(duration)
            # time.sleep(0.05)
        self.disconnect()
        mean = statistics.mean(ping_times)
        stdev = statistics.stdev(ping_times)
        max_ping = max(ping_times)
        min_ping = min(ping_times)
        return {'mean': mean, 'min': min_ping, 'max': max_ping, 'stdev': stdev}

    @staticmethod
    def get_network_list():
        return NetFinder().get_network_list()

    def slow_search(self, network=None, return_first=True, timeout=None):
        self.slow_line_us_list = []
        if timeout is None:
            self.timeout = self.__default_slow_search_timeout
        nets = NetFinder()
        if network is not None:
            net_list = nets.get_network_list()
            if network > len(net_list):
                return []
        thread_count = self.__default_thread_count
        ip_list = []
        for i in range(0, thread_count):
            ip_list.append([])
        counter = 0
        for ip in nets.get_all_ips(interface=network):
            ip_list[counter].append(ip)
            counter += 1
            if counter == thread_count:
                counter = 0
        thread_list = []
        for thread_id in range(0, thread_count):
            thread = SlowSearchThread(ip_list[thread_id], return_first=return_first, timeout=timeout)
            thread_list.append(thread)
            thread.start()
        for thread in thread_list:
            thread.join()
            if len(thread.get_list()) > 0:
                self.slow_line_us_list.extend(thread.get_list())
        return self.slow_line_us_list


class SlowSearchThread(threading.Thread):

    __default_port = 1337

    def __init__(self, search_list, timeout, return_first=True):
        threading.Thread.__init__(self)
        self.search_list = search_list
        self.return_first = return_first
        self.timeout = timeout
        self.found_line_us = []

    def run(self):
        line_us_object = LineUs()
        for ip in self.search_list:
            # print(ip)
            if line_us_object.connect(str(ip), timeout=self.timeout):
                hello = line_us_object.get_hello_string()
                line_us_object.disconnect()
                line_us = (hello['NAME'], f'{hello["NAME"]}.local', str(ip), self.__default_port)
                self.found_line_us.append(line_us)
                if self.return_first:
                    return

    def get_list(self):
        return self.found_line_us


class LineUsListener:

    def __init__(self):
        self.on_found_line_us_callback = None
        self.line_us_list = []

    def remove_service(self, zconf, service_type, name):
        info = zconf.get_service_info(service_type, name)
        line_us_name = info.server.split('.')[0]
        line_us = (line_us_name, info.server, socket.inet_ntoa(info.address), info.port)
        self.line_us_list.remove(line_us)
        print(f'Service {name} removed')

    def add_service(self, zconf, service_type, name):
        info = zconf.get_service_info(service_type, name)
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

    def __init__(self):
        self.network_list = []
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
            interface_list = [self.network_list[interface]]
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

    my_line_us = LineUs()
    line_us_list = my_line_us.slow_search(return_first=False,)
    print(line_us_list)
