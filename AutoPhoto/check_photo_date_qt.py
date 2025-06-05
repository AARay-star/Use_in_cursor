import os
import shutil
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import logging
import glob
import ffmpeg
import subprocess
import sys
import json
from pillow_heif import register_heif_opener, HeifFile
import win32file
import win32con
import pywintypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox,
                            QTabWidget, QTextEdit, QProgressBar, QCheckBox, QGroupBox, QDesktopWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 注册HEIC支持
register_heif_opener()

# 设置默认检查目录
DEFAULT_CHECK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Check')
NO_INFO_DIR = os.path.join(DEFAULT_CHECK_DIR, 'NoInformation')
NO_VIDEO_INFO_DIR = os.path.join(DEFAULT_CHECK_DIR, 'NoVideoInformation')
BIG_VIDEO_DIR = os.path.join(DEFAULT_CHECK_DIR, 'BigVideo')
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg-7.1.1', 'bin')

# 确保必要的目录存在
for directory in [DEFAULT_CHECK_DIR, NO_INFO_DIR, NO_VIDEO_INFO_DIR, BIG_VIDEO_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")

def get_log_file():
    """获取新的日志文件路径"""
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
            print(f"创建日志目录: {LOG_DIR}")

        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(LOG_DIR, f'photo_check_{current_time}.txt')
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== 检查记录文件创建时间: {current_time} ===\n")
        
        log_files = glob.glob(os.path.join(LOG_DIR, 'photo_check_*.txt'))
        log_files.sort(reverse=True)
        
        for old_file in log_files[3:]:
            try:
                os.remove(old_file)
            except Exception as e:
                print(f"删除旧文件失败: {str(e)}")
        
        return log_file
    except Exception as e:
        print(f"创建日志文件时出错: {str(e)}")
        backup_log_dir = DEFAULT_CHECK_DIR
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_log_file = os.path.join(backup_log_dir, f'photo_check_{current_time}.txt')
        
        with open(backup_log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== 检查记录文件创建时间: {current_time} ===\n")
        
        return backup_log_file

def write_to_log(log_file, content):
    """写入内容到日志文件"""
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(content + '\n')
    except Exception as e:
        print(f"写入日志文件时出错: {str(e)}")

def check_ffmpeg():
    """检查ffmpeg是否已安装"""
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
            
        ffprobe_path = os.path.join(FFMPEG_DIR, 'ffprobe.exe')
        if os.path.exists(ffprobe_path):
            result = subprocess.run([ffprobe_path, '-version'], capture_output=True, text=True)
            return result.returncode == 0
            
        return False
    except FileNotFoundError:
        ffprobe_path = os.path.join(FFMPEG_DIR, 'ffprobe.exe')
        if os.path.exists(ffprobe_path):
            try:
                result = subprocess.run([ffprobe_path, '-version'], capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        return False

def get_ffprobe_path():
    """获取ffprobe的路径"""
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'ffprobe'
    except FileNotFoundError:
        pass
        
    ffprobe_path = os.path.join(FFMPEG_DIR, 'ffprobe.exe')
    if os.path.exists(ffprobe_path):
        return ffprobe_path
        
    return None

class CheckThread(QThread):
    """检查线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, directory, move_no_info, move_big_video):
        super().__init__()
        self.directory = directory
        self.move_no_info = move_no_info
        self.move_big_video = move_big_video
        # 确保 checker 在 MediaDateChecker 定义之后被创建
        self.checker = MediaDateChecker(directory)

    def run(self):
        try:
            print("检查线程启动...")
            results = self.checker.scan_directory(
                move_no_info=self.move_no_info,
                move_big_video=self.move_big_video
            )
            print("检查线程完成.")
            self.finished.emit(results)
        except Exception as e:
            print(f"检查线程出错: {str(e)}")
            self.error.emit(str(e))

class UpdateDatesThread(QThread):
    """更新日期线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int, int)
    error = pyqtSignal(str)

    def __init__(self, files_to_update):
        super().__init__()
        self.files_to_update = files_to_update

    def run(self):
        success_count = 0
        fail_count = 0
        skipped_count = 0

        for path, date_obj, date_type in self.files_to_update:
            try:
                if not os.path.exists(path):
                    self.progress.emit(f"文件不存在: {path}")
                    skipped_count += 1
                    continue

                wintime = pywintypes.Time(date_obj)
                handle = win32file.CreateFile(
                    path,
                    win32con.GENERIC_WRITE,
                    0, None, win32con.OPEN_EXISTING,
                    win32con.FILE_ATTRIBUTE_NORMAL, None
                )

                win32file.SetFileTime(handle, wintime, wintime, wintime)
                handle.Close()

                success_count += 1
                self.progress.emit(f"成功修改文件日期: {path} -> {date_obj} (来源: {date_type})")

            except Exception as e:
                fail_count += 1
                self.progress.emit(f"修改文件日期失败: {path} - {str(e)}")

        self.finished.emit(success_count, fail_count, skipped_count)

class MediaDateChecker:
    def __init__(self, directory):
        self.directory = directory
        self.supported_image_formats = ['.jpg', '.jpeg', '.tiff', '.tif', '.png', '.heic', '.heif']
        self.supported_video_formats = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm']
        self.date_tags = [
            'DateTimeOriginal',  # 原始拍摄时间
            'DateTimeDigitized', # 数字化时间
            'DateTime',          # 修改时间
        ]
        self.has_ffmpeg = check_ffmpeg()
        self.ffprobe_path = get_ffprobe_path()
        self.bitrate_threshold = 20000  # 比特率阈值（kbps）
        
    def get_exif_date(self, image_path):
        """获取图片的EXIF日期信息"""
        try:
            ext = os.path.splitext(image_path)[1].lower()
            
            # 特殊处理HEIC格式
            if ext == '.heic':
                try:
                    print(f"\n开始处理HEIC文件: {image_path}")
                    
                    # 从文件名获取日期
                    filename = os.path.basename(image_path)
                    try:
                        # 尝试从文件名解析日期（格式：YYYY-MM-DD HHMMSS）
                        date_str = filename.split('.')[0]  # 移除扩展名
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H%M%S')
                        print(f"从文件名获取到日期: {date_str}")
                        return date_obj.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError as e:
                        print(f"从文件名解析日期失败: {str(e)}")
                    
                    # 使用HeifFile直接读取HEIC文件
                    try:
                        heif_file = HeifFile(image_path)
                        print("成功打开HEIC文件")
                        
                        # 尝试从元数据中获取日期
                        metadata = heif_file.metadata
                        if metadata:
                            print("元数据内容:", metadata)
                            
                            # 尝试不同的日期标签
                            date_tags = [
                                'DateTimeOriginal',
                                'DateTimeDigitized',
                                'DateTime',
                                'CreateDate',
                                'ModifyDate',
                                'DateCreated',
                                'DateModified',
                                'DateTimeCreated',
                                'DateTimeModified',
                                'ContentCreateDate',
                                'ContentModifyDate'
                            ]
                            
                            for tag in date_tags:
                                if tag in metadata:
                                    date_str = metadata[tag]
                                    print(f"找到日期标签 {tag}: {date_str}")
                                    try:
                                        # 尝试不同的日期格式
                                        for fmt in [
                                            '%Y:%m:%d %H:%M:%S',      # 2024:05:18 19:26:20
                                            '%Y-%m-%d %H:%M:%S',      # 2024-05-18 19:26:20
                                            '%Y/%m/%d %H:%M:%S',      # 2024/05/18 19:26:20
                                            '%Y:%m:%d %H:%M:%S%z',    # 2024:05:18 19:26:20+0800
                                            '%Y-%m-%d %H:%M:%S%z',    # 2024-05-18 19:26:20+0800
                                            '%Y/%m/%d %H:%M:%S%z',    # 2024/05/18 19:26:20+0800
                                            '%Y:%m:%d %H:%M:%S.%f',   # 2024:05:18 19:26:20.123
                                            '%Y-%m-%d %H:%M:%S.%f',   # 2024-05-18 19:26:20.123
                                            '%Y/%m/%d %H:%M:%S.%f',   # 2024/05/18 19:26:20.123
                                            '%Y:%m:%d %H:%M:%S.%f%z', # 2024:05:18 19:26:20.123+0800
                                            '%Y-%m-%d %H:%M:%S.%f%z', # 2024-05-18 19:26:20.123+0800
                                            '%Y/%m/%d %H:%M:%S.%f%z'  # 2024/05/18 19:26:20.123+0800
                                        ]:
                                            try:
                                                date_obj = datetime.strptime(date_str, fmt)
                                                print(f"成功解析日期: {date_str} -> {date_obj}")
                                                return date_obj.strftime('%Y-%m-%d %H:%M:%S')
                                            except ValueError:
                                                continue
                                    except Exception as e:
                                        print(f"解析日期时出错: {str(e)}")
                                        continue
                        else:
                            print("未找到元数据")
                    except Exception as e:
                        print(f"读取HEIC文件时出错: {str(e)}")
                    
                    return None
                except Exception as e:
                    print(f"处理HEIC文件 {image_path} 时出错: {str(e)}")
                    return None
            
            # 处理其他格式
            try:
                image = Image.open(image_path)
                if not hasattr(image, '_getexif') or image._getexif() is None:
                    print(f"文件 {image_path} 没有EXIF数据")
                    return None
                    
                exif = image._getexif()
                date_info = None
                
                for tag_id in exif:
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in self.date_tags:
                        date_info = exif[tag_id]
                        print(f"从EXIF数据中找到日期: {date_info}")
                        break
                        
                return date_info
            except Exception as e:
                print(f"处理图片 {image_path} 时出错: {str(e)}")
                return None
                
        except Exception as e:
            print(f"处理图片 {image_path} 时出错: {str(e)}")
            return None

    def get_video_date(self, video_path):
        """获取视频的创建媒体时间"""
        if not self.has_ffmpeg or not self.ffprobe_path:
            return None
            
        try:
            # 使用ffprobe获取视频元数据
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_entries', 'format=tags',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ffprobe处理视频失败: {result.stderr}")
                return None
                
            # 解析ffprobe输出
            metadata = json.loads(result.stdout)
            
            # 尝试获取创建媒体时间
            tags = metadata.get('format', {}).get('tags', {})
            creation_time = None
            
            # 尝试不同的标签名
            for tag in ['creation_time', 'date', 'date_created', 'creation_date']:
                if tag in tags:
                    creation_time = tags[tag]
                    break
            
            if creation_time:
                try:
                    # 尝试解析不同格式的日期
                    for fmt in [
                        '%Y-%m-%d %H:%M:%S',  # 2024-03-14 15:30:00
                        '%Y-%m-%dT%H:%M:%S.%fZ',  # 2024-03-14T15:30:00.000Z
                        '%Y-%m-%dT%H:%M:%S',  # 2024-03-14T15:30:00
                        '%Y:%m:%d %H:%M:%S',  # 2024:03:14 15:30:00
                        '%Y/%m/%d %H:%M:%S',  # 2024/03/14 15:30:00
                        '%Y-%m-%d'  # 2024-03-14
                    ]:
                        try:
                            date_obj = datetime.strptime(creation_time, fmt)
                            return date_obj.strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue
                except Exception as e:
                    print(f"解析视频日期失败: {str(e)}")
                    pass
                    
            return None
        except Exception as e:
            print(f"处理视频 {video_path} 时出错: {str(e)}")
            return None

    def get_video_bitrate(self, video_path):
        """获取视频的比特率（kbps）"""
        if not self.has_ffmpeg or not self.ffprobe_path:
            return None
            
        try:
            # 使用ffprobe获取视频比特率
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ffprobe处理视频失败: {result.stderr}")
                return None
                
            # 解析ffprobe输出
            metadata = json.loads(result.stdout)
            
            # 获取比特率（bps）并转换为kbps
            bitrate = metadata.get('format', {}).get('bit_rate')
            if bitrate:
                return int(int(bitrate) / 1000)  # 转换为kbps
                
            return None
        except Exception as e:
            print(f"获取视频比特率时出错: {str(e)}")
            return None

    def check_media(self, file_path):
        """检查媒体文件的日期信息"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in self.supported_image_formats:
            date = self.get_exif_date(file_path)
            if date:
                try:
                    # 尝试解析日期字符串
                    if isinstance(date, str):
                        # 如果已经是字符串格式，直接返回
                        return True, date, "拍摄日期", None
                    else:
                        # 如果是其他格式，尝试解析
                        date_obj = datetime.strptime(date, '%Y:%m:%d %H:%M:%S')
                        return True, date_obj.strftime('%Y-%m-%d %H:%M:%S'), "拍摄日期", None
                except ValueError as e:
                    print(f"解析日期字符串时出错: {str(e)}")
                    return False, "日期格式无效", "拍摄日期", None
            return False, "未找到拍摄日期信息", "拍摄日期", None
            
        elif ext in self.supported_video_formats:
            if not self.has_ffmpeg:
                return False, "未安装ffmpeg，无法处理视频", "创建媒体时间", None
            date = self.get_video_date(file_path)
            bitrate = self.get_video_bitrate(file_path)
            if date:
                return True, date, "创建媒体时间", bitrate
            return False, "未找到创建媒体时间", "创建媒体时间", bitrate
            
        return False, "不支持的文件格式", "未知", None

    def move_to_no_info(self, file_path):
        """移动文件到NoInformation或NoVideoInformation文件夹"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            target_dir = NO_VIDEO_INFO_DIR if ext in self.supported_video_formats else NO_INFO_DIR
            
            file_name = os.path.basename(file_path)
            new_path = os.path.join(target_dir, file_name)
            
            # 如果文件已存在，添加序号
            counter = 1
            name, ext = os.path.splitext(file_name)
            while os.path.exists(new_path):
                new_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                counter += 1
                
            shutil.move(file_path, new_path)
            return new_path
        except Exception as e:
            print(f"移动文件 {file_path} 时出错: {str(e)}")
            return None

    def move_to_big_video(self, video_path):
        """移动大视频到BigVideo文件夹"""
        try:
            file_name = os.path.basename(video_path)
            new_path = os.path.join(BIG_VIDEO_DIR, file_name)
            
            # 如果文件已存在，添加序号
            counter = 1
            name, ext = os.path.splitext(file_name)
            while os.path.exists(new_path):
                new_path = os.path.join(BIG_VIDEO_DIR, f"{name}_{counter}{ext}")
                counter += 1
                
            shutil.move(video_path, new_path)
            return new_path
        except Exception as e:
            print(f"移动视频 {video_path} 时出错: {str(e)}")
            return None

    def scan_directory(self, move_no_info=False, move_big_video=False):
        """扫描目录中的所有媒体文件"""
        results = {
            'with_date': [],
            'without_date': [],
            'big_videos': [],  # 新增：大视频列表
            'livp_files': []   # 新增：LIVP文件列表
        }
        
        for root, _, files in os.walk(self.directory):
            # 跳过NoInformation、NoVideoInformation和BigVideo文件夹
            if NO_INFO_DIR in root or NO_VIDEO_INFO_DIR in root or BIG_VIDEO_DIR in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # 统计LIVP文件
                if ext == '.livp':
                    results['livp_files'].append(file_path)
                    continue
                
                if ext in self.supported_image_formats or ext in self.supported_video_formats:
                    has_date, date_info, date_type, bitrate = self.check_media(file_path)
                    
                    # 检查视频比特率
                    if ext in self.supported_video_formats and move_big_video and bitrate and bitrate > self.bitrate_threshold:
                        new_path = self.move_to_big_video(file_path)
                        if new_path:
                            results['big_videos'].append((new_path, f"{bitrate} kbps"))
                        continue
                    
                    if has_date:
                        results['with_date'].append((file_path, date_info, date_type, bitrate))
                    else:
                        if move_no_info:
                            new_path = self.move_to_no_info(file_path)
                            if new_path:
                                results['without_date'].append((new_path, date_info, date_type, bitrate))
                        else:
                            results['without_date'].append((file_path, date_info, date_type, bitrate))
        
        return results

    def print_report(self, results, log_file):
        """打印检查报告"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 准备报告内容
            report = []
            report.append(f"\n=== 媒体文件日期检查报告 ({current_time}) ===")
            report.append(f"检查目录: {self.directory}")
            
            # 显示LIVP文件信息
            if results['livp_files']:
                report.append(f"\nLIVP文件 ({len(results['livp_files'])}个):")
                for path in results['livp_files']:
                    report.append(f"文件: {path}")
                    report.append("")
            
            # 显示大视频信息
            if results['big_videos']:
                report.append(f"\n大视频文件 ({len(results['big_videos'])}个):")
                for path, bitrate in results['big_videos']:
                    report.append(f"文件: {path}")
                    report.append(f"比特率: {bitrate}")
                    report.append("")
            
            report.append(f"\n有日期信息的文件 ({len(results['with_date'])}个):")
            for path, date, date_type, bitrate in results['with_date']:
                report.append(f"文件: {path}")
                report.append(f"日期类型: {date_type}")
                report.append(f"日期: {date}")
                if bitrate:
                    report.append(f"比特率: {bitrate} kbps")
                report.append("")
            
            report.append(f"\n没有日期信息的文件 ({len(results['without_date'])}个):")
            for path, reason, date_type, bitrate in results['without_date']:
                report.append(f"文件: {path}")
                report.append(f"日期类型: {date_type}")
                report.append(f"原因: {reason}")
                if bitrate:
                    report.append(f"比特率: {bitrate} kbps")
                report.append("")
            
            report.append("\n" + "="*50 + "\n")
            
            # 写入日志文件
            write_to_log(log_file, '\n'.join(report))
            
            return '\n'.join(report)
                
        except Exception as e:
            error_msg = f"生成报告时出错: {str(e)}"
            print(error_msg)
            write_to_log(log_file, error_msg)
            return error_msg

class MediaCheckerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.check_results = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('媒体文件日期检查工具')
        # 设置窗口大小
        self.resize(1000, 600)
        # 窗口居中显示
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 目录选择
        dir_group = QGroupBox("目录设置")
        dir_layout = QVBoxLayout()
        
        dir_input_layout = QHBoxLayout()
        self.dir_path = QLineEdit(DEFAULT_CHECK_DIR)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_directory)
        dir_input_layout.addWidget(QLabel("选择媒体文件目录:"))
        dir_input_layout.addWidget(self.dir_path)
        dir_input_layout.addWidget(browse_btn)
        
        dir_layout.addLayout(dir_input_layout)
        dir_layout.addWidget(QLabel(f"默认检查目录: {DEFAULT_CHECK_DIR}"))
        self.log_label = QLabel("检查记录将保存在AutoPhoto文件夹中")
        dir_layout.addWidget(self.log_label)
        
        if not check_ffmpeg():
            ffmpeg_label = QLabel("警告: 未检测到ffmpeg，无法处理视频文件")
            ffmpeg_label.setStyleSheet("color: red;")
            dir_layout.addWidget(ffmpeg_label)
        
        dir_group.setLayout(dir_layout)
        left_layout.addWidget(dir_group)

        # 选项设置
        options_group = QGroupBox("选项设置")
        options_layout = QVBoxLayout()
        
        self.move_checkbox = QCheckBox("自动移动无日期文件到对应文件夹")
        self.move_big_video_checkbox = QCheckBox("自动移动比特率大于20000kbps的视频到BigVideo文件夹")
        
        options_layout.addWidget(self.move_checkbox)
        options_layout.addWidget(self.move_big_video_checkbox)
        options_group.setLayout(options_layout)
        left_layout.addWidget(options_group)

        # 按钮
        buttons_layout = QHBoxLayout()
        self.check_btn = QPushButton("开始检查")
        self.check_btn.clicked.connect(self.start_check)
        self.update_dates_btn = QPushButton("修改文件创建日期")
        self.update_dates_btn.clicked.connect(self.update_file_dates)
        buttons_layout.addWidget(self.check_btn)
        buttons_layout.addWidget(self.update_dates_btn)
        left_layout.addLayout(buttons_layout)

        # 标签页
        self.tab_widget = QTabWidget()
        
        # 有日期信息标签页
        self.with_info_text = QTextEdit()
        self.with_info_text.setReadOnly(True)
        self.tab_widget.addTab(self.with_info_text, "有日期信息")
        
        # 无日期信息标签页
        self.without_info_text = QTextEdit()
        self.without_info_text.setReadOnly(True)
        self.tab_widget.addTab(self.without_info_text, "无日期信息")
        
        # 大视频文件标签页
        self.big_video_text = QTextEdit()
        self.big_video_text.setReadOnly(True)
        self.tab_widget.addTab(self.big_video_text, "大视频文件")
        
        # LIVP文件标签页
        self.livp_text = QTextEdit()
        self.livp_text.setReadOnly(True)
        self.tab_widget.addTab(self.livp_text, "LIVP文件")
        
        left_layout.addWidget(self.tab_widget)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        left_layout.addWidget(self.progress_bar)

        # 右侧统计面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        stats_group = QGroupBox("文件统计信息")
        stats_layout = QVBoxLayout()
        
        self.stats_labels = {}
        stats_items = [
            ("有日期信息", "0"),
            ("无日期信息", "0"),
            ("大视频文件", "0"),
            ("LIVP文件", "0"),
            ("文件总数", "0")
        ]
        
        for label, value in stats_items:
            layout = QHBoxLayout()
            layout.addWidget(QLabel(f"{label}:"))
            self.stats_labels[label] = QLabel(value)
            self.stats_labels[label].setStyleSheet("font-weight: bold;")
            layout.addWidget(self.stats_labels[label])
            stats_layout.addLayout(layout)
        
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        right_layout.addStretch()

        # 添加到主布局
        main_layout.addWidget(left_panel, stretch=3)
        main_layout.addWidget(right_panel, stretch=1)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择媒体文件目录", self.dir_path.text())
        if directory:
            self.dir_path.setText(directory)

    def start_check(self):
        if not self.dir_path.text():
            QMessageBox.warning(self, "警告", "请选择媒体文件目录")
            return

        if not check_ffmpeg():
            QMessageBox.critical(self, "错误", 
                "未检测到ffmpeg，无法处理视频文件。\n\n"
                "请确保ffmpeg文件夹位于AutoPhoto目录下，\n"
                "并且包含ffmpeg.exe和ffprobe.exe文件。\n\n"
                f"当前查找路径：{FFMPEG_DIR}")
            return

        self.progress_bar.setRange(0, 0)
        self.check_btn.setEnabled(False)
        self.update_dates_btn.setEnabled(False)

        # 清空所有文本框
        self.with_info_text.clear()
        self.without_info_text.clear()
        self.big_video_text.clear()
        self.livp_text.clear()

        # 创建新的日志文件
        current_log_file = get_log_file()
        self.log_label.setText(f"当前检查记录保存在: {current_log_file}")

        # 创建并启动检查线程
        self.check_thread = CheckThread(
            self.dir_path.text(),
            self.move_checkbox.isChecked(),
            self.move_big_video_checkbox.isChecked()
        )
        self.check_thread.finished.connect(self.update_results)
        self.check_thread.error.connect(self.show_error)
        self.check_thread.start()

    def update_results(self, results):
        print("更新结果...")
        self.check_results = results
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.check_btn.setEnabled(True)
        self.update_dates_btn.setEnabled(True)

        # 更新统计信息
        self.stats_labels["有日期信息"].setText(str(len(results['with_date'])))
        self.stats_labels["无日期信息"].setText(str(len(results['without_date'])))
        self.stats_labels["大视频文件"].setText(str(len(results['big_videos'])))
        self.stats_labels["LIVP文件"].setText(str(len(results['livp_files'])))
        total_files = len(results['with_date']) + len(results['without_date']) + len(results['livp_files'])
        self.stats_labels["文件总数"].setText(str(total_files))

        # 更新各个标签页的内容
        self.update_tab_content(self.with_info_text, results['with_date'], "有日期信息的文件")
        self.update_tab_content(self.without_info_text, results['without_date'], "没有日期信息的文件")
        self.update_tab_content(self.big_video_text, results['big_videos'], "大视频文件")
        self.update_tab_content(self.livp_text, results['livp_files'], "LIVP文件")

        # 生成并写入报告
        checker = MediaDateChecker(self.dir_path.text())
        current_log_file = self.log_label.text().replace("当前检查记录保存在: ", "") # 获取当前的log文件路径
        checker.print_report(results, current_log_file)
        print("结果更新完成.")

    def update_tab_content(self, text_widget, items, title):
        if items:
            text_widget.append(f"{title} ({len(items)}个):\n")
            for item in items:
                if isinstance(item, tuple):
                    if len(item) == 2:  # 大视频文件
                        path, bitrate = item
                        text_widget.append(f"文件: {path}\n")
                        text_widget.append(f"比特率: {bitrate}\n")
                    else:  # 有日期或无日期文件
                        path, info, date_type, bitrate = item
                        text_widget.append(f"文件: {path}\n")
                        text_widget.append(f"日期类型: {date_type}\n")
                        if isinstance(info, str):
                            text_widget.append(f"日期: {info}\n")
                        else:
                            text_widget.append(f"原因: {info}\n")
                        if bitrate:
                            text_widget.append(f"比特率: {bitrate} kbps\n")
                else:  # LIVP文件
                    text_widget.append(f"文件: {item}\n")
                text_widget.append("")
        else:
            text_widget.append(f"没有找到{title}\n")

    def update_file_dates(self):
        if not self.check_results:
            QMessageBox.warning(self, "警告", "请先运行检查")
            return

        files_to_update = []
        
        # 处理有日期信息的文件
        for path, date, date_type, _ in self.check_results['with_date']:
            try:
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y:%m:%d %H:%M:%S',
                    '%Y/%m/%d %H:%M:%S',
                    '%Y-%m-%d %H%M%S',
                    '%Y:%m:%d %H%M%S',
                    '%Y/%m/%d %H%M%S'
                ]
                
                date_obj = None
                for fmt in date_formats:
                    try:
                        date_obj = datetime.strptime(date, fmt)
                        break
                    except ValueError:
                        continue
                
                if date_obj:
                    files_to_update.append((path, date_obj, date_type))
            except Exception as e:
                print(f"处理日期时出错: {date} for {path} - {str(e)}")
                continue

        # 处理无日期信息的文件
        for path, reason, date_type, _ in self.check_results['without_date']:
            try:
                filename = os.path.basename(path)
                date_str = filename.split('.')[0]
                
                date_formats = [
                    '%Y-%m-%d %H%M%S',
                    '%Y:%m:%d %H%M%S',
                    '%Y/%m/%d %H%M%S'
                ]
                
                date_obj = None
                for fmt in date_formats:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if date_obj:
                    files_to_update.append((path, date_obj, "文件名日期"))
            except Exception as e:
                print(f"处理文件名日期时出错: {path} - {str(e)}")
                continue

        if not files_to_update:
            QMessageBox.information(self, "提示", "没有找到可以修改日期的文件")
            return

        reply = QMessageBox.question(self, "确认", 
            f"将修改 {len(files_to_update)} 个文件的创建日期，是否继续？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            self.check_btn.setEnabled(False)
            self.update_dates_btn.setEnabled(False)
            self.progress_bar.setRange(0, 0)
            
            self.update_thread = UpdateDatesThread(files_to_update)
            self.update_thread.progress.connect(lambda msg: print(msg))
            self.update_thread.finished.connect(self.show_update_result)
            self.update_thread.error.connect(self.show_error)
            self.update_thread.start()

    def show_update_result(self, success_count, fail_count, skipped_count):
        print("显示更新结果...")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.check_btn.setEnabled(True)
        self.update_dates_btn.setEnabled(True)
        
        message = f"文件日期修改完成\n成功: {success_count} 个文件\n失败: {fail_count} 个文件"
        if skipped_count > 0:
            message += f"\n跳过: {skipped_count} 个文件"
        QMessageBox.information(self, "完成", message)
        print("更新结果显示完成.")

    def show_error(self, error_msg):
        print(f"显示错误: {error_msg}")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.check_btn.setEnabled(True)
        self.update_dates_btn.setEnabled(True)
        QMessageBox.critical(self, "错误", error_msg)

def main():
    print("应用启动...")
    app = QApplication(sys.argv)
    window = MediaCheckerGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 