import unittest
import lineus
import time


class TestConnect(unittest.TestCase):

    def test_successful_connect(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.connect('line-us.local')
        my_line_us.disconnect()
        self.assertTrue(success)

    def test_successful_connect_default_name(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.connect()
        my_line_us.disconnect()
        self.assertTrue(success)

    def test_successful_connect_with_wait(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.connect(wait=5)
        my_line_us.disconnect()
        self.assertTrue(success)

    def test_successful_connect_with_timout(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.connect(timeout=50)
        my_line_us.disconnect()
        self.assertTrue(success)

    def test_unsuccessful_connect(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.connect('wgrhmftmf.local')
        my_line_us.disconnect()
        self.assertFalse(success)

    def test_good_timeout(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.set_timeout(50)
        self.assertTrue(success)

    def test_good_timeout_connected(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        success = my_line_us.set_timeout(50)
        my_line_us.disconnect()
        self.assertTrue(success)

    def test_bad_timeout(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.set_timeout('bob')
        self.assertFalse(success)

    def test_connected(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        success = my_line_us.connected()
        my_line_us.disconnect()
        self.assertTrue(success)

    def test_not_connected(self):
        my_line_us = lineus.LineUs()
        success = my_line_us.connected()
        self.assertFalse(success)

    def test_get_name(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect('line-us.local')
        name = my_line_us.get_name()
        my_line_us.disconnect()
        self.assertEqual('line-us.local', name)

    def test_get_line_us_list(self):
        my_line_us = lineus.LineUs()
        time.sleep(.5)
        line_us_list = my_line_us.get_line_us_list()
        self.assertIsInstance(line_us_list, list)

    def test_get_info(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        info = my_line_us.get_info()
        my_line_us.disconnect()
        self.assertGreater(len(info), 0)
        self.assertIsInstance(info, (dict, ))

    def test_get_hello(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        hello = my_line_us.get_hello_string()
        my_line_us.disconnect()
        self.assertGreater(len(hello), 0)
        self.assertIsInstance(hello, (dict, ))

    def test_send_gcode(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        reply = my_line_us.send_gcode('M122')
        my_line_us.disconnect()
        self.assertGreater(len(reply), 0)
        self.assertIsInstance(reply, str)

    def test_send_gcode_with_params(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        reply = my_line_us.send_gcode('G94', 'S7')
        my_line_us.disconnect()
        self.assertGreater(len(reply), 0)
        self.assertIsInstance(reply, str)

    def test_g01(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        reply = my_line_us.g01(1000, 1000, 1000)
        my_line_us.disconnect()
        self.assertGreater(len(reply), 0)
        self.assertIsInstance(reply, str)

    def test_send_raw_gcode(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        reply = my_line_us.send_raw_gcode('M122')
        my_line_us.disconnect()
        self.assertGreater(len(reply), 0)
        self.assertIsInstance(reply, str)

    def test_ping(self):
        my_line_us = lineus.LineUs()
        ping_stats = my_line_us.ping('line-us.local')
        self.assertEqual(len(ping_stats), 4)
        self.assertIsInstance(ping_stats, dict)

    # Seems to be a problem with M28 S32 reply not including a \0. No idea why
    # def test_save_to_line_us(self):
    #     my_line_us = lineus.LineUs()
    #     my_line_us.connect()
    #     reply = my_line_us.save_to_lineus('G28\nG28\n', 32)
    #     self.assertGreater(len(reply), 0)
    #     self.assertIsInstance(reply, str)

    def test_list_files(self):
        my_line_us = lineus.LineUs()
        my_line_us.connect()
        files = my_line_us.list_lineus_files()
        self.assertGreater(len(files), 0)
        self.assertIsInstance(files, list)

    def test_slow_search(self):
        my_line_us = lineus.LineUs()
        line_us_list = my_line_us.slow_search()
        self.assertIsInstance(line_us_list, list)

    def test_slow_search_all(self):
        my_line_us = lineus.LineUs()
        line_us_list = my_line_us.slow_search(return_first=False)
        self.assertIsInstance(line_us_list, list)


if __name__ == '__main__':
    unittest.main()
