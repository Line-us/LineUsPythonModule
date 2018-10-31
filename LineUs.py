import socket
import shlex
from zeroconf import ServiceBrowser, Zeroconf


class LineUs:
    """An example class to show how to use the Line-us API"""

    def __init__(self):
        self.__line_us = None
        self.__connected = False
        self.__hello_message = ''
        self.on_found_line_us_callback = None
        self.zeroconf = Zeroconf()
        self.listener = LineUsListener()
        self.browser = ServiceBrowser(self.zeroconf, "_lineus._tcp.local.", self.listener)
        self.line_us_name = ''
        self.info = {}

    def connect(self, line_us_name):
        self.__line_us = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.__line_us.connect((line_us_name, 1337))
        except:
            return False
        self.__connected = True
        self.line_us_name = line_us_name
        self.__hello_message = self.__read_response()
        return True

    def connected(self):
        return self.__connected

    def get_name(self):
        return self.line_us_name

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
        if self.__connected:
            return self.__hello_message.encode('ascii')
        else:
            return 'Not connected'

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

    def send_gcode(self, gcode, parameters):
        cmd = gcode.encode()
        cmd += b' '
        cmd += parameters.encode()
        self.__send_command(cmd)
        return self.__read_response()

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


class LineUsListener:

    def __init__(self):
        self.on_found_line_us_callback = None
        self.line_us_list = []

    @staticmethod
    def remove_service(_self, _zeroconf, _service_type, name):
        print("Service %s removed" % (name,))

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
        return


if __name__ == '__main__':
    def callback_func(line_us):
        print(f'callback: {line_us[0]}')


    my_line_us = LineUs()
    my_line_us.on_found_line_us(callback_func)
    while True:
        pass
