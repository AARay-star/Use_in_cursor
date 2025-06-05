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

# 设置默认检查目录
DEFAULT_CHECK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Check')
NO_INFO_DIR = os.path.join(DEFAULT_CHECK_DIR, 'NoInformation')
LOG_DIR = os.path.dirname(os.path.abspath(__file__))  # AutoPhoto文件夹

# 确保Check文件夹存在
if not os.path.exists(DEFAULT_CHECK_DIR):
    os.makedirs(DEFAULT_CHECK_DIR)
    print(f"创建检查目录: {DEFAULT_CHECK_DIR}")

# 确保NoInformation文件夹存在
if not os.path.exists(NO_INFO_DIR):
    os.makedirs(NO_INFO_DIR)
    print(f"创建无信息图片目录: {NO_INFO_DIR}")

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

class PhotoDateChecker:
    def __init__(self, directory):
        self.directory = directory
        self.supported_formats = ['.jpg', '.jpeg', '.tiff', '.tif', '.png', '.heic', '.heif']
        self.date_tags = [
            'DateTimeOriginal',  # 原始拍摄时间
            'DateTimeDigitized', # 数字化时间
            'DateTime',          # 修改时间
        ]
        
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
            logging.error(f"处理图片 {image_path} 时出错: {str(e)}")
            return None

    def check_photo(self, image_path):
        """检查单张图片的日期信息"""
        date = self.get_exif_date(image_path)
        if date:
            try:
                # 尝试解析日期字符串
                date_obj = datetime.strptime(date, '%Y:%m:%d %H:%M:%S')
                return True, date_obj.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                return False, "日期格式无效"
        return False, "未找到日期信息"

    def move_to_no_info(self, image_path):
        """移动图片到NoInformation文件夹"""
        try:
            file_name = os.path.basename(image_path)
            new_path = os.path.join(NO_INFO_DIR, file_name)
            
            # 如果文件已存在，添加序号
            counter = 1
            name, ext = os.path.splitext(file_name)
            while os.path.exists(new_path):
                new_path = os.path.join(NO_INFO_DIR, f"{name}_{counter}{ext}")
                counter += 1
                
            shutil.move(image_path, new_path)
            return new_path
        except Exception as e:
            logging.error(f"移动图片 {image_path} 时出错: {str(e)}")
            return None

    def scan_directory(self, move_no_info=False):
        """扫描目录中的所有图片"""
        results = {
            'with_date': [],
            'without_date': []
        }
        
        for root, _, files in os.walk(self.directory):
            # 跳过NoInformation文件夹
            if NO_INFO_DIR in root:
                continue
                
            for file in files:
                if any(file.lower().endswith(fmt) for fmt in self.supported_formats):
                    image_path = os.path.join(root, file)
                    has_date, date_info = self.check_photo(image_path)
                    
                    if has_date:
                        results['with_date'].append((image_path, date_info))
                    else:
                        if move_no_info:
                            new_path = self.move_to_no_info(image_path)
                            if new_path:
                                results['without_date'].append((new_path, date_info))
                        else:
                            results['without_date'].append((image_path, date_info))
        
        return results

    def print_report(self, results, log_file):
        """打印检查报告"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 准备报告内容
            report = []
            report.append(f"\n=== 图片日期检查报告 ({current_time}) ===")
            report.append(f"检查目录: {self.directory}")
            
            report.append(f"\n有拍摄日期的图片 ({len(results['with_date'])}张):")
            for path, date in results['with_date']:
                report.append(f"文件: {path}")
                report.append(f"日期: {date}")
                report.append("")
            
            report.append(f"\n没有拍摄日期的图片 ({len(results['without_date'])}张):")
            for path, reason in results['without_date']:
                report.append(f"文件: {path}")
                report.append(f"原因: {reason}")
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

class PhotoCheckerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("图片日期检查工具")
        self.root.geometry("800x600")
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 目录选择
        ttk.Label(main_frame, text="选择图片目录:").grid(row=0, column=0, sticky=tk.W)
        self.dir_path = tk.StringVar(value=DEFAULT_CHECK_DIR)
        ttk.Entry(main_frame, textvariable=self.dir_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="浏览", command=self.browse_directory).grid(row=0, column=2)
        
        # 添加说明标签
        ttk.Label(main_frame, text=f"默认检查目录: {DEFAULT_CHECK_DIR}", wraplength=600).grid(row=1, column=0, columnspan=3, pady=5)
        self.log_label = ttk.Label(main_frame, text="检查记录将保存在AutoPhoto文件夹中", wraplength=600)
        self.log_label.grid(row=2, column=0, columnspan=3, pady=5)
        
        # 选项
        self.move_var = tk.BooleanVar()
        ttk.Checkbutton(main_frame, text="自动移动无日期图片到NoInformation文件夹", variable=self.move_var).grid(row=3, column=0, columnspan=3, pady=10)
        
        # 开始按钮
        ttk.Button(main_frame, text="开始检查", command=self.start_check).grid(row=4, column=0, columnspan=3, pady=10)
        
        # 结果显示
        self.result_text = tk.Text(main_frame, height=20, width=80)
        self.result_text.grid(row=5, column=0, columnspan=3, pady=10)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, length=300, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, pady=10)
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_path.set(directory)
            
    def start_check(self):
        if not self.dir_path.get():
            messagebox.showerror("错误", "请选择图片目录")
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
            checker = PhotoDateChecker(self.dir_path.get())
            results = checker.scan_directory(move_no_info=self.move_var.get())
            
            # 更新UI
            self.root.after(0, self.update_results, results, log_file)
        except Exception as e:
            self.root.after(0, self.show_error, str(e))
        finally:
            self.root.after(0, self.progress.stop)
            
    def update_results(self, results, log_file):
        self.result_text.delete(1.0, tk.END)
        
        # 显示有日期的图片
        self.result_text.insert(tk.END, f"\n有拍摄日期的图片 ({len(results['with_date'])}张):\n")
        for path, date in results['with_date']:
            self.result_text.insert(tk.END, f"文件: {path}\n")
            self.result_text.insert(tk.END, f"日期: {date}\n\n")
            
        # 显示没有日期的图片
        self.result_text.insert(tk.END, f"\n没有拍摄日期的图片 ({len(results['without_date'])}张):\n")
        for path, reason in results['without_date']:
            self.result_text.insert(tk.END, f"文件: {path}\n")
            self.result_text.insert(tk.END, f"原因: {reason}\n\n")
            
        # 添加分隔线
        self.result_text.insert(tk.END, "\n" + "="*50 + "\n")
        
        # 自动滚动到顶部
        self.result_text.see("1.0")
        
        # 生成并写入报告
        checker = PhotoDateChecker(self.dir_path.get())
        checker.print_report(results, log_file)
            
    def show_error(self, error_msg):
        messagebox.showerror("错误", error_msg)
        
    def run(self):
        self.root.mainloop()

def main():
    # 创建GUI应用
    app = PhotoCheckerGUI()
    app.run()

if __name__ == "__main__":
    main() 