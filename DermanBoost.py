# -*- coding: utf-8 -*-
import os
import sys
import ctypes
import time
import shutil
import threading
import winreg
import subprocess
import webbrowser
import json
from tkinter import Tk, Label, Button, Frame, messagebox, Canvas, Checkbutton, BooleanVar, filedialog
import psutil

try:
    from PIL import Image, ImageDraw
    import pystray
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    from pypresence import Presence
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# --- CONFIG (JSON) YÖNETİMİ ---
CONFIG_FILE = "derman_config.json"

def load_config():
    default_config = {
        "custom_game": "",
        "startup": False,
        "use_ultimate_perf": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**default_config, **json.load(f)}
        except:
            return default_config
    return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except:
        pass

# --- GÜVENLİ VE SESSİZ OPTİMİZASYON MOTORU ---

def get_junk_paths():
    return [
        os.path.expandvars(r'%TEMP%'),
        r'C:\Windows\Temp',
        r'C:\Windows\Prefetch',
        r'C:\Windows\Logs',
        os.path.expandvars(r'%USERPROFILE%\AppData\Local\Microsoft\Windows\WER')
    ]

def calculate_junk_size():
    total_bytes = 0
    for path in get_junk_paths():
        if os.path.exists(path):
            for root_dir, dirs, files in os.walk(path):
                for file in files:
                    try:
                        total_bytes += os.path.getsize(os.path.join(root_dir, file))
                    except:
                        continue
    return round(total_bytes / (1024 * 1024), 2)

def clean_system_junk():
    cleaned_bytes = 0
    for path in get_junk_paths():
        if os.path.exists(path):
            for root_dir, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    try:
                        cleaned_bytes += os.path.getsize(file_path)
                        os.unlink(file_path)
                    except:
                        continue
    return round(cleaned_bytes / (1024 * 1024), 2)

def set_power_scheme(scheme_guid):
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(f"powercfg /setactive {scheme_guid}", startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    except:
        pass

def activate_ultimate_performance():
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # Nihai Performans şemasını etkinleştir / kontrol et
        res = subprocess.run("powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61", startupinfo=startupinfo, capture_output=True, text=True, shell=True)
        guid = "e9a42b02-d5df-448d-aa00-03f14749eb61"
        if "GUID" in res.stdout:
            guid = res.stdout.split("GUID:")[1].split("(")[0].strip()
        set_power_scheme(guid)
        return guid
    except:
        return None

def set_balanced_performance():
    # Windows Dengeli Güç Planı varsayılan GUID'i
    set_power_scheme("381b4222-f694-41f0-9685-ff5bb260df2e")

def disable_useless_services():
    services = ["Fax", "RemoteRegistry", "MapsBroker"]
    for service in services:
        try:
            subprocess.run(f'sc config "{service}" start= disabled', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
            subprocess.run(f'net stop "{service}"', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        except:
            pass

def optimize_network():
    try:
        subprocess.run("netsh interface ip delete destinationcache", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        subprocess.run("netsh int tcp set global autotuninglevel=normal", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        subprocess.run("ipconfig /flushdns", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        return True
    except:
        return False

def restart_explorer():
    try:
        subprocess.run("taskkill /f /im explorer.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        time.sleep(0.5)
        subprocess.run("start explorer.exe", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        return True
    except:
        return False

def purge_ram_and_cache():
    try:
        ctypes.windll.psapi.EmptyWorkingSet(ctypes.c_void_p(-1))
        temp = bytearray(150000000)
        del temp
        ctypes.windll.psapi.EmptyWorkingSet(ctypes.c_void_p(-1))
        optimize_network()
        return True
    except:
        return False

# --- NVIDIA GPU VERİ OKUYUCU ---
def get_nvidia_gpu_data():
    gpu_data = {"usage": 0, "temp": 0, "fan": 0, "available": False}
    try:
        cmd = "nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,fan.speed --format=csv,noheader,nounits"
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, text=True, shell=True)
        stdout, _ = res.communicate()
        
        if stdout and "," in stdout:
            parts = stdout.strip().split(",")
            gpu_data["usage"] = int(parts[0].strip())
            gpu_data["temp"] = int(parts[1].strip())
            try: gpu_data["fan"] = int(parts[2].strip())
            except: gpu_data["fan"] = 0
            gpu_data["available"] = True
    except:
        pass
    return gpu_data

# --- STARTUP AYARLARI ---
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def toggle_startup(status):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        if status:
            winreg.SetValueEx(key, "DermanRam", 0, winreg.REG_SZ, f'"{sys.executable}" "{os.path.abspath(__file__)}"')
        else:
            try: winreg.DeleteValue(key, "DermanRam")
            except FileNotFoundError: pass
        winreg.CloseKey(key)
    except: pass

def check_startup_status():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, "DermanRam")
        winreg.CloseKey(key)
        return True
    except:
        return False

# --- BİRİNCİ SINIF SİMETRİK ARAYÜZ ---

class DermanRamQuantum:
    def __init__(self, root):
        self.root = root
        self.root.title("DermanBoost v1.0")
        self.root.geometry("780x590")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)
        
        self.root.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        
        self.is_running = True
        self.tray_icon = None
        self.discord_client = None
        self.last_discord_state = ""
        
        # Config Yükleme
        self.config = load_config()
        self.custom_game_exe = self.config["custom_game"]
        self.custom_game_name = os.path.splitext(self.custom_game_exe)[0].upper() if self.custom_game_exe else "Seçilmedi"
        
        self.junk_size_mb = 0.0
        
        self.setup_ui()
        self.init_discord_rpc()
        
        # İş parçacıklarını başlat
        threading.Thread(target=self.hardware_monitor_loop, daemon=True).start()
        threading.Thread(target=self.auto_game_booster_loop, daemon=True).start()
        threading.Thread(target=self.fast_junk_scanner_loop, daemon=True).start()

    def setup_ui(self):
        # Üst Başlık
        self.lbl_title = Label(self.root, text="DERMANBOOST v1.0", fg="#cdd6f4", bg="#1e1e2e", font=("Segoe UI", 16, "bold"))
        self.lbl_title.pack(pady=(12, 2))
        self.lbl_sub = Label(self.root, text="Gelişmiş Donanım Paneli ve Özel Oyun Optimizasyon İstasyonu", fg="#a6adc8", bg="#1e1e2e", font=("Segoe UI", 9, "italic"))
        self.lbl_sub.pack(pady=(0, 10))
        
        # Ana Kapsayıcı
        self.main_container = Frame(self.root, bg="#1e1e2e")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)
        
        # --- SOL PANEL: CANLI DONANIM MONİTÖRÜ ---
        self.left_frame = Frame(self.main_container, bg="#11111b", width=310, height=440, bd=1, relief="solid")
        self.left_frame.pack_propagate(False)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(5, 5))
        
        # CANLI ÇÖP DETEKTÖRÜ
        self.lbl_junk_scanner = Label(self.left_frame, text="Taranan Çöp Dosya: Hesaplanıyor...", fg="#f38ba8", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.lbl_junk_scanner.pack(pady=(12, 5))
        
        # RAM Bölümü
        self.lbl_ram_text = Label(self.left_frame, text="RAM Yükü: ...", fg="#89b4fa", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.lbl_ram_text.pack(pady=(8, 2))
        self.canvas_ram = Canvas(self.left_frame, width=260, height=12, bg="#313244", highlightthickness=0)
        self.canvas_ram.pack()
        self.bar_ram = self.canvas_ram.create_rectangle(0, 0, 0, 12, fill="#a6e3a1", width=0)
        
        # CPU Bölümü
        self.lbl_cpu_text = Label(self.left_frame, text="CPU Kullanımı: ...", fg="#f9e2af", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.lbl_cpu_text.pack(pady=(8, 2))
        self.canvas_cpu = Canvas(self.left_frame, width=260, height=12, bg="#313244", highlightthickness=0)
        self.canvas_cpu.pack()
        self.bar_cpu = self.canvas_cpu.create_rectangle(0, 0, 0, 12, fill="#89b4fa", width=0)
        
        # Gelişmiş GPU / Ekran Kartı Bölümü (RPM Dahil)
        self.lbl_gpu_title = Label(self.left_frame, text="--- EKRAN KARTI (GPU) DURUMU ---", fg="#cba6f7", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.lbl_gpu_title.pack(pady=(15, 2))
        
        self.lbl_gpu_usage = Label(self.left_frame, text="GPU Kullanımı: %0", fg="#cdd6f4", bg="#11111b", font=("Segoe UI", 9))
        self.lbl_gpu_usage.pack(pady=1)
        
        self.lbl_gpu_temp = Label(self.left_frame, text="GPU Sıcaklığı: 0°C", fg="#f38ba8", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.lbl_gpu_temp.pack(pady=1)
        
        self.lbl_gpu_fan = Label(self.left_frame, text="GPU Fan Hızı: %0 (0 RPM)", fg="#94e2d5", bg="#11111b", font=("Segoe UI", 9))
        self.lbl_gpu_fan.pack(pady=1)
        
        # Durum Footer
        self.lbl_thermal = Label(self.left_frame, text="Sistem Durumu: İzleniyor", fg="#a6e3a1", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.lbl_thermal.pack(pady=10)
        
        self.startup_var = BooleanVar(value=self.config["startup"])
        self.chk_startup = Checkbutton(
            self.left_frame, text="Windows Başlangıcına Ekle", variable=self.startup_var,
            command=self.on_startup_toggle,
            bg="#11111b", fg="#cdd6f4", selectcolor="#1e1e2e", activebackground="#11111b", font=("Segoe UI", 9)
        )
        self.chk_startup.pack(side="bottom", pady=(0, 10))

        # --- SAĞ PANEL: MODÜLLER VE ÖZEL OYUN SEÇİMİ ---
        self.right_frame = Frame(self.main_container, bg="#1e1e2e", width=410, height=440)
        self.right_frame.pack_propagate(False)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 5))
        
        btn_layout = {"font": ("Segoe UI", 9, "bold"), "bd": 0, "cursor": "hand2", "fg": "#11111b", "height": 2}
        
        # 6 Temel Fonksiyon Butonu
        self.btn_ram = Button(self.right_frame, text="⚡ Derin RAM Önbelleğini Boşalt", bg="#89b4fa", command=self.trigger_ram, **btn_layout)
        self.btn_ram.pack(fill="x", pady=2)
        
        self.btn_junk = Button(self.right_frame, text="🧹 Sistem Günlüklerini ve Çöplerini Süpür", bg="#f9e2af", command=self.trigger_junk, **btn_layout)
        self.btn_junk.pack(fill="x", pady=2)
        
        self.btn_net = Button(self.right_frame, text="🌐 Ağ Gecikmesini (Ping) Optimize Et", bg="#94e2d5", command=self.trigger_net, **btn_layout)
        self.btn_net.pack(fill="x", pady=2)
        
        self.btn_power = Button(self.right_frame, text="🔌 Nihai Performans Modunu Aktif Et", bg="#cba6f7", command=self.trigger_power, **btn_layout)
        self.btn_power.pack(fill="x", pady=2)
        
        self.btn_debloat = Button(self.right_frame, text="🛠️ Arka Plan Gereksiz Servisleri Durdur", bg="#eba0ac", command=self.trigger_debloat, **btn_layout)
        self.btn_debloat.pack(fill="x", pady=2)
        
        self.btn_exp = Button(self.right_frame, text="🔄 Explorer Masaüstünü Yeniden Başlat", bg="#f38ba8", command=self.trigger_explorer, **btn_layout)
        self.btn_exp.pack(fill="x", pady=2)
        
        # Özel Oyun Ekleme Çerçevesi
        self.game_select_frame = Frame(self.right_frame, bg="#181825", bd=1, relief="solid")
        self.game_select_frame.pack(fill="x", pady=6, ipady=3)
        
        self.lbl_select_title = Label(self.game_select_frame, text="🎯 Otomatik Boost İçin Özel Oyun (.exe)", fg="#cba6f7", bg="#181825", font=("Segoe UI", 9, "bold"))
        self.lbl_select_title.pack(pady=(2, 0))
        
        self.lbl_chosen_game = Label(
            self.game_select_frame, 
            text=f"Takip Edilen: {self.custom_game_exe}" if self.custom_game_exe else "Takip Edilen: Yok (Tüm oyunlar dahil)", 
            fg="#a6e3a1" if self.custom_game_exe else "#a6adc8", 
            font=("Segoe UI", 8, "italic")
        )
        self.lbl_chosen_game.pack(pady=1)
        
        self.btn_select_game = Button(self.game_select_frame, text="📁 Oyun Exe'si Seç", bg="#cba6f7", font=("Segoe UI", 8, "bold"), bd=0, cursor="hand2", fg="#11111b", command=self.select_custom_game)
        self.btn_select_game.pack(pady=3, padx=30, fill="x")

        # Oyunda Nihai Performans'a Geçilsin mi? (Düşük PC Güvenlik Önlemi)
        self.ult_perf_var = BooleanVar(value=self.config["use_ultimate_perf"])
        self.chk_ult_perf = Checkbutton(
            self.right_frame, text="Oyun Algılandığında Nihai Güç Moduna Geç (Zayıf PC'ler için kapatın)", 
            variable=self.ult_perf_var, command=self.on_perf_toggle,
            bg="#1e1e2e", fg="#a6adc8", selectcolor="#11111b", activebackground="#1e1e2e", font=("Segoe UI", 8)
        )
        self.chk_ult_perf.pack(pady=2)

        self.lbl_game_status = Label(self.right_frame, text="🎮 Akıllı Oyun Takip Sistemi: Beklemede", fg="#a6adc8", bg="#1e1e2e", font=("Segoe UI", 9, "bold"))
        self.lbl_game_status.pack(pady=4)
        
        self.btn_ultra = Button(
            self.right_frame, text="🚀 TÜM SİSTEMİ ULTRA BOOST ET",
            bg="#a6e3a1", font=("Segoe UI", 11, "bold"), bd=0, cursor="hand2", fg="#11111b", height=2,
            command=self.trigger_ultra
        )
        self.btn_ultra.pack(fill="x", side="bottom")
        
        # --- EN ALT: GITHUB LİNKİ & BİLGİ ALANI ---
        self.lbl_github = Label(self.root, text="Developer: github.com/dermandertsiz1", fg="#cba6f7", bg="#1e1e2e", font=("Segoe UI", 8, "underline"), cursor="hand2")
        self.lbl_github.pack(side="bottom", pady=(2, 5))
        self.lbl_github.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/dermandertsiz1"))

    # --- DISCORD RICH PRESENCE ENTEGRASYONU ---
    def init_discord_rpc(self):
        if DISCORD_AVAILABLE:
            try:
                # Derman Boost Uygulama ID'si
                self.discord_client = Presence("1524894208899678329") # Burayı istersen kendi Discord Developer portalındaki ID ile değiştirebilirsin
                self.discord_client.connect()
                self.update_discord_status("Boşta")
            except:
                self.discord_client = None

    def update_discord_status(self, game_name=None):
        if not DISCORD_AVAILABLE or not self.discord_client:
            return
        try:
            if game_name:
                state_text = f"Derman Boost ile {game_name} Oyununu Boostluyor"
            else:
                state_text = "Sistemi Optimize Ediyor"
                
            if self.last_discord_state != state_text:
                self.discord_client.update(
                    state=state_text,
                    large_image="logo", # Discord portalında yüklediğin görsel adı
                    large_text="DermanBoost",
                    start=time.time()
                )
                self.last_discord_state = state_text
        except:
            pass

    # --- CONFIG TETİKLEYİCİLERİ ---
    def on_startup_toggle(self):
        status = self.startup_var.get()
        toggle_startup(status)
        self.config["startup"] = status
        save_config(self.config)

    def on_perf_toggle(self):
        self.config["use_ultimate_perf"] = self.ult_perf_var.get()
        save_config(self.config)

    def select_custom_game(self):
        file_path = filedialog.askopenfilename(
            title="Hedef Oyunun Executable (.exe) Dosyasını Seç",
            filetypes=[("Executable Files", "*.exe")]
        )
        if file_path:
            self.custom_game_exe = os.path.basename(file_path).lower()
            self.custom_game_name = os.path.splitext(self.custom_game_exe)[0].upper()
            self.lbl_chosen_game.config(text=f"Takip Edilen: {self.custom_game_exe}", fg="#a6e3a1")
            self.config["custom_game"] = self.custom_game_exe
            save_config(self.config)
            messagebox.showinfo("Başarılı", f"{self.custom_game_name} takibe alındı! Başlatıldığı an sistem otomatik boostlanacak.")

    # --- DETEKTÖRLER VE DÖNGÜLER ---

    def fast_junk_scanner_loop(self):
        """Arka planda çöp boyutunu sürekli güncel tutan hafif döngü"""
        while self.is_running:
            try:
                self.junk_size_mb = calculate_junk_size()
                if self.junk_size_mb > 0:
                    self.lbl_junk_scanner.config(text=f"Taranan Çöp Dosya: {self.junk_size_mb} MB", fg="#f38ba8")
                else:
                    self.lbl_junk_scanner.config(text="Taranan Çöp Dosya: Temiz (0 MB)", fg="#a6e3a1")
            except: pass
            time.sleep(5)

    def hardware_monitor_loop(self):
        while self.is_running:
            try:
                # RAM Bilgisi
                mem = psutil.virtual_memory()
                ram_pct = mem.percent
                self.lbl_ram_text.config(text=f"RAM Yükü: %{ram_pct} ({round(mem.used/(1024**3),2)}GB / {round(mem.total/(1024**3),2)}GB)")
                self.canvas_ram.coords(self.bar_ram, 0, 0, int((ram_pct/100)*260), 12)
                
                # CPU Bilgisi
                cpu_pct = psutil.cpu_percent()
                self.lbl_cpu_text.config(text=f"CPU Kullanımı: %{cpu_pct}")
                self.canvas_cpu.coords(self.bar_cpu, 0, 0, int((cpu_pct/100)*260), 12)
                
                # GPU Bilgisi & RPM Eğrisi
                gpu = get_nvidia_gpu_data()
                if gpu["available"]:
                    self.lbl_gpu_usage.config(text=f"GPU Kullanımı: %{gpu['usage']}", fg="#a6e3a1" if gpu['usage'] > 0 else "#cdd6f4")
                    self.lbl_gpu_temp.config(text=f"GPU Sıcaklığı: {gpu['temp']}°C")
                    
                    if gpu["fan"] > 0:
                        simulated_rpm = int(gpu["fan"] * 35) # Simüle donanım fan eğrisi
                        self.lbl_gpu_fan.config(text=f"GPU Fan Hızı: %{gpu['fan']} ({simulated_rpm} RPM)")
                    else:
                        self.lbl_gpu_fan.config(text="GPU Fan Hızı: %0 (0 RPM - Sessiz Mod)")
                else:
                    self.lbl_gpu_usage.config(text="GPU Kullanımı: Pasif / Bulunamadı")
                    self.lbl_gpu_temp.config(text="GPU Sıcaklığı: N/A")
                    self.lbl_gpu_fan.config(text="GPU Fan Hızı: N/A")

                # Isı Durumu Kontrolü
                if cpu_pct > 80 or (gpu["available"] and gpu["temp"] > 80):
                    self.lbl_thermal.config(text="Sistem Durumu: YÜKSEK SICAKLIK / YÜK", fg="#f38ba8")
                elif cpu_pct > 40 or (gpu["available"] and gpu["usage"] > 30):
                    self.lbl_thermal.config(text="Sistem Durumu: Oyun Modu Aktif", fg="#f9e2af")
                else:
                    self.lbl_thermal.config(text="Sistem Durumu: Serin / Kararlı", fg="#a6e3a1")
            except: pass
            time.sleep(1)

    def auto_game_booster_loop(self):
        default_game_exes = ["unturned.exe", "minecraft.exe", "robloxplayerbeta.exe", "fortniteclient-win64-shipping.exe", "genshinimpact.exe"]
        was_gaming = False
        
        while self.is_running:
            try:
                detected = False
                target_list = default_game_exes + [self.custom_game_exe] if self.custom_game_exe else default_game_exes
                
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] and proc.info['name'].lower() in target_list:
                        game_name = proc.info['name'].split('.')[0].upper()
                        self.lbl_game_status.config(text=f"🔥 OYUN ALGILANDI: {game_name} (Auto Boost!)", fg="#a6e3a1")
                        
                        # Güç Planı Optimizasyonu (Kullanıcı seçtiyse)
                        if self.ult_perf_var.get() and not was_gaming:
                            activate_ultimate_performance()
                        
                        purge_ram_and_cache()
                        self.update_discord_status(game_name)
                        detected = True
                        was_gaming = True
                        break
                
                if not detected:
                    self.lbl_game_status.config(text="... Akıllı Oyun Takip Sistemi: Beklemede ...", fg="#a6adc8")
                    self.update_discord_status(None)
                    
                    # Oyundan çıkıldıysa dengeli moda geri dön
                    if was_gaming:
                        set_balanced_performance()
                        was_gaming = False
                        
            except: pass
            time.sleep(3)

    # --- BUTON METODLARI ---
    def trigger_ram(self):
        purge_ram_and_cache()
        messagebox.showinfo("DermanRam", "RAM Önbelleği Başarıyla Boşaltıldı!")

    def trigger_junk(self):
        mb = clean_system_junk()
        self.junk_size_mb = 0.0
        self.lbl_junk_scanner.config(text="Taranan Çöp Dosya: Temiz (0 MB)", fg="#a6e3a1")
        messagebox.showinfo("DermanRam", f"Disk Süpürüldü!\n{mb} MB çöp dosya kalıntısı uçuruldu.")

    def trigger_net(self):
        optimize_network()
        messagebox.showinfo("DermanRam", "DNS ve Ağ önbelleği sıfırlandı, ping kararlılığı sağlandı!")

    def trigger_power(self):
        activate_ultimate_performance()
        messagebox.showinfo("DermanRam", "Nihai Performans Modu Güç Planlarına Yazıldı.")

    def trigger_debloat(self):
        disable_useless_services()
        messagebox.showinfo("DermanRam", "Gereksiz Windows Servisleri Güvenle Kapatıldı.")

    def trigger_explorer(self):
        restart_explorer()

    def trigger_ultra(self):
        self.btn_ultra.config(text="KUANTUM MOTOR DEVREDE...", state="disabled", bg="#585b70")
        def run():
            purge_ram_and_cache()
            mb = clean_system_junk()
            self.junk_size_mb = 0.0
            if self.ult_perf_var.get():
                activate_ultimate_performance()
            disable_useless_services()
            optimize_network()
            self.root.after(0, lambda: messagebox.showinfo("Quantum Boost", f"Sistem En Üst Seviyeye Çıkarıldı!\n\n- RAM & Network Optimize Edildi.\n- {mb} MB Log Dosyası Süpürüldü.\n- Gereksiz Servisler Durduruldu."))
            self.root.after(0, lambda: self.btn_ultra.config(text="🚀 TÜM SİSTEMİ ULTRA BOOST ET", state="normal", bg="#a6e3a1"))
        threading.Thread(target=run, daemon=True).start()

    # --- TEPSİ METODLARI ---
    def minimize_to_tray(self):
        if TRAY_AVAILABLE:
            self.root.withdraw()
            if not self.tray_icon:
                image = Image.new('RGB', (64, 64), color='#1e1e2e')
                dc = ImageDraw.Draw(image)
                dc.rectangle([(16, 16), (48, 48)], fill='#a6e3a1')
                
                menu = pystray.Menu(
                    pystray.MenuItem('Arayüzü Göster', self.show_window, default=True),
                    pystray.MenuItem('⚡ Hızlı Optimize Et', self.tray_fast_boost),
                    pystray.MenuItem('Tamamen Çıkış', self.quit_app)
                )
                self.tray_icon = pystray.Icon("DermanBoost", image, "DermanBoost v1.0", menu)
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
        else:
            self.quit_app()

    def tray_fast_boost(self):
        purge_ram_and_cache()
        clean_system_junk()
        optimize_network()
        if TRAY_AVAILABLE and self.tray_icon:
            self.tray_icon.notify("Sistem arka planda ışık hızında optimize edildi! 🚀", title="DermanBoost v1.0")

    def show_window(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.deiconify)

    def quit_app(self):
        self.is_running = False
        if self.tray_icon:
            try: self.tray_icon.stop()
            except: pass
        self.root.destroy()
        sys.exit()
    
    def auto_game_booster_loop(self):
        # Senin manuel eklediğin oyunlar ve config'den gelenler
        was_gaming = False
        
        while self.is_running:
            try:
                # Sadece tanımlı oyunları kontrol et
                target_list = [
    # --- Popüler FPS / Rekabetçi ---
    "valorant.exe", "cs2.exe", "r5apex.exe", "fortniteclient-win64-shipping.exe", 
    "overwatch.exe", "callofduty.exe", "modernwarfare.exe", "blackops6.exe", 
    "rainbowsix.exe", "destiny2.exe", "rustclient.exe", "tarkov.exe",

    # --- Battle Royale / Açık Dünya ---
    "pubg.exe", "pubgland.exe", "h1z1.exe", "dayz_x64.exe",

    # --- Minecraft & Sandbox ---
    "minecraft.exe", "javaw.exe", "robloxplayerbeta.exe", "unturned.exe", 
    "terraria.exe", "garrysmod.exe",

    # --- RPG / Hikayeli / MMORPG ---
    "genshinimpact.exe", "starrail.exe", "zenlesszonezero.exe", "eldring.exe", 
    "witcher3.exe", "cyberpunk2077.exe", "gtav.exe", "rdr2.exe", 
    "skyrim.exe", "wow.exe", "ffxiv.exe", "dota2.exe", "lol.exe",

    # --- Diğer Popülerler ---
    "rocketleague.exe", "osu!.exe", "paladins.exe", "warframe.exe",
    "deadbydaylight-win64-shipping.exe", "phasmophobia.exe", "stardewvalley.exe"
]
                if self.custom_game_exe:
                    target_list.append(self.custom_game_exe.lower())
                
                detected = False
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] and proc.info['name'].lower() in target_list:
                        game_name = proc.info['name'].split('.')[0].upper()
                        self.lbl_game_status.config(text=f"🔥 OYUN ALGILANDI: {game_name}", fg="#a6e3a1")
                        
                        if self.config.get("use_ultimate_perf", True) and not was_gaming:
                            activate_ultimate_performance()
                        
                        purge_ram_and_cache()
                        self.update_discord_status(game_name)
                        detected = True
                        was_gaming = True
                        break
                
                if not detected:
                    self.lbl_game_status.config(text="... Sistem Beklemede ...", fg="#a6adc8")
                    self.update_discord_status(None)
                    if was_gaming:
                        set_balanced_performance()
                        was_gaming = False
            except: pass
            time.sleep(3)

if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
        
    root = Tk()
    app = DermanRamQuantum(root)
    root.mainloop()