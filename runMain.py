import sys
import os
import winreg
import subprocess
import time
import icon
from Main import Ui_Main
from checkNet import NetworkChecker
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import QTimer, QThread, QEventLoop, QUrl, QByteArray
from PyQt5.QtGui import QIcon
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


def get_app_path():
    if getattr(sys, 'frozen', False):
        # 打包后的exe文件路径
        return os.path.dirname(sys.executable)
    else:
        # 脚本运行时的目录
        return os.path.dirname(os.path.abspath(__file__))


def create_batch_file(exe_path):
    bat_script = r"""
@echo off
cd /d "%~dp0"
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if %errorlevel% neq 0 (
    goto UACPrompt
) else (
    goto :runScript
)

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\runAsAdmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\runAsAdmin.vbs"

    "%temp%\runAsAdmin.vbs"
    del "%temp%\runAsAdmin.vbs"
    exit /B

:runScript
    start {}
    """
    with open('run_connectCUG_admin.bat', 'w') as f:
        f.write(bat_script.format(exe_path))


def add_to_startup(file_path):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0,
                         winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, 'ConnectCUG', 0, winreg.REG_SZ, file_path)
    winreg.CloseKey(key)


def wait_for_seconds(seconds):
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(loop.quit)
    timer.start(seconds * 1000)  # 将秒转换为毫秒
    loop.exec_()


class MyThreadRefresh(QThread):
    def __init__(self):
        super(MyThreadRefresh, self).__init__()

    def run(self):
        subprocess.run('ipconfig/release', shell=True)
        time.sleep(5)
        subprocess.run('ipconfig/renew', shell=True)
        time.sleep(5)


class ConnectCUG(QWidget, Ui_Main):
    def __init__(self, parent=None):
        super(ConnectCUG, self).__init__(parent=parent)
        self.app_path = get_app_path()
        self.filePath = os.path.join(self.app_path, 'info.txt')
        self.haveAccount = False
        self.network_checker = NetworkChecker()
        self.setupUi(self)
        self.out_log('程序启动')
        self.manager = None
        self.loginTime = 0  # 登录时间
        self.verifyIP = None  # 登录的url的ip
        self.netType = None  # 网络类型
        self.data = QByteArray()
        self.manager = QNetworkAccessManager()
        # 添加定时器，每隔一段时间检查网络状态
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_network)
        self.timer.start(1800000)  # 1800秒（0.5小时）检查一次
        self.signal_slot()
        # 判断是否连网
        self.check_network()
        self.init_info()

    def signal_slot(self):
        self.pushButton.clicked.connect(self.login)
        self.pushButton_2.clicked.connect(self.release_login)
        self.network_checker.connection_status.connect(self.update_net_status)
        self.manager.finished.connect(self.handle_response)

    def release_login(self):
        self.pushButton.setEnabled(True)

    def check_network(self):
        self.out_log('正在检测当前是否连网')
        self.network_checker.check_internet_connection()

    def update_net_status(self, connected):
        ip = self.network_checker.get_ip()
        net_type = self.network_checker.get_net_type()
        self.netType = net_type
        if connected:
            self.label_status.setText("已连接到网络")
            self.out_log('检测状态：已连接到网络')
            self.label_ip.setText(ip)
            self.out_log('IP地址为{}'.format(ip))
            self.label_7.setText(net_type)
            self.out_log('网络类型为{}'.format(net_type))
        else:
            self.label_status.setText("未连接到网络")
            self.out_log('检测状态：未连接到网络')
            if ip == '0.0.0.0':
                self.out_log('请检查网线是否插好或者WIFI是否连接到CUG')
            else:
                if '以太网' in net_type:
                    self.out_log('当前是网线连接，正在做连接到楼下服务器的预防措施，请等待3秒')
                    self.network_checker.set_ethernet_configuration(net_type)
                    time.sleep(2)
                    wait_for_seconds(3)
                    self.network_checker.set_ethernet_configuration_dhcp(net_type)
                    self.out_log('预防措施操作完成')
                    if self.haveAccount:
                        self.login()
                    else:
                        QMessageBox.warning(self, '警告', '本地未查询到登录信息，请手动登录账号')

    def init_info(self):
        if os.path.isfile(self.filePath):
            try:
                with open('info.txt', 'r') as file:
                    lines = file.readlines()
                    username = lines[0].strip().split('=')[1]
                    password = lines[1].strip().split('=')[1]
                    self.lineEdit.setText(username)
                    self.lineEdit_2.setText(password)
                self.out_log('从本地读取登录信息成功')
                self.haveAccount = True
            except Exception as e:
                QMessageBox.warning(self, '警告', '错误：{}'.format(str(e)))
        else:
            self.out_log('本地未查询到登录信息')
            self.haveAccount = False

    def login(self):
        username = self.lineEdit.text()
        password = self.lineEdit_2.text()
        if username == '' or password == '':
            QMessageBox.warning(self, '警告', '请先输入账号')
            return
        self.loginTime = 0
        self.pushButton.setEnabled(False)
        if '以太网' not in self.netType:
            self.out_log('请等待10秒刷新网络')
            wait_for_seconds(10)
            refresh_thread = MyThreadRefresh()
            refresh_thread.start()
            self.out_log('刷新完成')
        self.out_log('开始登录账号{}'.format(username))
        url = 'http://192.168.167.115/srun_portal_pc?ac_id=1&srun_wait=1&theme=basic'
        self.verifyIP = '192.168.167.115'
        self.data.append('username={}&password={}'.format(username, password).encode())
        request = QNetworkRequest(QUrl(url))
        # 设置超时时间为5秒（以毫秒为单位）
        request.setTransferTimeout(5000)
        self.manager.post(request, self.data)
        try:
            with open(self.filePath, 'w') as file:
                file.write('studentNumber={}\npassword={}\n'.format(username, password))
        except Exception as e:
            QMessageBox.warning(self, '警告', '错误：{}'.format(str(e)))

    def login_2_3(self, url):
        request = QNetworkRequest(QUrl(url))
        if self.loginTime == 1:
            self.verifyIP = '192.168.167.14'
        elif self.loginTime == 2:
            self.verifyIP = '192.168.167.13'
        # 设置超时时间为5秒（以毫秒为单位）
        request.setTransferTimeout(5000)
        self.manager.post(request, self.data)

    def handle_response(self, reply):
        self.loginTime += 1
        er = reply.error()
        if er == QNetworkReply.NoError:
            self.out_log('使用{}登录成功'.format(self.verifyIP))
            ip = self.network_checker.get_ip()
            net_type = self.network_checker.get_net_type()
            self.label_ip.setText(ip)
            self.out_log('IP地址为{}'.format(ip))
            self.label_7.setText(net_type)
            self.out_log('网络类型为{}'.format(net_type))

        elif er == 5:
            if self.loginTime == 1:
                self.out_log('使用{}登录超时，尝试使用{}再次登录'.format(self.verifyIP, '192.168.167.14'))
                self.login_2_3('http://192.168.167.14/srun_portal_pc?ac_id=1&srun_wait=1&theme=basic')
            elif self.loginTime == 2:
                self.out_log('使用{}登录超时，尝试使用{}再次登录'.format(self.verifyIP, '192.168.167.13'))
                self.login_2_3('http://192.168.167.13/srun_portal_pc?ac_id=1&srun_wait=1&theme=basic')
            else:
                self.out_log('登录失败，请联系作者反馈（cnlik@cug.edu.cn）')
        else:
            self.out_log('错误信息{}'.format(reply.errorString()))
            if self.loginTime == 1:
                self.out_log('使用{}登录失败，尝试使用{}再次登录'.format(self.verifyIP, '192.168.167.14'))
                self.login_2_3('http://192.168.167.14/srun_portal_pc?ac_id=1&srun_wait=1&theme=basic')
            elif self.loginTime == 2:
                self.out_log('使用{}登录失败，尝试使用{}再次登录'.format(self.verifyIP, '192.168.167.13'))
                self.login_2_3('http://192.168.167.13/srun_portal_pc?ac_id=1&srun_wait=1&theme=basic')
            else:
                self.out_log('登录失败，请联系作者反馈（cnlik@cug.edu.cn）')

    def out_log(self, log):
        self.textBrowser.append(log)


if __name__ == '__main__':
    if not os.path.exists(os.path.join(get_app_path(), 'run_connectCUG_admin.bat')):
        exePath = os.path.join(get_app_path(), 'ConnectCUG.exe')
        create_batch_file(exePath)
        add_to_startup(os.path.abspath('run_connectCUG_admin.bat'))
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(':/pic/logo.ico'))
    w = ConnectCUG()
    w.show()
    sys.exit(app.exec_())
