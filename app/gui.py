from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QTimer

from .ui.appgui import Ui_MainWindow
from .setting_gui import SettingWindow
from .app import Controller


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, controller: Controller, parent=None, update_interval=20):
        super().__init__(parent)
        self.setupUi(self)

        self.setting_window = SettingWindow(controller)
        self.setting_btn.clicked.connect(self.setting_btn_clicked)
        self.connect_btn.clicked.connect(self.connect_btn_clicked)

        self.controller = controller
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.setInterval(update_interval)
        self.timer.start()

        self.joy_axes = [self.joy_lx_label, self.joy_ly_label,
                         self.joy_rx_label, self.joy_ry_label]
        self.trigger_axes = [self.trigger_l2_label, self.trigger_r2_label]

    def setting_btn_clicked(self):
        self.setting_window.show()

    def connect_btn_clicked(self):
        if self.controller.is_serial_connected():
            self.setting_window.auto_reconnect_check.setChecked(False)
            self.controller.serial_disconnect()
        else:
            port = self.controller.ports[self.setting_window.get_selected_port()]
            baudrate = self.setting_window.get_selected_baudrate()
            self.controller.serial_connect(port, baudrate)

    def set_uart_connect_text(self):
        if self.controller.is_serial_connected():
            self.uart_connection_status.setText('UART: Connected')
            self.uart_connection_status.setStyleSheet(
                'background-color: green; color: white;')
            self.connect_btn.setText('Disconnect')
        else:
            self.uart_connection_status.setText('UART: Disconnected')
            self.uart_connection_status.setStyleSheet(
                'background-color: red; color: white;')
            self.connect_btn.setText('Connect')

    def set_controller_connect_text(self):
        if self.controller.joysticks is not None:
            self.controller_connection_status.setText('Controller: Connected')
            self.controller_connection_status.setStyleSheet(
                'background-color: green; color: white;')
        else:
            self.controller_connection_status.setText(
                'Controller: Disconnected')
            self.controller_connection_status.setStyleSheet(
                'background-color: red; color: white;')

    def display_controller_state(self):
        for i, label in enumerate(self.joy_axes):
            label.setText(
                f'{int.from_bytes(self.controller.ctrller_axis_state[i:i+1], "big", signed=True)}')
        for i, label in enumerate(self.trigger_axes):
            label.setText(
                f'{int.from_bytes(self.controller.ctrller_axis_state[i+4:i+5], "big")}')
        self.button_state_label.setText(
            f'Button: {int.from_bytes(self.controller.ctrller_btn_state[:], "big"):024b}')
        self.raw_data_label.setText(
            f'Data  : {int.from_bytes(self.controller.ctrller_axis_state[:6], "big"):012x}'
                    + f'{int.from_bytes(self.controller.ctrller_btn_state[:], "big"):06x}' + f'{self.controller.checksum_byte:02x}')

    def update(self):
        self.controller.tick()

        self.set_uart_connect_text()
        self.set_controller_connect_text()
        self.display_controller_state()
