from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QMainWindow

from .ui.appsettinggui import Ui_SettingWindow
from .app import Controller


class SettingWindow(QMainWindow, Ui_SettingWindow):
    def __init__(self, controller: Controller, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.controller = controller
        self.close_btn.clicked.connect(self.close_btn_clicked)
        self.scan_btn.clicked.connect(self.scan_btn_clicked)
        self.auto_reconnect_check.stateChanged.connect(self.auto_reconnect_state_changed)
        self.port_group_box_update()
        
    def close_btn_clicked(self):
        self.close()
    
    def scan_btn_clicked(self):
        self.port_group_box_update()
    
    def auto_reconnect_state_changed(self):
        self.controller.set_serial_auto_reconnect(self.get_auto_reconnect())
    
    def port_group_box_update(self):
        self.port_group.clear()
        for port in self.scan_available_ports():
            self.port_group.addItem(port)
    
    def scan_available_ports(self):
        return self.controller.get_available_ports()
    
    def get_selected_port(self):
        return self.port_group.currentText()
    
    def get_selected_baudrate(self):
        return int(self.baudrate_group.currentText())
    
    def get_auto_reconnect(self):
        return self.auto_reconnect_check.isChecked()
        