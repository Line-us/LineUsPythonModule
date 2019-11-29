import socket
import shlex
import re
import zeroconf
import netifaces
import ipaddress
import threading
import time
import statistics


class LineUs:
    """
    The Python module for Line-us. The module allows you to easily control your Line-us from Python using
    the TCP API which allow full access to all of the Line-us GCodes. Create a Line-us instance using::

        >>> my_line_us = LineUs()

    It is worth creating the ``LineUs()`` object as early as possible in your code as the search for
    machines begins as soon as the objet is created.
    """

    _default_port = 1337
    _default_slow_search_timeout = .5
    _default_connect_timeout = 5
    _default_thread_count = 20

    def __init__(self):
        self._line_us = None
        self._connected = False
        self._hello_message = None
        self.on_found_line_us_callback = None
        self.zeroconf = zeroconf.Zeroconf()
        self.listener = None
        self.browser = None
        self.line_us_name = None
        self.slow_line_us_list = []
        self.info = {}
        self.timeout = 0
        self.listener = LineUsListener()
        self.browser = zeroconf.ServiceBrowser(self.zeroconf, "_lineus._tcp.local.", self.listener)

    def connect(self, line_us_name=None, wait=2, timeout=None):
        """
        Connect to a Line-us. If ``line_us_name`` is not specified then the module will connect to the first
        Line-us that it finds. The Bonjour search starts when the LineUs object is created and it may take some
        time to discover the Line-us machines so the ``connect()`` function allows you to set a wait time (default 2s)
        to allow discovery. A timeout for the TCP connection can also be set. The default is ``None``, so the connection
        will wait forever. The simplest form of connect is::

            >>> my_line_us.connect()

        Returns ``True`` if the connection was successful.
        """
        start_time = time.perf_counter()
        if line_us_name is None:
            while line_us_name is None:
                line_us_name = self.listener.get_first_line_us()
                if line_us_name is None and time.perf_counter() - start_time > wait:
                    return False
        if isinstance(line_us_name, (list, tuple)):
            line_us_ip = line_us_name[2]
            line_us_name = line_us_name[0]
        else:
            line_us_ip = line_us_name
        self._line_us = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if timeout is not None:
            self._line_us.settimeout(timeout)
        else:
            self._line_us.settimeout(self._default_connect_timeout)
        try:
            self._line_us.connect((line_us_ip, self._default_port))
        except OSError:
            # print(error)
            return False
        self._connected = True
        self.line_us_name = line_us_name
        self._hello_message = self._read_response()
        return True

    def set_timeout(self, timeout):
        """
        This function sets the TCP timeout in seconds for the TCP connection to your Line-us.
        For example to set the timeout to 1.5 seconds::

            >>> my_line_us.set_timeout(1.5)

        Returns ```True``` if the timeout was successfully set.

        """
        try:
            timeout = int(timeout)
            self.timeout = timeout
            if self.connected():
                self._line_us.settimeout(timeout)
            return True
        except ValueError:
            return False

    def connected(self):
        """
        Returns ``True`` if a Line-us is connected
        """
        return self._connected

    def get_name(self):
        """
        Returns the name of the Line-us that you are connected to. If you are not connected to a Line-us
        it will return ``None``.
        """
        return self.line_us_name

    def get_line_us_list(self):
        """
        Returns an list with an element for each of the Line-us that the module has discovered. Each element
        in the list is a tuple of: ``(name, bonjour_name, ip_address)``. You can use either the bonjour_name or the
        ip_address in the ``connect()`` function to connect, although in most circumstances ip_address is a better
        option as it saves a name lookup. You do not need to be connected to a Line-us to use this function::

            >>> my_line_us = LineUs()
            >>> my_line_us.get_line_us_list()
            [('line-us-dev', 'line-us-dev.local.', '192.168.27.223', 1337), ('line-us-rob', 'line-us-rob.local.', '192.168.27.150', 1337)]

        """
        return self.listener.get_line_us_list()

    def get_info(self):
        """
        Returns a dictionary with infomation about the Line-us that is currently connected. Refer to the GCode
        spec in the Programming section of https://Line-us.com for more detail, but tan example is::

            {'ChipID': '1575520',
             'WifiMode': '1',
             'WifiModeSet': '0',
             'WifisConfigured': '1',
             'MemDraw': '0',
             'Gestures': '0',
             'ContinuousDrawing': '0',
             'DrawingCount': '0',
             'name': 'line-us-dev',
             'mac': 'C:3A:E8:18:0A:60',
             'FlashChipID': '0x1640ef',
             'FlashChipMode': '0',
             'FlashChipSpeed': '40000000',
             'FreeHeap': '25728',
             'ResetReason': 'External System',
             'Uptime': '0d0h12m11s',
             'Time': 'Fri Nov 29 16',
             'FSUsed': '112197',
             'FSTotal': '1953282',
             'FSFree': '1841085',
             'FSPercent': '5',
             'FS': '/0000001.txt-109291;/cal-29;/key-344; ',
             'Serial': 'ikdBW+',
             'Cal': '10.79735,-1.902405,9.900639',
             'ZMap': '0;100;300;200',
             'ServoReverse': '0,0,1'}

        """
        info = {}
        raw_info = self.send_gcode('M122', '')
        fields = shlex.split(raw_info)
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
        """
        Returns the hello string sent by Line-us wen you connect. The hello string is stored so you can run
        ``get_hello_string()`` at any time that a Line-us is connected. If no Line-us is conencted it will
        return ``None``. The hello string has a form similar to::

            {'VERSION': '3.2.0 Nov 22 2019 11:28:36', 'NAME': 'line-us', 'SERIAL': '1575520'}

        """
        hello_message = {}
        if self._connected:
            fields = shlex.split(self._hello_message)
            if fields.pop(0) != 'hello':
                return None
            for field in fields:
                split_fields = field.split(':', 1)
                hello_message[split_fields[0]] = split_fields[1]
            return hello_message
        else:
            return None

    def disconnect(self):
        """Close the connection to the Line-us. Returns True."""
        if self.connected():
            self._line_us.close()
        self._connected = False
        self._line_us = None
        self._hello_message = None
        self.line_us_name = None
        self.info = {}
        self.timeout = 0
        return True

    def g01(self, x=None, y=None, z=None):
        """
        Send a G01 (interpolated move), and wait for the response before returning. One or more of x, y and z
        must be specified. Some example commands are::

            >>> my_line_us.g01(1000, 0, 1000)     # (x, y, z)
            >>> my_line_us.g01(z=0)
            >>> my_line_us.g01(1000, 500)         # (x, y)

        Returns the reply message from Line-us, for Example::

            ok X:1000.00 Y:0.00 Z:1000.00

        """
        if x is None and y is None and z is None:
            return False
        cmd = b'G01 '
        if x is not None:
            cmd += b' X'
            cmd += str(x).encode()
        if y is not None:
            cmd += b' Y'
            cmd += str(y).encode()
        if z is not None:
            cmd += b' Z'
            cmd += str(z).encode()
        self._send_command(cmd)
        return self._read_response()

    def send_gcode(self, gcode, parameters=''):
        """
        Send an arbitrary GCode to Line-us. Refer to the GCode guide for details on supported commands. Some example
        uses are::

            >>> my_line_us.send_gcode('G28')                      # Go to home position
            >>> my_line_us.send_gcode('M550', 'Pline-us-rob')     # Re-name your Line-us

        The function returns the response from Line-us
        """
        cmd = gcode.encode()
        cmd += b' '
        cmd += parameters.encode()
        self._send_command(cmd)
        return self._read_response()

    def send_raw_gcode(self, gcode):
        """
        Send a raw GCode to Line-us. It is your responsibility to construct a vaild GCode, For example::

            >>> my_line_us.send_raw_gcode('M550 Pline-us')

        The function returns the response from Line-us
        """
        cmd = gcode.encode()
        self._send_command(cmd)
        return self._read_response()

    def save_to_lineus(self, gcode, position):
        """
        Save a drawing to the Line-us internal memory. The ``position`` parameter is the file numebr to save to
        and must be between 1 and 32. The ``gcode`` parameter is a string with the entrie gcode
        to save with each GCode separated with ``\\n``, for example to save GCode to file number 2::

            >>> gcode = 'G28\\nG01 X1000 Y0\\nG01 X1000  Y1000\\n'
            >>> my_line_us.save_to_lineus(gcode, 2)

        The function returns ``ok``
        """
        self.send_gcode('M28', f'S{position}')
        for line in gcode.splitlines():
            self.send_raw_gcode(line)
        self.send_gcode('M29')
        return 'ok'

    def list_lineus_files(self):
        """
        This function returns a list of the files stored on your Line-us. Each element in the list is a tuple of
        ``(file_number, size, fine_name)``. For Example::

            >>> my_line_us.list_lineus_files()
            [('1', '109291', '/0000001.txt'), ('2', '51765', '/0000002.txt')]

        """
        info = []
        raw_info = self.send_gcode('M20')
        fields = shlex.split(raw_info)
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

    def _read_response(self):
        """Read from the socket one byte at a time until we get a null"""
        line = b''
        while True:
            char = self._line_us.recv(1)
            if char != b'\x00':
                line += char
            elif char == b'\x00':
                break
        # print(f'R:{line.decode("utf - 8")}')
        while line[-1] in (10, 13, 0):
            line = line[:-1]
        return line.decode('utf-8')

    def _send_command(self, command):
        """Send the command to Line-us"""
        # print(f'S:{command}')
        command += b'\x00'
        self._line_us.send(command)

    def on_found_line_us(self, callback):
        self.listener.on_found_line_us(callback)

    def ping(self, line_us_name, count=5):
        """
        The ``ping()`` command tests the speed of the connection to a Line-us. You should be disconnected before
        calling it. It returns a ``dict`` with the following information::

            {'mean': 3.7004387999999944,
             'min': 2.9651769999999855,
             'max': 5.283999999999955,
             'stdev': 1.025966272915769}

        """
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
            self.timeout = self._default_slow_search_timeout
        nets = NetFinder()
        if network is not None:
            net_list = nets.get_network_list()
            if network > len(net_list):
                return []
        thread_count = self._default_thread_count
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

    _default_port = 1337

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
                line_us = (hello['NAME'], f'{hello["NAME"]}.local', str(ip), self._default_port)
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
    my_line_us.connect()
    reply = my_line_us.ping('line-us-dev.local')
    print(reply)
    # line_us_list = my_line_us.slow_search(return_first=False,)
    # print(line_us_list)
