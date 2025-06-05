import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, 
                            QLabel, QDesktopWidget, QMenuBar, QMenu, QAction, QStatusBar,
                            QHBoxLayout, QLineEdit, QMessageBox, QColorDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

class SecondWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('友好的提醒')
        self.setGeometry(400, 300, 400, 300)
        
        # 设置窗口背景色
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f6fa;
            }
        """)
        
        # 创建标签显示"你好"
        label = QLabel('你好', self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #2c3e50;
                font-weight: bold;
                padding: 20px;
            }
        """)
        
        # 设置布局
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

class MessageWindow(QWidget):
    def __init__(self, message):
        super().__init__()
        self.setWindowTitle('消息')
        self.setGeometry(400, 300, 300, 200)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)  # 确保窗口显示在最前面
        
        # 计算窗口位置（屏幕右三分之一处）
        screen = QDesktopWidget().screenGeometry()
        window_width = 300
        window_height = 200
        x = int(screen.width() * 2/3) - window_width//2  # 右三分之一位置
        y = (screen.height() - window_height) // 2  # 垂直居中
        self.move(x, y)
        
        # 设置窗口背景色
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f6fa;
            }
        """)
        
        # 创建标签显示消息
        label = QLabel(message, self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #2c3e50;
                font-weight: bold;
                padding: 20px;
            }
        """)
        
        # 设置布局
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
        
        # 显示窗口
        self.show()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('主窗口')
        self.setFixedSize(800, 800)
        
        # 初始化窗口列表
        self.open_windows = []
        
        # 设置窗口背景色
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
        """)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('就绪')
        
        # 将窗口移动到屏幕中央
        self.center()
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        
        # 创建搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('搜索...')
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 16px;
                border: 2px solid #3498db;
                border-radius: 10px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #2980b9;
            }
        """)
        main_layout.addWidget(self.search_box)
        
        # 创建按钮容器
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setSpacing(20)
        
        # 创建按钮
        self.btn_second = QPushButton('第二窗口', self)
        self.btn_dingzhen = QPushButton('关闭', self)
        self.btn_close = QPushButton('丁真', self)
        self.btn_color = QPushButton('更改颜色', self)
        self.btn_timer = QPushButton('开始计时', self)
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                font-size: 24px;
                padding: 20px;
                margin: 10px;
                min-width: 250px;
                min-height: 80px;
                border-radius: 15px;
                background-color: #3498db;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
                border: 2px solid #1a5276;
            }
            QPushButton:pressed {
                background-color: #2471a3;
                padding-top: 22px;
                padding-bottom: 18px;
            }
        """
        self.btn_second.setStyleSheet(button_style)
        self.btn_dingzhen.setStyleSheet(button_style)
        self.btn_close.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                padding: 20px;
                margin: 10px;
                min-width: 250px;
                min-height: 80px;
                border-radius: 15px;
                background-color: #e74c3c;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
                border: 2px solid #922b21;
            }
            QPushButton:pressed {
                background-color: #a93226;
                padding-top: 22px;
                padding-bottom: 18px;
            }
        """)
        self.btn_color.setStyleSheet(button_style)
        self.btn_timer.setStyleSheet(button_style)
        
        # 添加按钮到布局
        button_layout.addWidget(self.btn_second)
        button_layout.addWidget(self.btn_dingzhen)
        button_layout.addWidget(self.btn_close)
        button_layout.addWidget(self.btn_color)
        button_layout.addWidget(self.btn_timer)
        
        main_layout.addWidget(button_container)
        
        # 连接按钮信号
        self.btn_second.clicked.connect(self.open_second_window)
        self.btn_dingzhen.clicked.connect(self.close_all_windows)
        self.btn_close.clicked.connect(self.show_dingzhen)
        self.btn_color.clicked.connect(self.change_color)
        self.btn_timer.clicked.connect(self.toggle_timer)
        
        # 初始化计时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer_running = False
        self.seconds = 0
        
        # 初始化第二个窗口
        self.second_window = None

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close_all_windows)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        color_action = QAction('更改颜色', self)
        color_action.triggered.connect(self.change_color)
        edit_menu.addAction(color_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def new_file(self):
        self.statusBar.showMessage('新建文件...', 2000)

    def show_about(self):
        QMessageBox.about(self, '关于', '这是一个示例程序\n版本 1.0')

    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {color.name()};
                }}
            """)

    def toggle_timer(self):
        if not self.timer_running:
            self.timer.start(1000)  # 每秒更新一次
            self.btn_timer.setText('停止计时')
            self.timer_running = True
        else:
            self.timer.stop()
            self.btn_timer.setText('开始计时')
            self.timer_running = False
            self.seconds = 0
            self.statusBar.showMessage('计时已停止')

    def update_timer(self):
        self.seconds += 1
        minutes = self.seconds // 60
        seconds = self.seconds % 60
        self.statusBar.showMessage(f'计时: {minutes:02d}:{seconds:02d}')

    def center(self):
        # 获取屏幕几何信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口几何信息
        size = self.geometry()
        # 计算窗口居中位置
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        # 移动窗口
        self.move(x, y)

    def close_all_windows(self):
        # 关闭所有打开的窗口
        for window in self.open_windows:
            if window and window.isVisible():
                window.close()
        # 关闭主窗口
        self.close()

    def open_second_window(self):
        if not self.second_window:
            self.second_window = SecondWindow()
            self.open_windows.append(self.second_window)
        self.second_window.show()

    def show_dingzhen(self):
        # 创建新的消息窗口实例
        self.message_window = MessageWindow("雪豹闭嘴")
        self.open_windows.append(self.message_window)
        # 确保窗口显示
        self.message_window.raise_()
        self.message_window.activateWindow()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
