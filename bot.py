import os
import sys
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import ctypes

import cv2
import numpy as np
import keyboard
import dxcam
import win32api
import win32gui
import win32con
from colorama import Fore, Back, Style, init

init(autoreset=True)

winmm = ctypes.WinDLL('winmm')
winmm.timeBeginPeriod(1)

def precise_sleep(duration):
    if duration <= 0:
        return
    end_time = time.perf_counter() + duration
    if duration > 0.002:
        time.sleep(duration - 0.002)
    while time.perf_counter() < end_time:
        pass

class SkylineBot:
    def __init__(self):
        self.setup_console()
        self.config = self.load_config()
        self.monitor_width = ctypes.windll.user32.GetSystemMetrics(0)
        self.monitor_height = ctypes.windll.user32.GetSystemMetrics(1)
        self.hwnd = self.get_console_hwnd()
        
        if self.config.get("console_window_ontop") == "true" and self.hwnd:
            win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        self.setup_lanes()
        self.load_assets()
        self.calculate_regions()
        
        self.lane_cooldowns = {self.config[f"key_{i}"]: 0.0 for i in range(1, self.number_of_lanes + 1)}
        self.lane_tracking = {self.config[f"key_{i}"]: {"y": 0, "time": 0, "speeds": [], "last_y": 0, "last_time": 0} for i in range(1, self.number_of_lanes + 1)}
        
        # Locked in exactly 31ms based on your specific hardware latency math
        self.auto_delay_compensation = 0.031
        
        self.camera = dxcam.create(output_color="GRAY", max_buffer_len=512)
        self.executor = ThreadPoolExecutor(max_workers=8)
        
        self.print_welcome()

    def setup_console(self):
        os.system("title Skyline Autoplayer Console")
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_welcome(self):
        print(f'''{Fore.BLUE}
   _____ __ __ __  __ __    ___  _   __  ____
  / ___// //_//\\ \\/ // /   / _ \\/ | / / / __/
  \\__ \\/ ,<    \\  // /   / // /  |/ / / _/  
 ___/ / /| |   / // /___/ // / /|  / / /___ 
/____/_/ |_|  /_//_____/____/_/ |_/ /_____/ 
''')
        print(f"{Fore.CYAN}Skyline Autoplayer - NEURAL AUTO-ADJUST MODE")
        print(f"{Fore.WHITE}Press CAPS LOCK to start tracking.")
        print(f"{Fore.WHITE}Press {str.upper(self.config['exit_key'])} to close.\n")

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except Exception:
            sys.exit(1)

    def get_console_hwnd(self):
        hwnd_list = []
        def callback(hwnd, ctx):
            if win32gui.GetWindowText(hwnd).find("Skyline Autoplayer Console") != -1:
                hwnd_list.append(hwnd)
        win32gui.EnumWindows(callback, None)
        return hwnd_list[0] if hwnd_list else None

    def setup_lanes(self):
        if self.config.get("always_single_lanemode") != "true":
            self.number_of_lanes = 4
        else:
            self.number_of_lanes = self.config["single_lanemode_lanes"]

    def load_assets(self):
        asset_dir = f"assets/{self.monitor_height}"
        suffix = self.config.get("tile_filename_suffix", "")
        self.templates = []
        def load_img(name, conf_key):
            path = f"{asset_dir}/{name}{suffix}.png"
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE).astype(np.uint8)
                self.templates.append({
                    "image": img, "w": img.shape[1], "h": img.shape[0],
                    "confidence": self.config.get(conf_key, self.config["min_confidence"])
                })
        load_img("tile", "min_confidence")
        if self.config.get("use_white_tile") == "true": load_img("white", "white_tile_min_confidence")
        if self.config.get("use_battlestage_tile") == "true": load_img("battlestage", "battlestage_tile_min_confidence")
        if self.config.get("use_diamond_tile") == "true": load_img("diamond", "diamond_tile_min_confidence")

    def calculate_regions(self):
        base_width = 555 if self.number_of_lanes == 4 else 696
        base_height = 250
        base_offset = 190
        self.scale_factor = 1080 / self.monitor_height
        self.target_y_center = int(self.config["min_tile_pixels_top_offset_scaled"] // self.scale_factor)
        
        if self.scale_factor != 1:
            base_width = int(base_width // self.scale_factor)
            base_height = int(base_height // self.scale_factor)
            base_offset = int(base_offset // self.scale_factor)

        shift = (8 // self.scale_factor) if self.number_of_lanes == 5 else 1
        self.region_left = int(((self.monitor_width - base_width) // 2) + shift)
        self.region_top = (self.monitor_height - base_height) - base_offset
        self.region_right = self.region_left + base_width
        self.region_bottom = self.region_top + base_height
        self.section_size = base_width // self.number_of_lanes

    def press_key(self, key, delay):
        if delay > 0:
            precise_sleep(delay)
        keyboard.press(key)
        precise_sleep(self.config["keypress_holdtime"])
        keyboard.release(key)

    def trigger_lane_predictive(self, key, delay):
        current_time = time.perf_counter()
        adjusted_delay = max(0, delay + self.auto_delay_compensation)
        if current_time >= self.lane_cooldowns[key]:
            self.lane_cooldowns[key] = current_time + adjusted_delay + self.config["max_lane_cooldown"] + self.config["keypress_holdtime"]
            self.executor.submit(self.press_key, key, adjusted_delay)

    def process_template(self, screenshot, template_data):
        res = cv2.matchTemplate(screenshot, template_data["image"], cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= template_data["confidence"])
        rects = []
        for pt in zip(*loc[::-1]):
            rects.append((int(pt[0]), int(pt[1]), template_data["w"], template_data["h"]))
            rects.append((int(pt[0]), int(pt[1]), template_data["w"], template_data["h"]))
        rects, _ = cv2.groupRectangles(rects, 1, 0.2)
        
        current_time = time.perf_counter()
        active_lanes = set()
        
        for (x, y, w, h) in rects:
            cx, cy = x + (w // 2), y + (h // 2)
            lane_idx = cx // self.section_size + 1
            lane_key = self.config.get(f"key_{lane_idx}")
            
            if lane_key:
                active_lanes.add(lane_key)
                track = self.lane_tracking[lane_key]
                
                if cy < self.target_y_center and cy > track["y"]:
                    if track["time"] > 0:
                        dt = current_time - track["time"]
                        dy = cy - track["y"]
                        if dt > 0 and dy > 0:
                            current_speed = dy / dt
                            track["speeds"].append(current_speed)
                            if len(track["speeds"]) > 3:
                                track["speeds"].pop(0)
                    track["y"] = cy
                    track["time"] = current_time
                    track["last_y"] = cy
                    track["last_time"] = current_time
                
                if cy >= self.target_y_center - 15:
                    if len(track["speeds"]) > 0 and cy < self.target_y_center:
                        average_speed = sum(track["speeds"]) / len(track["speeds"])
                        distance_left = self.target_y_center - cy
                        delay = distance_left / average_speed
                        self.trigger_lane_predictive(lane_key, min(delay, 0.1))
                    elif cy >= self.target_y_center - 5:
                        self.trigger_lane_predictive(lane_key, 0)
                    
                    track["y"] = 0
                    track["time"] = 0
                    track["speeds"].clear()

        for key, track in self.lane_tracking.items():
            if key not in active_lanes and track["last_y"] > 0:
                if current_time - track["last_time"] > 0.05:
                    vanish_distance = self.target_y_center - track["last_y"]
                    # Halved the step size for smoother micro-adjustments
                    if vanish_distance > 30:
                        self.auto_delay_compensation += 0.0005
                    elif vanish_distance < -10:
                        self.auto_delay_compensation -= 0.0005
                    
                    track["last_y"] = 0
                    track["last_time"] = 0

    def run(self):
        self.camera.start(region=(self.region_left, self.region_top, self.region_right, self.region_bottom), target_fps=self.config.get("capture_fps", 200))
        try:
            exit_key = self.config['exit_key']
            while not keyboard.is_pressed(exit_key):
                if win32api.GetKeyState(0x14):
                    frame = self.camera.get_latest_frame()
                    if frame is not None:
                        for template in self.templates:
                            self.process_template(frame, template)
                else:
                    precise_sleep(0.002)
        finally:
            self.cleanup()

    def cleanup(self):
        self.camera.stop()
        self.executor.shutdown(wait=False)
        winmm.timeEndPeriod(1)
        if self.config.get("console_window_ontop") == "true" and self.hwnd:
            win32gui.SetWindowPos(self.hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

if __name__ == "__main__":
    bot = SkylineBot()
    bot.run()