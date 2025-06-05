import os
import shutil
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import glob
import ffmpeg
import subprocess
import sys
import json

# 设置默认检查目录
DEFAULT_CHECK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Check')
NO_INFO_DIR = os.path.join(DEFAULT_CHECK_DIR, 'NoInformation')
NO_VIDEO_INFO_DIR = os.path.join(DEFAULT_CHECK_DIR, 'NoVideoInformation')
BIG_VIDEO_DIR = os.path.join(DEFAULT_CHECK_DIR, 'BigVideo')  # 大视频文件夹
LOG_DIR = os.path.dirname(os.path.abspath(__file__))  # AutoPhoto文件夹
FFMPEG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg-7.1.1', 'bin')  # ffmpeg目录

# 确保Check文件夹存在
if not os.path.exists(DEFAULT_CHECK_DIR):
    os.makedirs(DEFAULT_CHECK_DIR)
    print(f"创建检查目录: {DEFAULT_CHECK_DIR}")

# 确保NoInformation文件夹存在
if not os.path.exists(NO_INFO_DIR):
    os.makedirs(NO_INFO_DIR)
    print(f"创建无信息图片目录: {NO_INFO_DIR}")

# 确保NoVideoInformation文件夹存在
if not os.path.exists(NO_VIDEO_INFO_DIR):
    os.makedirs(NO_VIDEO_INFO_DIR)
    print(f"创建无信息视频目录: {NO_VIDEO_INFO_DIR}")

# 确保BigVideo文件夹存在
if not os.path.exists(BIG_VIDEO_DIR):
    os.makedirs(BIG_VIDEO_DIR)
    print(f"创建大视频目录: {BIG_VIDEO_DIR}")

def get_log_file():
    """获取新的日志文件路径"""
    try:
        # 确保日志目录存在
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
            print(f"创建日志目录: {LOG_DIR}")

        # 获取当前时间作为日志文件名的一部分
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(LOG_DIR, f'photo_check_{current_time}.txt')
        
        # 创建文件并写入初始内容
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== 检查记录文件创建时间: {current_time} ===\n")
        
        # 清理旧的日志文件，只保留最近的三次
        log_files = glob.glob(os.path.join(LOG_DIR, 'photo_check_*.txt'))
        log_files.sort(reverse=True)  # 按时间倒序排序
        
        # 删除旧的日志文件
        for old_file in log_files[3:]:  # 保留最新的3个文件
            try:
                os.remove(old_file)
            except Exception as e:
                print(f"删除旧文件失败: {str(e)}")
        
        return log_file
    except Exception as e:
        print(f"创建日志文件时出错: {str(e)}")
        # 如果出错，使用备用方案：保存到Check文件夹
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
        # 首先尝试使用环境变量中的ffmpeg
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
            
        # 如果环境变量中的ffmpeg不可用，尝试使用本地ffmpeg
        ffprobe_path = os.path.join(FFMPEG_DIR, 'ffprobe.exe')
        if os.path.exists(ffprobe_path):
            result = subprocess.run([ffprobe_path, '-version'], capture_output=True, text=True)
            return result.returncode == 0
            
        return False
    except FileNotFoundError:
        # 如果环境变量中的ffmpeg不可用，尝试使用本地ffmpeg
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
        # 首先尝试使用环境变量中的ffprobe
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'ffprobe'
    except FileNotFoundError:
        pass
        
    # 如果环境变量中的ffprobe不可用，使用本地ffprobe
    ffprobe_path = os.path.join(FFMPEG_DIR, 'ffprobe.exe')
    if os.path.exists(ffprobe_path):
        return ffprobe_path
        
    return None

def show_ffmpeg_error():
    """显示ffmpeg安装提示"""
    messagebox.showerror(
        "错误",
        "未检测到ffmpeg，无法处理视频文件。\n\n"
        "请确保ffmpeg文件夹位于AutoPhoto目录下，\n"
        "并且包含ffmpeg.exe和ffprobe.exe文件。\n\n"
        "当前查找路径：" + FFMPEG_DIR
    )

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
            image = Image.open(image_path)
            if not hasattr(image, '_getexif') or image._getexif() is None:
                return None
                
            exif = image._getexif()
            date_info = None
            
            for tag_id in exif:
                tag = TAGS.get(tag_id, tag_id)
                if tag in self.date_tags:
                    date_info = exif[tag_id]
                    break
                    
            return date_info
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
                    date_obj = datetime.strptime(date, '%Y:%m:%d %H:%M:%S')
                    return True, date_obj.strftime('%Y-%m-%d %H:%M:%S'), "拍摄日期", None
                except ValueError:
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
            'big_videos': []  # 新增：大视频列表
        }
        
        for root, _, files in os.walk(self.directory):
            # 跳过NoInformation、NoVideoInformation和BigVideo文件夹
            if NO_INFO_DIR in root or NO_VIDEO_INFO_DIR in root or BIG_VIDEO_DIR in root:
                continue
                
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.supported_image_formats or ext in self.supported_video_formats:
                    file_path = os.path.join(root, file)
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

class MediaCheckerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("媒体文件日期检查工具")
        self.root.geometry("800x600")
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 目录选择
        ttk.Label(main_frame, text="选择媒体文件目录:").grid(row=0, column=0, sticky=tk.W)
        self.dir_path = tk.StringVar(value=DEFAULT_CHECK_DIR)
        ttk.Entry(main_frame, textvariable=self.dir_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="浏览", command=self.browse_directory).grid(row=0, column=2)
        
        # 添加说明标签
        ttk.Label(main_frame, text=f"默认检查目录: {DEFAULT_CHECK_DIR}", wraplength=600).grid(row=1, column=0, columnspan=3, pady=5)
        self.log_label = ttk.Label(main_frame, text="检查记录将保存在AutoPhoto文件夹中", wraplength=600)
        self.log_label.grid(row=2, column=0, columnspan=3, pady=5)
        
        # 检查ffmpeg状态
        if not check_ffmpeg():
            self.ffmpeg_label = ttk.Label(main_frame, text="警告: 未检测到ffmpeg，无法处理视频文件", foreground="red", wraplength=600)
            self.ffmpeg_label.grid(row=3, column=0, columnspan=3, pady=5)
        
        # 选项
        self.move_var = tk.BooleanVar()
        ttk.Checkbutton(main_frame, text="自动移动无日期文件到对应文件夹", variable=self.move_var).grid(row=4, column=0, columnspan=3, pady=10)
        
        # 大视频选项
        self.move_big_video_var = tk.BooleanVar()
        ttk.Checkbutton(main_frame, text="自动移动比特率大于20000kbps的视频到BigVideo文件夹", variable=self.move_big_video_var).grid(row=5, column=0, columnspan=3, pady=10)
        
        # 开始按钮
        ttk.Button(main_frame, text="开始检查", command=self.start_check).grid(row=6, column=0, columnspan=3, pady=10)
        
        # 结果显示
        self.result_text = tk.Text(main_frame, height=20, width=80)
        self.result_text.grid(row=7, column=0, columnspan=3, pady=10)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, length=300, mode='indeterminate')
        self.progress.grid(row=8, column=0, columnspan=3, pady=10)
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_path.set(directory)
            
    def start_check(self):
        if not self.dir_path.get():
            messagebox.showerror("错误", "请选择媒体文件目录")
            return
            
        if not check_ffmpeg():
            show_ffmpeg_error()
            return
            
        self.progress.start()
        self.result_text.delete(1.0, tk.END)
        
        # 创建新的日志文件
        current_log_file = get_log_file()
        self.log_label.config(text=f"当前检查记录保存在: {current_log_file}")
        
        # 在新线程中运行检查
        thread = threading.Thread(target=self.run_check, args=(current_log_file,))
        thread.daemon = True
        thread.start()
        
    def run_check(self, log_file):
        try:
            checker = MediaDateChecker(self.dir_path.get())
            results = checker.scan_directory(
                move_no_info=self.move_var.get(),
                move_big_video=self.move_big_video_var.get()
            )
            
            # 更新UI
            self.root.after(0, self.update_results, results, log_file)
        except Exception as e:
            self.root.after(0, self.show_error, str(e))
        finally:
            self.root.after(0, self.progress.stop)
            
    def update_results(self, results, log_file):
        self.result_text.delete(1.0, tk.END)
        
        # 显示大视频信息
        if results['big_videos']:
            self.result_text.insert(tk.END, f"\n大视频文件 ({len(results['big_videos'])}个):\n")
            for path, bitrate in results['big_videos']:
                self.result_text.insert(tk.END, f"文件: {path}\n")
                self.result_text.insert(tk.END, f"比特率: {bitrate}\n\n")
        
        # 显示有日期的文件
        self.result_text.insert(tk.END, f"\n有日期信息的文件 ({len(results['with_date'])}个):\n")
        for path, date, date_type, bitrate in results['with_date']:
            self.result_text.insert(tk.END, f"文件: {path}\n")
            self.result_text.insert(tk.END, f"日期类型: {date_type}\n")
            self.result_text.insert(tk.END, f"日期: {date}\n")
            if bitrate:
                self.result_text.insert(tk.END, f"比特率: {bitrate} kbps\n")
            self.result_text.insert(tk.END, "\n")
            
        # 显示没有日期的文件
        self.result_text.insert(tk.END, f"\n没有日期信息的文件 ({len(results['without_date'])}个):\n")
        for path, reason, date_type, bitrate in results['without_date']:
            self.result_text.insert(tk.END, f"文件: {path}\n")
            self.result_text.insert(tk.END, f"日期类型: {date_type}\n")
            self.result_text.insert(tk.END, f"原因: {reason}\n")
            if bitrate:
                self.result_text.insert(tk.END, f"比特率: {bitrate} kbps\n")
            self.result_text.insert(tk.END, "\n")
            
        # 添加分隔线
        self.result_text.insert(tk.END, "\n" + "="*50 + "\n")
        
        # 自动滚动到顶部
        self.result_text.see("1.0")
        
        # 生成并写入报告
        checker = MediaDateChecker(self.dir_path.get())
        checker.print_report(results, log_file)
            
    def show_error(self, error_msg):
        messagebox.showerror("错误", error_msg)
        
    def run(self):
        self.root.mainloop()

def main():
    # 创建GUI应用
    app = MediaCheckerGUI()
    app.run()

if __name__ == "__main__":
    main() 