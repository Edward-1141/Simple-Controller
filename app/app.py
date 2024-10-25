import time
import os
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
    MAX_NUM_BUTTONS = 16     # 8 buttons    
    CHECKSUM = 1        # 1 byte checksum
    # NUM_HAT = 1        # ignore hat for now
    NUM_CONTROLLER_BYTES = MAX_NUM_JOY_AXIS + MAX_NUM_BUTTONS // 8 + CHECKSUM

    class Mode(Enum):
        AUTO_RECONNECT_MEMORY = 1
        DISABLED_AUTO_CONNECT = 2

    def __init__(self, mode: Mode = Mode.AUTO_RECONNECT_MEMORY):
        self.pressed_keys = set()
        self.ser = None
        self.joysticks = None
        self.num_buttons = 0
        self.num_axis = 0
        self.port = ''
        self.baudrate = Controller.DEFAULT_BAUDRATE
        self.mode = mode
        self.ports = serial.tools.list_ports.comports()

        self.controller_state_data = bytearray(Controller.NUM_CONTROLLER_BYTES) # For sending through serial

        pygame.init()
        pygame.joystick.init()

        self.tick()

    def get_available_ports(self):
        self.ports = serial.tools.list_ports.comports()
        return [port.description for port in self.ports]
    
    def is_serial_connected(self):
        return self.ser is not None

    def serial_auto_reconnect_memory(self):
        if self.port == '': # No memory
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

    def serial_connect(self, port, baudrate = DEFAULT_BAUDRATE):
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

    def update_controller_state(self):
        # Check if controller is still connected
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED and self.joysticks is None:
                self.joysticks = pygame.joystick.Joystick(0)
                self.joysticks.init()
                self.num_buttons = self.joysticks.get_numbuttons()
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
            for i in range(min(Controller.MAX_NUM_JOY_AXIS, self.num_axis)):
                raw_axis_value = self.joysticks.get_axis(i)
                if i in (4, 5): # Triggers
                    axis_value = int((raw_axis_value + 1) * 127)
                    axis_value = max(0, min(255, axis_value))
                    self.controller_state_data[i] = pack('B', axis_value)[0]
                else:
                    if abs(raw_axis_value) < self.JOY_THRESHOLD:
                        raw_axis_value = 0
                    axis_value = int(raw_axis_value * 127)
                    axis_value = max(-128, min(127, axis_value))
                    self.controller_state_data[i] = pack('b', axis_value)[0]

            for i in range(min(Controller.MAX_NUM_BUTTONS, self.num_buttons)):
                if self.joysticks.get_button(i):
                    self.controller_state_data[Controller.MAX_NUM_JOY_AXIS + i // 8] |= 1 << (i % 8)
                else:
                    self.controller_state_data[Controller.MAX_NUM_JOY_AXIS + i // 8] &= ~(1 << (i % 8))
            
            if Controller.CHECKSUM == 1:
                checksum = 0x00
                for i in range(Controller.NUM_CONTROLLER_BYTES - 1):
                    checksum ^= self.controller_state_data[i]
                self.controller_state_data[-1] = checksum
        except pygame.error:
            del self.joysticks
            self.joysticks = None
        # Ignore hat for now

    def serial_send(self):
        if not self.is_serial_connected():
            return
        
        try:
            self.ser.write(bytearray([Controller.HEADER]))
            self.ser.write(self.controller_state_data)
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