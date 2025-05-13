import win32gui
import win32con
import os
import time
import re
import winreg
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
import threading
from PIL import Image, ImageTk
import mimetypes
import math
import sys

TARGET_WINDOW_TITLE = ["메시지 관리함", "개의 안읽은 메시지"]
SAVE_BUTTON_TEXT = "모든파일 저장 (Ctrl+S)"
SIZE_PATTERN = re.compile(r"\(\d+(?:\.\d+)?\s?(KB|MB|GB)\)$", re.IGNORECASE)

icon_cache = {}

class Theme:
    def __init__(self):
        self.dark = {
            'bg': '#2D2D2D',
            'fg': '#E0E0E0',
            'select_bg': '#404040',
            'button_bg': '#3D3D3D',
            'button_fg': '#E0E0E0',
            'border': '#555555',
            'highlight': '#4D7CAE'
        }
        self.light = {
            'bg': '#F5F5F5',
            'fg': '#333333',
            'select_bg': '#E0E0E0',
            'button_bg': '#EFEFEF',
            'button_fg': '#333333',
            'border': '#CCCCCC',
            'highlight': '#4A90E2'
        }
        self.current = self.light

def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_down_path():
    try:
        key_path = r'Software\\Jiransoft\\CoolMsg50\\Option\\GetFile'
        value_name = 'DownPath'
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(registry_key, value_name)
        winreg.CloseKey(registry_key)
        return value
    except FileNotFoundError:
        return os.path.join(os.path.expanduser("~"), "Downloads")
    except Exception as e:
        print(f"Error: {e}")
        return os.path.join(os.path.expanduser("~"), "Downloads")

DOWNLOAD_PATH = get_down_path()

def load_default_icons():
    file_types = {
        'image': '🖼️',
        'audio': '🎵',
        'video': '🎬',
        'text': '📄',
        'application': '📦',
        'pdf': '📑',
        'archive': '🗜️',
        'unknown': '📎'
    }
    return file_types

def get_file_icon(filename):
    if filename in icon_cache:
        return icon_cache[filename]
    
    file_types = load_default_icons()
    mimetype, _ = mimetypes.guess_type(filename)
    
    if not mimetype:
        icon = file_types['unknown']
    elif mimetype.startswith('image/'):
        icon = file_types['image']
    elif mimetype.startswith('audio/'):
        icon = file_types['audio']
    elif mimetype.startswith('video/'):
        icon = file_types['video']
    elif mimetype.startswith('text/'):
        icon = file_types['text']
    elif mimetype == 'application/pdf':
        icon = file_types['pdf']
    elif mimetype in ['application/zip', 'application/x-rar-compressed']:
        icon = file_types['archive']
    elif mimetype.startswith('application/'):
        icon = file_types['application']
    else:
        icon = file_types['unknown']
    
    icon_cache[filename] = icon
    return icon

def extract_filename(text):
    match = SIZE_PATTERN.search(text)
    if match:
        return text[:match.start()].strip()
    return text.strip()

def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    print(f"{timestamp} {msg}")

def find_window_by_title_keyword(keywords):
    result = []
    for keyword in keywords:
        def callback(hwnd, _):
            if keyword in win32gui.GetWindowText(hwnd):
                result.append(hwnd)
        win32gui.EnumWindows(callback, None)

    return result

def find_controls_by_size_pattern(hwnd):
    matched = []
    def recurse(h):
        text = try_get_text(h)
        if SIZE_PATTERN.search(text):
            matched.append((h, text.strip()))
        children = []
        win32gui.EnumChildWindows(h, lambda ch, param: param.append(ch), children)
        for ch in children:
            recurse(ch)
    recurse(hwnd)
    return matched

def try_get_text(hwnd):
    try:
        length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH)
        if length == 0:
            return ""
        buffer = win32gui.PyMakeBuffer((length + 1) * 2)
        win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length + 1, buffer)
        return buffer[:].tobytes().decode("utf-16", errors="ignore").rstrip("\x00")
    except Exception as e:
        return f"[ERROR: {e}]"

def click_button_by_text(parent_hwnd, button_text):
    found = []
    def recurse(hwnd):
        if try_get_text(hwnd).strip() == button_text:
            found.append(hwnd)
            return
        children = []
        win32gui.EnumChildWindows(hwnd, lambda ch, param: param.append(ch), children)
        for ch in children:
            recurse(ch)
    recurse(parent_hwnd)
    if found:
        log(f"'저장' 버튼 클릭 (HWND: {hex(found[0])})")
        win32gui.SendMessage(found[0], win32con.BM_CLICK, 0, 0)
        return True
    return False

class RoundedFrame(tk.Canvas):
    def __init__(self, parent, bg='#FFFFFF', width=200, height=100, corner_radius=10, **kwargs):
        super().__init__(parent, bg=bg, highlightthickness=0, **kwargs)
        self.corner_radius = corner_radius
        self.width = width
        self.height = height
        self.configure(width=width, height=height)
        self.bind("<Configure>", self._on_resize)
        self._draw_rounded_rect()
        
    def _on_resize(self, event):
        self.width = event.width
        self.height = event.height
        self._draw_rounded_rect()
        
    def _draw_rounded_rect(self):
        self.delete("all")
        x1, y1 = 0, 0
        x2, y2 = self.width, self.height
        radius = self.corner_radius
        
        self.create_polygon(
            x1+radius, y1,
            x2-radius, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2-radius,
            x1, y1+radius,
            smooth=True, fill=self['bg'], outline=self['bg']
        )

class HoverButton(tk.Canvas):
    def __init__(self, parent, command=None, text="", width=100, height=30, 
                 bg="#EFEFEF", fg="#333333", hover_bg="#E0E0E0", hover_fg="#000000", 
                 corner_radius=5, **kwargs):
        super().__init__(parent, width=width, height=height, 
                         highlightthickness=0, bg=parent["bg"], **kwargs)
        self.command = command
        self.text = text
        self.corner_radius = corner_radius
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover_bg
        self.hover_fg = hover_fg
        self.width = width
        self.height = height
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        
        self._draw_button(bg, fg)
        
    def _draw_button(self, bg, fg):
        self.delete("all")
        
        self.create_rectangle(
            0, 0, self.width, self.height,
            fill=bg, outline=bg, width=0,
            radius=self.corner_radius
        )
        
        self.create_text(
            self.width // 2, self.height // 2,
            text=self.text, fill=fg, font=("Malgun Gothic", 9)
        )
        
    def _on_enter(self, event):
        self._draw_button(self.hover_bg, self.hover_fg)
        
    def _on_leave(self, event):
        self._draw_button(self.bg, self.fg)
        
    def _on_press(self, event):
        self._draw_button(self.hover_fg, self.hover_bg)
        
    def _on_release(self, event):
        self._draw_button(self.hover_bg, self.hover_fg)
        if self.command:
            self.command()

class FileItem(tk.Frame):
    def __init__(self, parent, filename, filepath, theme, **kwargs):
        super().__init__(parent, bg=theme.current['bg'], **kwargs)
        
        self.filename = filename
        self.filepath = filepath
        self.theme = theme
        
        self.configure(
            padx=5, 
            pady=5, 
            bd=1, 
            relief="flat",
            highlightthickness=1,
            highlightbackground=theme.current['border'],
            highlightcolor=theme.current['highlight']
        )
        
        icon_text = get_file_icon(filename)
        self.icon_label = tk.Label(self, text=icon_text, font=("Segoe UI", 16), bg=theme.current['bg'], fg=theme.current['fg'])
        self.icon_label.pack(side=tk.LEFT, padx=(5, 10))
        self.icon_label.bind("<Enter>", self._on_enter)
        self.icon_label.bind("<Leave>", self._on_leave)
        self.icon_label.bind("<Double-1>", self._on_double_click)
        
        info_frame = tk.Frame(self, bg=theme.current['bg'])
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_frame.bind("<Enter>", self._on_enter)
        info_frame.bind("<Leave>", self._on_leave)
        info_frame.bind("<Double-1>", self._on_double_click)

        self.name_label = tk.Label(info_frame, text=filename, font=("Malgun Gothic", 10), 
                                  anchor="w", bg=theme.current['bg'], fg=theme.current['fg'])
        self.name_label.pack(side=tk.TOP, fill=tk.X)
        self.name_label.bind("<Enter>", self._on_enter)
        self.name_label.bind("<Leave>", self._on_leave)
        self.name_label.bind("<Double-1>", self._on_double_click)
        
        meta_frame = tk.Frame(info_frame, bg=theme.current['bg'])
        meta_frame.pack(side=tk.TOP, fill=tk.X)
        meta_frame.bind("<Enter>", self._on_enter)
        meta_frame.bind("<Leave>", self._on_leave)
        meta_frame.bind("<Double-1>", self._on_double_click)
        
        self.size_label = tk.Label(meta_frame, text="", font=("Malgun Gothic", 8), 
                                  fg="#888888", bg=theme.current['bg'], anchor="w")
        self.size_label.pack(side=tk.LEFT, padx=(0, 10))
        self.size_label.bind("<Enter>", self._on_enter)
        self.size_label.bind("<Leave>", self._on_leave)
        self.size_label.bind("<Double-1>", self._on_double_click)
        
        self.time_label = tk.Label(meta_frame, text="", font=("Malgun Gothic", 8), 
                                   fg="#888888", bg=theme.current['bg'], anchor="w")
        self.time_label.pack(side=tk.LEFT)
        self.time_label.bind("<Enter>", self._on_enter)
        self.time_label.bind("<Leave>", self._on_leave)
        self.time_label.bind("<Double-1>", self._on_double_click)
        
        self.update_file_info()
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Double-1>", self._on_double_click)
        
    def update_file_info(self):
        try:
            if os.path.exists(self.filepath):
                file_size = os.path.getsize(self.filepath)
                mod_time = os.path.getmtime(self.filepath)
                
                size_str = format_size(file_size)
                self.size_label.config(text=size_str)
                
                time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
                self.time_label.config(text=time_str)
            else:
                self.size_label.config(text="다운로드 필요")
                self.time_label.config(text="")
        except Exception as e:
            self.size_label.config(text="정보 없음")
            self.time_label.config(text="")
    
    def _on_enter(self, event):
        self.config(bg=self.theme.current['select_bg'])
        self.icon_label.config(bg=self.theme.current['select_bg'])
        self.name_label.config(bg=self.theme.current['select_bg'])
        self.size_label.config(bg=self.theme.current['select_bg'])
        self.time_label.config(bg=self.theme.current['select_bg'])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                child.config(bg=self.theme.current['select_bg'])
                for subchild in child.winfo_children():
                    subchild.config(bg=self.theme.current['select_bg'])
    
    def _on_leave(self, event):
        self.config(bg=self.theme.current['bg'])
        self.icon_label.config(bg=self.theme.current['bg'])
        self.name_label.config(bg=self.theme.current['bg'])
        self.size_label.config(bg=self.theme.current['bg'])
        self.time_label.config(bg=self.theme.current['bg'])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                child.config(bg=self.theme.current['bg'])
                for subchild in child.winfo_children():
                    subchild.config(bg=self.theme.current['bg'])
    
    def _on_double_click(self, event):
        if os.path.exists(self.filepath):
            os.startfile(self.filepath)
        else:
            messagebox.showerror("오류", "파일이 존재하지 않습니다.")

class FileManagerGUI:
    def __init__(self):
        self.theme = Theme()
        
        self.window = tk.Tk()
        self.window.title("파일 관리")
        self.window.geometry("380x500")
        self.window.configure(bg=self.theme.current['bg'])
        self.window.overrideredirect(True)
        self.window.attributes('-alpha', 0.95)
        self.window.withdraw()
        self.last_window_pos = (0, 0)
        self.target_window_pos = (0, 0)
        self.animation_id = None
        self.position_update_time = 0
        self.throttle_delay = 100
        
        self.smooth_animation = True        
        if os.name == 'nt':
            try:
                from ctypes import windll
                hwnd = windll.user32.GetParent(self.window.winfo_id())
                style = windll.user32.GetWindowLongW(hwnd, -20)
                style = style | 0x00080000
                windll.user32.SetWindowLongW(hwnd, -20, style)
            except Exception as e:
                print(f"윈도우 효과 설정 실패: {e}")
        
        self.title_frame = tk.Frame(self.window, bg=self.theme.current['bg'], height=30)
        self.title_frame.pack(fill=tk.X, pady=(0, 5))
        self.title_frame.bind("<ButtonPress-1>", self.start_move)
        self.title_frame.bind("<ButtonRelease-1>", self.stop_move)
        self.title_frame.bind("<B1-Motion>", self.do_move)
        
        self.title_label = tk.Label(self.title_frame, text="쿨메신저 파일 관리", 
                                    font=("Malgun Gothic", 10, "bold"),
                                    bg=self.theme.current['bg'], 
                                    fg=self.theme.current['fg'])
        self.title_label.pack(side=tk.LEFT, padx=10)

        self.button_frame = tk.Frame(self.title_frame, bg=self.theme.current['bg'])
        self.button_frame.pack(side=tk.RIGHT, padx=5)

        self.separator = ttk.Separator(self.window, orient='horizontal')
        self.separator.pack(fill=tk.X, padx=10)

        self.container_frame = tk.Frame(self.window, bg=self.theme.current['bg'])
        self.container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.scrollbar = tk.Scrollbar(self.container_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(self.container_frame, bg=self.theme.current['bg'],
                               yscrollcommand=self.scrollbar.set,
                               highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar.config(command=self.canvas.yview)

        self.files_frame = tk.Frame(self.canvas, bg=self.theme.current['bg'])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.files_frame, anchor="nw")

        self.files_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.status_frame = tk.Frame(self.window, bg=self.theme.current['bg'], height=25)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(self.status_frame, text="준비됨", 
                                    font=("Malgun Gothic", 8),
                                    bg=self.theme.current['bg'], 
                                    fg="#888888", anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.file_items = []
        
        self.x = 0
        self.y = 0
    
    def update_theme(self):
        self.window.configure(bg=self.theme.current['bg'])

        self.title_frame.configure(bg=self.theme.current['bg'])
        self.title_label.configure(bg=self.theme.current['bg'], fg=self.theme.current['fg'])
        self.button_frame.configure(bg=self.theme.current['bg'])

        self.theme_button.configure(bg=self.theme.current['button_bg'], fg=self.theme.current['button_fg'])
        self.min_button.configure(bg=self.theme.current['button_bg'], fg=self.theme.current['button_fg'])
        self.close_button.configure(bg=self.theme.current['button_bg'])

        self.container_frame.configure(bg=self.theme.current['bg'])
        self.canvas.configure(bg=self.theme.current['bg'])
        self.files_frame.configure(bg=self.theme.current['bg'])

        self.status_frame.configure(bg=self.theme.current['bg'])
        self.status_label.configure(bg=self.theme.current['bg'])

        for item in self.file_items:
            item.theme = self.theme
            item._on_leave(None)
    
    
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
    
    def stop_move(self, event):
        self.x = None
        self.y = None
    
    def do_move(self, event):
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.window.winfo_x() + deltax
            y = self.window.winfo_y() + deltay
            self.window.geometry(f"+{x}+{y}")
    
    def on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def update_status(self, message):
        self.status_label.config(text=message)
    
    def clear_files(self):
        for item in self.file_items:
            item.destroy()
        self.file_items = []
    
    def add_file(self, filename):
        filepath = os.path.join(DOWNLOAD_PATH, filename)
        file_item = FileItem(self.files_frame, filename, filepath, self.theme)
        file_item.pack(fill=tk.X, pady=2)
        self.file_items.append(file_item)
        
        self.files_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def attach_to_window(self, hwnd):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            target_right = rect[2]
            target_top = rect[1]
            monitors = self.get_monitor_info()
            target_monitor = None
            for monitor in monitors:
                if (monitor['left'] <= target_right <= monitor['right'] and 
                    monitor['top'] <= target_top <= monitor['bottom']):
                    target_monitor = monitor
                    break
            
            if not target_monitor:
                target_monitor = monitors[0]

            x = target_right + 5
            y = target_top

            window_width = 380
            if x + window_width > target_monitor['right']:
                # 오른쪽 경계를 넘어가면 타겟 윈도우 왼쪽에 배치
                x = rect[0] - window_width - 5
                # 왼쪽 경계도 넘어가면 타겟 윈도우 위에 배치
                if x < target_monitor['left']:
                    x = rect[0]
                    y = rect[1] - 500 - 5
                    # 위쪽 경계도 넘어가면 타겟 윈도우 아래에 배치
                    if y < target_monitor['top']:
                        y = rect[3] + 5 
            current_time = int(time.time() * 1000)
            new_pos = (x, y)
            
            current_x = self.window.winfo_x()
            current_y = self.window.winfo_y()
            
            if (abs(current_x - x) > 5 or abs(current_y - y) > 5) and \
            (current_time - self.position_update_time > self.throttle_delay):
                
                self.position_update_time = current_time
                self.target_window_pos = new_pos
                
                if self.smooth_animation:
                    if self.animation_id:
                        self.window.after_cancel(self.animation_id)
                    self.animate_window_position()
                else:
                    self.window.geometry(f"380x500+{x}+{y}")
            
            foreground_hwnd = win32gui.GetForegroundWindow()
            if hwnd == foreground_hwnd:
                self.window.attributes("-topmost", True)
            else:
                self.window.attributes("-topmost", False)
                
        except Exception as e:
            print(f"attach_to_window error: {e}")

    def get_monitor_info(self):
        monitors = []
        
        try:
            import ctypes
            from ctypes import wintypes

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT),
                    ('dwFlags', wintypes.DWORD)
                ]
            
            MonitorFromWindow = ctypes.windll.user32.MonitorFromWindow
            GetMonitorInfo = ctypes.windll.user32.GetMonitorInfoW

            def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(mi)
                GetMonitorInfo(hMonitor, ctypes.byref(mi))

                monitor_info = {
                    'left': mi.rcWork.left,
                    'top': mi.rcWork.top,
                    'right': mi.rcWork.right,
                    'bottom': mi.rcWork.bottom,
                    'width': mi.rcWork.right - mi.rcWork.left,
                    'height': mi.rcWork.bottom - mi.rcWork.top,
                    'is_primary': (mi.dwFlags & 1) == 1  # MONITORINFOF_PRIMARY
                }
                monitors.append(monitor_info)
                return True
            
            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HMONITOR,
                wintypes.HDC,
                ctypes.POINTER(wintypes.RECT),
                wintypes.LPARAM
            )

            EnumDisplayMonitors = ctypes.windll.user32.EnumDisplayMonitors
            EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
            
            monitors.sort(key=lambda m: not m['is_primary'])
            
        except Exception as e:
            print(f"모니터 정보 가져오기 실패: {e}")
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            monitors.append({
                'left': 0,
                'top': 0,
                'right': screen_width,
                'bottom': screen_height,
                'width': screen_width,
                'height': screen_height,
                'is_primary': True
            })
        
        return monitors
    def animate_window_position(self):
        """부드러운 창 위치 애니메이션"""
        current_x = self.window.winfo_x()
        current_y = self.window.winfo_y()
        target_x, target_y = self.target_window_pos

        diff_x = target_x - current_x
        diff_y = target_y - current_y

        if abs(diff_x) < 2 and abs(diff_y) < 2:
            self.window.geometry(f"380x500+{target_x}+{target_y}")
            self.animation_id = None
            return

        new_x = current_x + diff_x // 5
        new_y = current_y + diff_y // 5

        self.window.geometry(f"380x500+{new_x}+{new_y}")

        self.animation_id = self.window.after(16, self.animate_window_position) 

def adaptive_watcher(gui):
    last_seen_texts = set()
    log("파일 관리자 시작")
    last_window_check_time = 0
    window_check_interval = 100

    while True:
        current_time = int(time.time() * 1000)

        if current_time - last_window_check_time > window_check_interval:
            last_window_check_time = current_time

            top_windows = find_window_by_title_keyword(TARGET_WINDOW_TITLE)
            if not top_windows:
                gui.window.withdraw()
                gui.clear_files()
                last_seen_texts.clear()
                time.sleep(0.5)
                continue
            hwnd = top_windows[0]
            gui.attach_to_window(hwnd)
            gui.window.deiconify()

        valid_texts = find_controls_by_size_pattern(hwnd)
        current_texts = set(text for _, text in valid_texts)

        if current_texts != last_seen_texts:
            gui.clear_files()
            for text in current_texts:
                filename = extract_filename(text)
                gui.add_file(filename)

                filepath = os.path.join(DOWNLOAD_PATH, filename)
                if not os.path.exists(filepath):
                    if click_button_by_text(hwnd, SAVE_BUTTON_TEXT):
                        gui.update_status(f"'{filename}' 다운로드 요청 중...")
            
            file_count = len(current_texts)
            gui.update_status(f"총 {file_count}개 파일 발견됨")
            last_seen_texts = current_texts

        time.sleep(0.05)
def main():
    gui = FileManagerGUI()

    watcher_thread = threading.Thread(target=adaptive_watcher, args=(gui,), daemon=True)
    watcher_thread.start()

    gui.window.mainloop()

if __name__ == "__main__":
    mimetypes.init()
    main()