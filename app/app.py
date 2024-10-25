import time
import os
import sys
from struct import pack
from enum import Enum
try:
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    import pygame
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Package not found. Please install required packages by running \"pip install -r requirements.txt\"")


class Controller:
    HEADER = 0x9C
    JOY_THRESHOLD = 0.08
    DEFAULT_BAUDRATE = 115200
    MAX_NUM_JOY_AXIS = 6    # 2 joysticks * 2 axis + 2 triggers
    MAX_NUM_BUTTONS = 16     # 16 buttons
    MAX_NUM_HAT = 2        # 1 hat -> 4 buttons

    class Mode(Enum):
        AUTO_RECONNECT_MEMORY = 1
        DISABLED_AUTO_CONNECT = 2

    def __init__(self, mode: Mode = Mode.AUTO_RECONNECT_MEMORY, check_sum=1):
        # Serial
        self.ser = None     # Serial object
        self.port = ''      # Port name
        self.baudrate = Controller.DEFAULT_BAUDRATE  # Baudrate
        self.mode = mode    # Auto reconnect mode
        self.ports = {port.description: port.device for port in serial.tools.list_ports.comports()}

        # Controller
        self.joysticks = None       # pygame joystick object
        self.num_buttons = 0        # Number of buttons
        self.num_axis = 0           # Number of axes
        self.num_hat = 0            # Number of hats
        self.check_sum = check_sum  # Checksum flag
        self.num_axes_bytes = 0     # Number of bytes for axes for sending data
        self.num_btns_bytes = 0     # Number of bytes for buttons for sending data
        self.checksum_byte = 0x00   # Checksum byte for sending data

        self.ctrller_axis_state = bytearray(Controller.MAX_NUM_JOY_AXIS)
        self.ctrller_btn_state = bytearray(
            Controller.MAX_NUM_BUTTONS // 8 + Controller.MAX_NUM_HAT // 2)

        pygame.init()
        pygame.joystick.init()

        self.tick()

    def get_available_ports(self):
        self.ports = {port.description: port.device for port in serial.tools.list_ports.comports()}
        return self.ports.keys()

    def is_serial_connected(self):
        return self.ser is not None

    def serial_auto_reconnect_memory(self):
        if self.port == '':  # No memory
            return

        devices = self.get_available_ports()

        if self.port not in devices:
            return
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
        except serial.SerialException:
            pass

    def serial_auto_reconnect(self):
        if self.mode == Controller.Mode.AUTO_RECONNECT_MEMORY:
            self.serial_auto_reconnect_memory()

    def set_serial_auto_reconnect(self, is_auto_reconnect):
        if is_auto_reconnect:
            self.mode = Controller.Mode.AUTO_RECONNECT_MEMORY
        else:
            self.mode = Controller.Mode.DISABLED_AUTO_CONNECT

    def serial_connect(self, port, baudrate=DEFAULT_BAUDRATE):
        try:
            self.ser = serial.Serial(port, baudrate)
            self.port = port
            self.baudrate = baudrate
        except serial.SerialException:
            pass

    def serial_disconnect(self):
        if self.is_serial_connected():
            self.ser.close()
            del self.ser
            self.ser = None

    def update_hat_button_state(self, button_index, condition):
        if condition == 1:
            self.ctrller_btn_state[button_index //
                                   8] |= 1 << (button_index % 8)
        elif condition == -1:
            self.ctrller_btn_state[(button_index + 1) //
                                   8] |= 1 << ((button_index + 1) % 8)
        else:
            self.ctrller_btn_state[button_index //
                                   8] &= ~(1 << (button_index % 8))
            self.ctrller_btn_state[(button_index + 1) //
                                   8] &= ~(1 << ((button_index + 1) % 8))

    def calculate_checksum(self):
        # TODO: Implement a more efficient checksum in pythonic way
        self.checksum_byte = 0x00
        for i in range(self.num_axes_bytes):
            self.checksum_byte ^= self.ctrller_axis_state[i]
        for i in range(self.num_btns_bytes):
            self.checksum_byte ^= self.ctrller_btn_state[i]

    def update_controller_state(self):
        # Check if controller is still connected
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED and self.joysticks is None:
                self.joysticks = pygame.joystick.Joystick(0)
                self.joysticks.init()
                self.num_hat = self.joysticks.get_numhats()
                self.num_buttons = self.joysticks.get_numbuttons() + self.num_hat * \
                    4   # 4 buttons per hat
                self.num_axis = self.joysticks.get_numaxes()
                return
            elif event.type == pygame.JOYDEVICEREMOVED and self.joysticks is not None:
                del self.joysticks
                self.joysticks = None
                return

        # Update controller state if connected
        if self.joysticks is None:
            return
        try:
            # Update axis state
            for i in range(min(Controller.MAX_NUM_JOY_AXIS, self.num_axis)):
                raw_axis_value = self.joysticks.get_axis(i)
                if i in (4, 5):  # Triggers
                    axis_value = int((raw_axis_value + 1) * 127)
                    self.ctrller_axis_state[i] = pack(
                        'B', max(0, min(255, axis_value)))[0]
                else:
                    if abs(raw_axis_value) < self.JOY_THRESHOLD:
                        raw_axis_value = 0
                    axis_value = int(raw_axis_value * 127)
                    self.ctrller_axis_state[i] = pack(
                        'b', max(-128, min(127, axis_value)))[0]

            # Update button state
            for i in range(min(Controller.MAX_NUM_BUTTONS, self.num_buttons)):
                if self.joysticks.get_button(i):
                    self.ctrller_btn_state[i // 8] |= 1 << (i % 8)
                else:
                    self.ctrller_btn_state[i // 8] &= ~(1 << (i % 8))

            # Update hat state as buttons
            for i in range(min(Controller.MAX_NUM_HAT, self.num_hat)):
                hat_state = self.joysticks.get_hat(i)
                self.update_hat_button_state(i * 4, hat_state[0])
                self.update_hat_button_state(i * 4 + 2, hat_state[1])

            self.num_axes_bytes = min(
                Controller.MAX_NUM_JOY_AXIS, self.num_axis)
            self.num_btns_bytes = min(
                Controller.MAX_NUM_BUTTONS // 8, self.num_buttons // 8)

            if self.check_sum:
                self.calculate_checksum()

        except pygame.error as e:
            del self.joysticks
            self.joysticks = None
            sys.stderr.write(f'Error: {e}\n')
            sys.exit(1)

    def serial_send(self):
        if not self.is_serial_connected():
            return

        try:
            self.ser.write(bytearray([Controller.HEADER]))
            self.ser.write(self.ctrller_axis_state[:self.num_axes_bytes])
            self.ser.write(self.ctrller_btn_state[:self.num_btns_bytes])
            if self.check_sum:
                self.ser.write(bytearray([self.checksum_byte]))
        except serial.SerialException:
            del self.ser
            self.ser = None

    def tick(self):
        self.update_controller_state()

        if not self.is_serial_connected():
            self.serial_auto_reconnect()
        else:
            self.serial_send()

    def get_connection_status(self):
        return f'Uart: {"Connected" if self.is_serial_connected() else "Disconnected"}'

    def get_controller_state(self):
        if self.joysticks is None:
            return None

        return self.controller_state_data
