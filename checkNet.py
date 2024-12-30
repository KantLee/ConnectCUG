import socket
import psutil
import subprocess
from PyQt5.QtCore import QUrl, QObject, pyqtSignal
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest


class NetworkChecker(QObject):
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.on_request_finished)

    def check_internet_connection(self):
        url = QUrl("https://www.baidu.com/")
        request = QNetworkRequest(url)
        self.manager.get(request)

    def check_connect(self):
        net_state = subprocess.run(
            'ping www.baidu.com',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=True
        )
        return net_state.returncode

    def on_request_finished(self, reply):
        connected = not reply.error()
        self.connection_status.emit(connected)
        reply.deleteLater()

    def get_ip(self):
        st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            st.connect(('10.255.255.255', 1))
            self.ip = st.getsockname()[0]
        except Exception:
            self.ip = '0.0.0.0'
        finally:
            st.close()
        return self.ip

    def get_net_type(self):
        net_info = psutil.net_if_addrs()
        for name, info in net_info.items():
            ipv4_address = None  # 初始化为None，以便处理接口没有IPv4地址的情况
            for addr in info:
                if addr.family == socket.AF_INET:
                    ipv4_address = addr.address
                    break  # 找到IPv4地址后就退出循环
            if ipv4_address == self.ip:
                return name
        return '未知类型'

    def from_type_get_ip(self, type):
        ipv4_address = None  # 初始化为None，以便处理接口没有IPv4地址的情况
        net_info = psutil.net_if_addrs()
        for name, info in net_info.items():
            if name == type:
                for addr in info:
                    if addr.family == socket.AF_INET:
                        ipv4_address = addr.address
                        break  # 找到IPv4地址后就退出循环
        return ipv4_address

    # 设置以太网ip地址和dns
    def set_ethernet_configuration(self, name):
        ip_addr = '172.27.113.130'
        mask = '255.255.0.0'
        gateway = '172.27.255.254'
        dns1 = '202.114.200.252'
        dns2 = '202.114.200.253'
        command1 = ['netsh', 'interface', 'ip', 'set', 'address', 'name={}'.format(name), 'source=static', ip_addr,
                    mask, gateway, '1']
        command2 = ['netsh', 'interface', 'ip', 'set', 'dns', name, 'static', dns1, 'primary']
        command3 = ['netsh', 'interface', 'ip', 'add', 'dns', name, dns2]
        # 手动设置ip
        subprocess.run(command1)
        # 手动设置DNS地址
        subprocess.run(command2)
        # 添加第二个DNS地址
        subprocess.run(command3)

    # 设置dhcp
    def set_ethernet_configuration_dhcp(self, name):
        command1 = ['netsh', 'interface', 'ip', 'set', 'address', 'name={}'.format(name), 'source=dhcp']
        command2 = ['netsh', 'interface', 'ip', 'set', 'dns', name, 'dhcp']
        subprocess.run(command1)
        subprocess.run(command2)
