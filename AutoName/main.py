import sys
import random
import math
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                            QMessageBox, QGraphicsView, QGraphicsScene, QDesktopWidget)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush

class NameDisplay(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setStyleSheet("background-color: #f0f0f0; border-radius: 10px;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.names = []
        self.current_index = 0
        self.is_final = True  # 初始状态为停止
        self.animation_step = 0
        self.breath_animation = QTimer()
        self.breath_animation.timeout.connect(self.update_breath)
        self.breath_animation.start(16)  # 约60fps的更新率
        
    def update_breath(self):
        self.animation_step = (self.animation_step + 1) % 360
        if not self.is_final:
            self.update_scene()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scene.setSceneRect(0, 0, self.width(), self.height())
        self.update_scene()
        
    def set_names(self, names):
        self.names = names
        self.is_final = True  # 导入后保持停止状态
        self.update_scene()
        
    def update_scene(self):
        self.scene.clear()
        if not self.names:
            return
            
        # 获取场景尺寸
        scene_width = self.width()
        scene_height = self.height()
        
        for i, name in enumerate(self.names):
            if self.is_final and i == self.current_index:
                # 最终选中的名字
                font = QFont()
                font.setFamily("Arial")
                font.setPointSize(200)
                text = self.scene.addText(name, font)
                text.setDefaultTextColor(QColor("#8A2BE2"))  # 紫色
                # 将文字居中显示
                text.setPos(scene_width/2 - text.boundingRect().width()/2,
                          scene_height/2 - text.boundingRect().height()/2)
            else:
                # 随机位置显示其他名字
                x = random.randint(50, max(51, int(scene_width - 100)))
                y = random.randint(50, max(51, int(scene_height - 100)))
                
                # 根据是否是当前显示的名字来决定字体大小
                font = QFont()
                font.setFamily("Arial")
                if i == self.current_index:
                    # 添加呼吸效果
                    breath = math.sin(math.radians(self.animation_step)) * 8
                    font.setPointSize(int(32 + breath))
                else:
                    font.setPointSize(24)
                
                text = self.scene.addText(name, font)
                if i == self.current_index:
                    # 当前显示的名字使用渐变色
                    color_value = int(128 + 127 * math.sin(math.radians(self.animation_step)))
                    text.setDefaultTextColor(QColor(color_value, 0, color_value))
                else:
                    text.setDefaultTextColor(QColor("#2c3e50"))
                text.setPos(x, y)
    
    def update_display(self):
        if self.names:
            self.current_index = (self.current_index + 1) % len(self.names)
            self.update_scene()
    
    def show_final_name(self, index):
        self.is_final = True
        self.current_index = index
        self.update_scene()

class AutoNameSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('自动点名系统')
        
        # 获取屏幕尺寸
        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        screen_height = screen.height()
        
        # 设置窗口大小为屏幕的一半
        window_width = screen_width // 2
        window_height = screen_height // 2
        
        # 计算窗口位置使其居中
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口大小和位置
        self.setGeometry(x, y, window_width, window_height)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #8A2BE2;
                color: white;
                border: none;
                padding: 30px 60px;
                border-radius: 15px;
                font-size: 32px;
                min-width: 300px;
                margin: 20px;
            }
            QPushButton:hover {
                background-color: #9932CC;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLabel {
                color: #2c3e50;
                font-size: 28px;
            }
        """)
        
        # 初始化变量
        self.students = []
        self.current_student = None
        self.is_running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建标题
        title_label = QLabel('自动点名系统')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet('font-size: 48px; font-weight: bold; color: #2c3e50; margin: 30px;')
        layout.addWidget(title_label)
        
        # 创建显示区域
        self.display_view = NameDisplay()
        self.display_view.setMinimumHeight(400)  # 调整显示区域高度
        layout.addWidget(self.display_view)
        
        # 创建总人数显示
        self.total_label = QLabel('总人数: 0')
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setStyleSheet('font-size: 32px; margin: 20px;')
        layout.addWidget(self.total_label)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(40)
        
        self.import_btn = QPushButton('导入名单')
        self.import_btn.clicked.connect(self.import_excel)
        button_layout.addWidget(self.import_btn)
        
        self.start_btn = QPushButton('开始点名')
        self.start_btn.clicked.connect(self.toggle_roll_call)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        
        layout.addLayout(button_layout)
        
    def import_excel(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, '选择Excel文件', '', 'Excel Files (*.xlsx *.xls)')
        
        if file_name:
            try:
                df = pd.read_excel(file_name)
                self.students = df.iloc[:, 0].tolist()
                self.total_label.setText(f'总人数: {len(self.students)}')
                self.start_btn.setEnabled(True)
                self.display_view.set_names(self.students)
                QMessageBox.information(self, '成功', f'成功导入 {len(self.students)} 名学生')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入失败: {str(e)}')
    
    def toggle_roll_call(self):
        if not self.is_running:
            self.is_running = True
            self.is_final = False  # 开始动画
            self.start_btn.setText('停止点名')
            self.timer.start(50)  # 加快更新速度
        else:
            self.is_running = False
            self.is_final = True  # 停止动画
            self.start_btn.setText('开始点名')
            self.timer.stop()
            if self.current_student:
                # 显示最终选中的名字
                self.display_view.show_final_name(self.students.index(self.current_student))
                QMessageBox.information(self, '点名结果', f'被点到的学生: {self.current_student}')
    
    def update_display(self):
        if self.students:
            self.current_student = random.choice(self.students)
            self.display_view.update_display()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AutoNameSystem()
    window.show()
    sys.exit(app.exec_()) 