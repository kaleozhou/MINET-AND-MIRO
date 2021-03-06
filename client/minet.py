#coding:utf-8
import ConfigParser
import os

from PyQt5.QtWidgets import (
    QApplication, QMessageBox, QWidget, QDialog, QLabel, QLineEdit,
    QTextEdit, QRadioButton, QPushButton, QTextBrowser,QTabWidget, QFileDialog,
    QHBoxLayout, QVBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem, QToolButton)

#from PyQt5.QtCore import *
from PyQt5.QtCore import pyqtSignal, Qt, QTranslator
from PyQt5.QtGui import QFont
from threading import Thread
from Queue import Queue
from datetime import datetime
from client import TcpClient, start_P2P_chat_TCP_server, isPortOpen, P2PChatClient, P2P_chat_manager
import sys
reload(sys)
sys.setdefaultencoding('utf8')

class UserDataBox(QWidget):

    def __init__(self, online_user_list=None, main_window=None):
        super(UserDataBox, self).__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.main_window = main_window
        # userDataJson = [
        #     ["user1", u"用户1", "127.0.0.1", "54321"],
        #     # ["user233333", u"红红火火", "127.0.0.1", "54321"],
        #     # ["user233333", u"红红火火", "127.0.0.1", "54321"],
        #     # ["user233333", u"红红火火", "127.0.0.1", "54321"],
        #     # ["user233333", u"红红火火", "127.0.0.1", "54321"],
        #     # ["user233333", u"红红火火", "127.0.0.1", "54321"],
        # ]
        if online_user_list:
            QDialog.__init__(self)
            userNum = len(online_user_list)

            self.resize(400, 110+45*userNum)
            self.setWindowTitle(u'在线用户列表')

            self.MyTable = QTableWidget(userNum, 4)
            self.MyTable.setHorizontalHeaderLabels(['用户名', '昵称', 'IP', '开放端口'])
            self.MyTable.setVerticalHeaderLabels([])

            for index,userData in enumerate(online_user_list):
                newItem = QTableWidgetItem(userData[0])
                newItem.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.MyTable.setItem(index, 0, newItem)

                newItem = QTableWidgetItem(userData[1])
                newItem.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.MyTable.setItem(index, 1, newItem)

                newItem = QTableWidgetItem(userData[2])
                newItem.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.MyTable.setItem(index, 2, newItem)

                newItem = QTableWidgetItem(str(userData[3]))
                newItem.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.MyTable.setItem(index, 3, newItem)

            self.MyTable.resizeColumnsToContents()   # 将列调整到跟内容大小相匹配
            self.MyTable.resizeRowsToContents()      # 将行大小调整到跟内容的大小相匹配

            # 布局和样式
            # 创建窗口部件
            self.widget_frame = QLabel()
            # 窗口标题
            self.title = QLabel('双击可进行P2P聊天')
            self.title.setAlignment(Qt.AlignCenter)

            self.top_layout = QVBoxLayout()
            self.top_layout.addWidget(self.title)
            self.top_layout.addWidget(self.MyTable)
            self.top_layout.setSpacing(10)

            self.widget_frame.setLayout(self.top_layout)

            self.layout_fram = QGridLayout()
            self.layout_fram.addWidget(self.widget_frame, 0, 0, 1, 1)
            self.layout_fram.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self.top_layout)

            self.widget_frame.setObjectName('frame')
            self.title.setObjectName('title')
            self.setStyleSheet(
            '#frame{'
                'background-color: #333333;'
            '}'
            '#title{'
                'color: white;'
                'font-size: 17pt;'
            '}'
            'QWidget {'
                'background-color: #333333;'
                'color: #fffff8;'
            '}'
            'QHeaderView::section {'
                'background-color: #646464;'
                'padding: 4px;'
                'border: 1px solid #fffff8;'
                'font-size: 16pt;'
            '}'
            'QTableWidget {'
                'gridline-color: #fffff8;'
                'font-size: 14pt;'
            '}'
            'QTableWidget QTableCornerButton::section {'
                'background-color: #646464;'
                'border: 1px solid #fffff8;'
            '}'
            )

            # 绑定信号 双击表格项时开始p2p聊天
            self.MyTable.itemDoubleClicked.connect(self.create_P2P_chat_to_user)


    def create_P2P_chat_to_user(self, item):
        # 获取所在行单元格的内容
        def getItemContent(item, index):
            return self.MyTable.item(item.row(), index).text()

        receiver_nickname = getItemContent(item, 1)
        p2p_server_host, p2p_server_port = getItemContent(item, 2), getItemContent(item, 3)
        jdata = {
            "host": p2p_server_host,
            "port": p2p_server_port,
            "nickname": receiver_nickname,
            "need_handshake": True
        }
        # 检查是否已经存在与该用户的对话 如有直接切换过去 没有就创建这个tab
        for secret_id in P2P_chat_manager.P2P_chat_objects:
            P2P_chat_object = P2P_chat_manager.P2P_chat_objects[secret_id]
            if P2P_chat_object['nickname'] == receiver_nickname:
                # 切换到该tabview
                self.main_window.tabView.setCurrentWidget(P2P_chat_object['chat_tab'])
                return
        self.main_window.addTab_to_tabView_signal.emit(jdata)


class MainWindow(QWidget):
    # 声明信号 不能放init中
    add_format_text_to_QTextBrowser_signal = pyqtSignal(dict, QTextBrowser)
    add_format_image_to_QTextBrowser_signal = pyqtSignal(dict, QTextBrowser)
    close_QTextBrowser_signal = pyqtSignal(str, QTextBrowser)
    addTab_to_tabView_signal = pyqtSignal(dict)

    def closeEvent(self, QCloseEvent):
        #print u"程序退出"
        self.__thread_killer = True
        self.client.finish()
        #print u"关闭client"
        self.recv_client.finish()
        #print u"关闭recv_client"
        for secret_id in P2P_chat_manager.P2P_chat_objects:
            P2P_chat_manager.P2P_chat_objects[secret_id]['client'].finish()
        #print u"关闭p2p chat client"

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
#        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("MINET")
        self.resize(500, 300)
        self.font_size = 15

        self.nickname = ""

        # 创建窗口部件
        self.widget_frame = QLabel()

        # 窗口标题
        self.title_fram = QLabel()
        self.title = QLabel('MINET')
        self.title.setAlignment(Qt.AlignCenter)
        self.title_fram.setFixedHeight(100)

        # 登录部分

        self.login_btn_fram = QLabel()
        self.login_input_fram = QLabel()
        self.username_lab = QLabel("用户名：")
        self.password_lab = QLabel("密码：")
        self.nickname_lab = QLabel("昵称：")
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.nickname_edit = QLineEdit()
        self.type_select_login = QRadioButton('登录')
        self.type_select_register = QRadioButton('注册')
        self.login_btn = QPushButton('登录')
        self.register_btn = QPushButton('注册')
        self.login_btn.setFixedWidth(100)
        self.register_btn.setFixedWidth(100)

        # 更换背景图片按钮
        self.select_background_image_file_btn = QToolButton()
        self.select_background_image_file_btn.setText('选择背景图片')
        #self.select_background_image_file_btn.setFixedWidth(150)

        # 显示详细聊天部分
        self.show_online_user_btn = QPushButton('查看在线用户')

        self.tabView = QTabWidget()
        self.group_chat = QTextBrowser()
        # self.P2P_chat = QTextBrowser()
        self.tabView.addTab(self.group_chat, '群聊')

        self.file_line_edit = QLineEdit()
        self.select_file_btn = QToolButton()
        self.select_file_btn.setText('选择图片/文件')
        self.send_file_btn = QToolButton()
        self.send_file_btn.setText('发送')

        self.adjust_font_lab = QLabel('调整文字大小：')
        self.font_smaller_btn = QToolButton()
        self.font_smaller_btn.setText('缩小')
        self.font_bigger_btn = QToolButton()
        self.font_bigger_btn.setText('增大')

        self.chat_msg_edit = QTextEdit()
        self.send_msg_btn = QPushButton('发送')
        self.chat_msg_edit.setMaximumHeight(80)
        self.chat_msg_edit.setPlaceholderText("有什么想说的？")

        # 布局
        # 标题部分
        self.__layout_title = QHBoxLayout()
        self.__layout_title.addWidget(self.title)
        self.title_fram.setLayout(self.__layout_title)

        # 登录部分
        self.login_input_layout = QGridLayout()
        self.login_input_layout.addWidget(self.username_lab, 0, 0, 1, 1)
        self.login_input_layout.addWidget(self.password_lab, 1, 0, 1, 1)
        self.login_input_layout.addWidget(self.nickname_lab, 2, 0, 1, 1)
        self.login_input_layout.addWidget(self.username_edit, 0, 1, 1, 3);
        self.login_input_layout.addWidget(self.password_edit, 1, 1, 1, 3);
        self.login_input_layout.addWidget(self.nickname_edit, 2, 1, 1, 3);
        self.login_input_layout.addWidget(self.type_select_login, 3, 1, 1, 2);
        self.login_input_layout.addWidget(self.type_select_register, 3, 2, 1, 2);
        self.login_input_layout.setContentsMargins(0, 0, 0, 0)

        self.login_btn_layout = QHBoxLayout()
        self.login_btn_layout.addWidget(self.login_btn)
        self.login_btn_layout.addWidget(self.register_btn)
        self.login_btn_layout.setContentsMargins(0, 0, 0, 0)

        self.login_input_fram.setFixedHeight(100)
        self.login_input_fram.setLayout(self.login_input_layout)
        self.login_btn_fram.setLayout(self.login_btn_layout)


        # 登录部分widget
        self.login_layout = QVBoxLayout()
        self.login_layout.addWidget(self.login_input_fram)
        self.login_layout.addWidget(self.login_btn_fram)

        self.login_widget = QLabel()
        self.login_widget.setLayout(self.login_layout)

        # 聊天部分工具

        self.tool_layout = QHBoxLayout()
        self.tool_layout.addWidget(self.select_file_btn)
        self.tool_layout.addWidget(self.file_line_edit)
        self.tool_layout.addWidget(self.send_file_btn)
        self.tool_layout.addWidget(self.adjust_font_lab)
        self.tool_layout.addWidget(self.font_smaller_btn)
        self.tool_layout.addWidget(self.font_bigger_btn)
        self.tool_layout.addWidget(self.select_background_image_file_btn)
        self.tool_widget = QLabel()
        self.tool_widget.setFixedHeight(50)
        self.tool_widget.setLayout(self.tool_layout)

        # 聊天部分widget
        self.chat_layout = QVBoxLayout()
        self.chat_layout.addWidget(self.show_online_user_btn)
        self.chat_layout.addWidget(self.tabView)
        self.chat_layout.addWidget(self.tool_widget)
        self.chat_layout.addWidget(self.chat_msg_edit)
        self.chat_layout.addWidget(self.send_msg_btn)

        self.chat_widget = QLabel()
        self.chat_widget.setLayout(self.chat_layout)

        # 顶部层
        self.top_layout = QVBoxLayout()
        self.top_layout.addWidget(self.title_fram)
        self.top_layout.addWidget(self.login_widget)
        self.top_layout.addWidget(self.chat_widget)
        self.top_layout.setSpacing(10)

        self.widget_frame.setLayout(self.top_layout)

        self.layout_fram = QGridLayout()
        self.layout_fram.addWidget(self.widget_frame, 0, 0, 1, 1)
        self.layout_fram.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout_fram)

        # set object name
        self.widget_frame.setObjectName('frame')
        self.title.setObjectName('title')
        self.tabView.setObjectName('tabView')
        self.group_chat.setObjectName('group_chat')
        # self.P2P_chat.setObjectName('P2P_chat')
        self.chat_msg_edit.setObjectName('chat_msg_edit')
        self.username_lab.setObjectName('username_lab')
        self.password_lab.setObjectName('password_lab')
        self.nickname_lab.setObjectName('nickname_lab')

        # 设置风格
        self.set_style('Images/bg.jpg')

        # 设置字体
        self.set_QTextBrowser_font_size(self.group_chat, 15)

        self.login_btn.setShortcut(Qt.Key_Return)

        # 关联 信号/槽
        self.login_btn.clicked.connect(self.login)
        self.register_btn.clicked.connect(self.register)
        self.send_msg_btn.clicked.connect(self.send_msg)
        self.chat_msg_edit.textChanged.connect(self.detect_return)
        self.type_select_register.toggled.connect(self.toggle_register)
        self.type_select_login.toggled.connect(self.toggle_login)
        self.show_online_user_btn.clicked.connect(self.show_online_user)
        self.select_file_btn.clicked.connect(self.choose_file)
        self.select_background_image_file_btn.clicked.connect(self.choose_background_image_file)
        self.font_smaller_btn.clicked.connect(self.font_smaller)
        self.font_bigger_btn.clicked.connect(self.font_bigger)
        self.send_file_btn.clicked.connect(self.send_file)

        # 绑定信号
        self.add_format_text_to_QTextBrowser_signal.connect(self.add_format_text_to_QTextBrowser)
        self.add_format_image_to_QTextBrowser_signal.connect(self.add_format_image_to_QTextBrowser)
        self.addTab_to_tabView_signal.connect(self.addTab_to_tabView)
        self.close_QTextBrowser_signal.connect(self.close_QTextBrowser)

        # 线程间共享数据队列
        queue_size = 10000
        self.__queue_result = Queue(queue_size)
        self.__queue_error = Queue(queue_size)

        # 强制结束子线程
        self.__thread_killer = False

        self.chat_widget.hide()
        self.type_select_login.click()
        # self.chat_layout_widgets = [self.tabView, self.chat_msg_edit, self.send_msg_btn]
        # self.login_layout_widgets = [self.login_btn_fram, self.login_input_fram]

        # 启动p2p聊天服务器
        # 从配置文件中读取host, port
        cf = ConfigParser.ConfigParser()
        cf.read("server.conf")
        self.self_p2p_server_host = cf.get("P2P_server", "host")
        self.self_p2p_server_port = cf.getint("P2P_server", "port")
        # 寻找可用端口
        while isPortOpen(self.self_p2p_server_host, self.self_p2p_server_port):
            self.self_p2p_server_port += 1
        self.P2P_chat_TCP_server_thread = Thread(target=start_P2P_chat_TCP_server, args=(self.self_p2p_server_host,self.self_p2p_server_port,self))
        self.P2P_chat_TCP_server_thread.start()

        # 启动群聊客户端
        self.client = TcpClient(self)
        self.recv_client = TcpClient(self, is_recv_boardcast=True)
        self.client.handshake(self.self_p2p_server_host, self.self_p2p_server_port)
        self.recv_client.handshake(self.self_p2p_server_host, self.self_p2p_server_port)

        P2P_chat_manager.main_window = self

    def set_QTextBrowser_font_size(self, QTextBrowser, size=15):
        font = QFont()
        font.setFamily("新宋体")
        font.setPointSize(int(size))
        font.setBold(True)
        font.setWeight(75)
        QTextBrowser.setFont(font)

    # 当前QTextBrowser中字体变小
    def font_smaller(self):
        self.font_size -= 1
        self.set_QTextBrowser_font_size(self.tabView.currentWidget(), self.font_size)

    # # 当前QTextBrowser中字体变大
    def font_bigger(self):
        self.font_size += 1
        self.set_QTextBrowser_font_size(self.tabView.currentWidget(), self.font_size)

    # 选择背景图片
    def choose_background_image_file(self):
        path = QFileDialog.getOpenFileName()
        if path[0] != '':
            self.set_style(path[0])

    def set_style(self, background_img_name="Images/bg"):
        self.setStyleSheet(
            'QLabel{'
                'color: white;'
            '}'
            '#frame{'
                'border-image: url(' + background_img_name + ');'
            '}'
            '#title{'
                'color: white;'
                'font-size: 20pt;'
            '}'
            '#open_tool{'
                'color: black;'
            '}'
            '#mode_fram{'
                # 'border-top: 1px solid rgba(20, 20, 20, 100);'
                # 'border-bottom: 1px solid rgba(20, 20, 20, 100);'
                'background: rgba(200, 200, 200, 40);'
            '}'
            '#ln_open_tool, #ln_path{'
                'border-top-left-radius:    2px;'
                'border-bottom-left-radius: 2px;'
            '}'
            '#ln_pattern{'
                'border-radius: 2px;'
            '}'
            '#state{'
                'background: rgba(200, 200, 200, 40);'
                'border-radius: 2px;'
                'padding: 1px;'
                'color: rgb(240, 240, 240);'
            '}'
            'QTabBar::tab {'
                'border: 0;'
                'width:  110px;'
                'height: 40px;'
                'margin: 0 2px 0 0;'        # top right bottom left
                # 'border-top-left-radius: 5px;'
                # 'border-top-right-radius: 5px;'
                'color: rgb(200, 255, 255;);'
            '}'
            'QTabBar::tab:selected{'
                'background: rgba(25, 255, 255, 40);'
                'border-left: 1px solid rgba(255, 255, 255, 200);'
                'border-top: 1px solid rgba(255, 255, 255, 200);'
                'border-right: 1px solid rgba(255, 255, 255, 200);'
            '}'
            'QTabWidget:pane {'
                'border: 1px solid rgba(255, 255, 255, 200);'
                'background: rgba(0, 0, 0, 80);'
            '}'
            'QTextBrowser{'
                'background: rgba(0, 0, 0, 0);'
                'color: white;'
                'border: 0;'
            '}'
            '#chat_msg_edit{'
                'background: rgba(0, 0, 0, 40);'
                'border: 1px solid rgba(220, 220, 220, 200);'
                'color: white;'
                'height: 10px;'
            '}'
            'QRadioButton{'
                'background: rgba(0, 0, 0, 0);'
                'color: white;'
            '}'
            'QLineEdit{'
                'background: rgba(0, 0, 0, 40);'
                'border: 1px solid rgba(220, 220, 220, 200);'
                'color: white;'
                'height: 20px;'
            '}'
            'QPushButton{'
                'background: rgba(0, 0, 0, 100);'
                'border-radius: 15px;'
                'height: 25px;'
                'color: white;'
            '}'
            'QPushButton::hover{'
                'background: rgba(0, 0, 0, 150);'
            '}'
            'QToolButton{'
                'background: rgba(100, 100, 100, 100);'
                'color: white;'
                'border-top-right-radius:    2px;'
                'border-bottom-right-radius: 2px;'
            '}'
            'QToolButton::hover{'
                'background: rgba(0, 0, 0, 150);'
            '}'
            )

    # 选择打开文件工具
    def choose_file(self):
        path = QFileDialog.getOpenFileName()
        if path[0] != '':
            self.file_line_edit.setText(path[0])

    # 发送文件/图片
    def send_file(self):

        def is_image_file(filepath):
            return filepath.endswith("png") or filepath.endswith("jpg") or filepath.endswith("jpeg") or filepath.endswith("gif")

        filepath = self.file_line_edit.text()
        # 获取widget的名称
        currentWidgetName = self.tabView.currentWidget().objectName()

        if os.path.isfile(filepath):
            #print u"发送文件/图片:", filepath
            # 群聊
            if currentWidgetName == 'group_chat':
                if is_image_file(filepath):
                    self.client.send_file(filepath, "image")
                    jdata = {"store_filename": filepath, "nickname": u"自己"}
                    self.add_format_image_to_QTextBrowser(jdata, self.group_chat)
                else:
                    self.client.send_file(filepath)
                    jdata = {"content": u"成功发送文件\n", "nickname": u"自己"}
                    self.add_format_text_to_QTextBrowser(jdata, self.group_chat)
            # P2P聊
            else:
                objs = P2P_chat_manager.P2P_chat_objects
                for secret_id in objs:
                    # #print objs[secret_id]
                    if secret_id == currentWidgetName:
                        sender_client = objs[secret_id].get('sender')
                        chat_tab = objs[secret_id].get('chat_tab')
                        if is_image_file(filepath):
                            jdata = {"store_filename": filepath, "nickname": u"自己"}
                            self.add_format_image_to_QTextBrowser(jdata, chat_tab)
                            sender_client.send_file(filepath, "image")
                        else:
                            jdata = {"content": u"成功发送文件\n", "nickname": u"自己"}
                            self.add_format_text_to_QTextBrowser(jdata, chat_tab)
                            sender_client.send_file(filepath)
            self.file_line_edit.setText("")

    # 检测回车，检测到就发送
    def detect_return(self):
        content = self.chat_msg_edit.toPlainText()
        # #print "%r" % content
        if content.endswith('\n'):
            self.send_msg_btn.click()

    #　切换到注册页
    def toggle_register(self):
        self.login_btn.hide()
        self.register_btn.show()
        self.nickname_lab.show()
        self.nickname_edit.show()

    #　切换到登录页
    def toggle_login(self):
        self.login_btn.show()
        self.register_btn.hide()
        self.nickname_lab.hide()
        self.nickname_edit.hide()

    # 查看在线用户（弹出窗口）
    def show_online_user(self):
        # 查询在线用户
        try:
            online_user_list = self.client.get_online_user()
            #print online_user_list
            # 显示新窗口
            self.tableViewWindow = UserDataBox(online_user_list=online_user_list, main_window=self)
            self.tableViewWindow.show()
        except Exception, e:
            #print e
            QMessageBox.warning(
                self,
                "提示",
                "查询失败TAT",
                QMessageBox.Yes)

    def login(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        # #print "username:"+username
        # #print "password:"+password
        try:
            assert self.client.login(username, password)
            assert self.recv_client.login(username, password)
            if self.client.nickname:
                self.nickname = self.client.nickname
                self.setWindowTitle(u"MINET - 用户" + self.client.nickname)
            QMessageBox.information(
                self,
                "提示",
                "登录成功！",
                QMessageBox.Yes)
            if self.chat_widget.isHidden():
                self.login_widget.hide()
                self.chat_widget.show()
                self.resize(1000, 800)
            else:
                self.chat_widget.hide()
                self.resize(500, 300)
            self.start_recv_msg()
        except Exception, e:
            #print e
            QMessageBox.warning(
                self,
                "提示",
                "登录失败！",
                QMessageBox.Yes)

    def register(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        nickname = self.nickname_edit.text()
        # #print "username:"+username
        # #print "password:"+password
        # #print "nickname:"+nickname
        try:
            assert self.client.register(username, password, nickname)
            QMessageBox.information(
                self,
                "提示",
                "注册完成！",
                QMessageBox.Yes)
            # 转到登录页
            self.type_select_login.click()
        except Exception, e:
            #print e
            QMessageBox.warning(
                self,
                "提示",
                "注册失败！",
                QMessageBox.Yes)

    # 往QTextBrowser中添加格式化的文本
    def add_format_text_to_QTextBrowser(self, jdata, QTextBrowserObject):
        time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        text = jdata.get("content", "")
        nickname = jdata.get("nickname", "")
        msg = u"%s %s\n%s\n" % (nickname.encode("utf-8"), time.encode("utf-8"), text.encode("utf-8"))
        QTextBrowserObject.insertPlainText(msg)
        # QTextBrowserObject.setText("%s%s"%(QTextBrowserObject.toPlainText(), msg))
        QTextBrowserObject.moveCursor(QTextBrowserObject.textCursor().End)

    # 往QTextBrowser中添加格式化的图片
    def add_format_image_to_QTextBrowser(self, jdata, QTextBrowserObject):
        time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        nickname = jdata.get("nickname", "")
        store_filename = jdata.get("store_filename")
        msg_head = u"%s %s\n" % (nickname.encode("utf-8"), time.encode("utf-8"))
        QTextBrowserObject.insertPlainText(msg_head)
        QTextBrowserObject.moveCursor(QTextBrowserObject.textCursor().End)
        QTextBrowserObject.insertHtml('<img src="%s"></img>' % store_filename)
        QTextBrowserObject.moveCursor(QTextBrowserObject.textCursor().End)
        QTextBrowserObject.insertPlainText("\n\n")
        QTextBrowserObject.moveCursor(QTextBrowserObject.textCursor().End)

    # 在tabview中关闭这个tab（会话结束）
    def close_QTextBrowser(self, secret_id, QTextBrowserObject):
        QMessageBox.information(
                self,
                "提示",
                u"%s断开连接，会话结束！" % P2P_chat_manager.P2P_chat_objects[secret_id].get("nickname"),
                QMessageBox.Yes)
        tab_number = P2P_chat_manager.P2P_chat_objects[secret_id].get("tab_number")
        if tab_number:
            self.tabView.removeTab(tab_number)
        P2P_chat_manager.P2P_chat_objects.pop(secret_id)

    # 往tabview中添加一个tab 并建立P2P_chat_client
    def addTab_to_tabView(self, jdata):
        host = jdata.get("host")
        port = jdata.get("port")
        nickname = jdata.get("nickname")
        secret_id = jdata.get("secret_id")
        # 创建新的tab
        chat_tab = QTextBrowser()
        self.set_QTextBrowser_font_size(chat_tab)
        tab_number = self.tabView.addTab(chat_tab, nickname)
        # 创建chat client 没有secret id 构造时会随机生成一个
        if secret_id:
            P2P_chat_client = P2PChatClient(host, port, nickname, self.client.nickname, self, chat_tab, secret_id)
        else:
            P2P_chat_client = P2PChatClient(host, port, nickname, self.client.nickname, self, chat_tab)
            secret_id = P2P_chat_client.secret_id
        P2P_chat_manager.P2P_chat_objects[secret_id]['chat_tab'] = chat_tab
        P2P_chat_manager.P2P_chat_objects[secret_id]['client'] = P2P_chat_client
        P2P_chat_manager.P2P_chat_objects[secret_id]['tab_number'] = tab_number
        # 把widget名称改成secret id
        chat_tab.setObjectName(secret_id)
        # 切换到该tabview
        self.tabView.setCurrentWidget(chat_tab)
        if jdata.get("need_handshake"):
            # 进行握手
            P2P_chat_client.handshake(self.self_p2p_server_host, self.self_p2p_server_port)

        # 在界面提示连接成功
        jdata = {"content": u"与%s建立P2P连接完成\n" % nickname, "nickname": u"【系统消息】"}
        P2P_chat_manager.main_window.add_format_text_to_QTextBrowser_signal.emit(jdata, chat_tab)

    def send_msg(self):
        # 获取widget的名称
        currentWidgetName = self.tabView.currentWidget().objectName()
        #print u"currentWidgetName:", currentWidgetName
        raw_content = self.chat_msg_edit.toPlainText()
        # 内容后面统一换行
        if not raw_content.endswith('\n'):
            raw_content += '\n'
        content = raw_content.replace('\n', '\\n')
        self.chat_msg_edit.clear()

        if currentWidgetName == 'group_chat':
            try:
                assert self.client.broadcast(content)
                jdata = {"content": raw_content, "nickname": u"自己"}
                self.add_format_text_to_QTextBrowser(jdata, self.group_chat)
            except Exception, e:
                #print "send_msg:", e
                QMessageBox.warning(
                    self,
                    "提示",
                    "发送失败！",
                    QMessageBox.Yes)
        else:
            try:
                jdata = {"content": raw_content, "nickname": u"自己"}
                objs = P2P_chat_manager.P2P_chat_objects
                for secret_id in objs:
                    # #print objs[secret_id]
                    if secret_id == currentWidgetName:
                        self.add_format_text_to_QTextBrowser(jdata, objs[secret_id].get('chat_tab'))
                        objs[secret_id].get('sender').chat(content)
            except Exception, e:
                #print "send_msg:", e
                QMessageBox.warning(
                    self,
                    "提示",
                    "发送失败！",
                    QMessageBox.Yes)

    def start_recv_msg(self):
        def start():
            while True:
                if self.__thread_killer:
                    #print u"停止接收信息"
                    return True
                jdata = self.recv_client.receive_one_msg()
                # 收到广播消息
                if jdata.get("action") == "broadcast":
                    #self.add_format_text_to_group_chat(jdata['content'])
                    self.add_format_text_to_QTextBrowser_signal.emit(jdata, self.group_chat)
                    #print u"%s发来消息:%s" % (jdata['nickname'], jdata['content'])
                # 收到文件广播
                if jdata.get("action") == "broadcast_file":
                    # 开始接收文件
                    store_filename = self.recv_client.recv_file(jdata.get('filename'), jdata.get('file_type'))
                    jdata['store_filename'] = store_filename
                    # 如果是图片 显示出来
                    if jdata.get("file_type") == 'image':
                        #print u"接收到图片"
                        self.add_format_image_to_QTextBrowser_signal.emit(jdata, self.group_chat)
                    else:
                        #print u"接收到文件"
                        jdata['content'] = u"已接收%s发来的文件，保存路径为:%s\n" % (jdata['nickname'], store_filename)
                        jdata['nickname'] = u"【系统消息】"
                        self.add_format_text_to_QTextBrowser_signal.emit(jdata, self.group_chat)

        self.recv_msg_thread = Thread(target=start)
        self.recv_msg_thread.start()
        return True


# 程序入口
if __name__ == '__main__':
    import sys
    translator = QTranslator()
    translator.load('qt_zh_CN.qm')
    app = QApplication(sys.argv)
    app.installTranslator(translator)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
