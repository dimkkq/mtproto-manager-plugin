import requests
import re
import socket
import json
import os
import time
import threading
from exteragram.plugins import BasePlugin
from exteragram.plugins.settings import SettingItem, SwitchSetting, ButtonSetting, TextSetting

# КОНФИГУРАЦИЯ
PROXY_SOURCE_URL = "https://raw.githubusercontent.com/Telegram-MTProto-Proxies/List/main/proxies.txt"
STORAGE_FILE = "mtproto_cache.json"
MAX_WORKERS = 10
TIMEOUT_SEC = 3

class MTProtoManagerPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.working_proxies = []
        self.storage_path = os.path.join(self.get_plugin_dir(), STORAGE_FILE)
    
    def fetch_raw_proxies(self):
        """Скачивает сырой текст со списками прокси"""
        try:
            response = requests.get(PROXY_SOURCE_URL, timeout=10)
            response.raise_for_status()
            return re.findall(r'tg://proxy\?server=([^&]+)&port=(\d+)&secret=([^&\s]+)', response.text)
        except Exception as e:
            self.log(f"Ошибка загрузки: {e}")
            return []
    
    def check_tcp_alive(self, host, port):
        """Быстрая проверка доступности порта"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT_SEC)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def process_proxy(self, server, port, secret):
        """Проверяет один прокси"""
        if self.check_tcp_alive(server, port):
            start_time = time.time()
            is_alive = self.check_tcp_alive(server, port)
            latency = round((time.time() - start_time) * 1000, 2)
            
            if is_alive:
                self.working_proxies.append({
                    "server": server,
                    "port": port,
                    "secret": secret,
                    "latency": latency,
                    "url": f"tg://proxy?server={server}&port={port}&secret={secret}"
                })
    
    def run_check(self):
        """Основной поток проверки"""
        self.log("Запуск сбора и проверки прокси...")
        raw_list = self.fetch_raw_proxies()
        if not raw_list:
            self.log("Список прокси пуст или источник недоступен.")
            return
        
        self.working_proxies = []
        threads = []
        
        for server, port, secret in raw_list[:50]:
            t = threading.Thread(target=self.process_proxy, args=(server, port, secret))
            threads.append(t)
            t.start()
            if len(threads) >= MAX_WORKERS:
                for th in threads: th.join()
                threads = []
        
        for th in threads: th.join()
        
        self.working_proxies.sort(key=lambda x: x["latency"])
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.working_proxies, f, indent=2)
        
        self.log(f"Проверка завершена. Найдено рабочих: {len(self.working_proxies)}")
        
        if self.working_proxies:
            best = self.working_proxies[0]
            self.log(f"ЛУЧШИЙ ПРОКСИ: {best['url']}")
            self.log(f"Задержка: {best['latency']} мс")
            self.show_notification("MTProto Manager", f"Найден прокси: {best['server']}:{best['port']} ({best['latency']} мс)")
    
    def create_settings(self):
        return [
            TextSetting("MTProto Auto Manager", "Автоматический поиск и проверка прокси"),
            ButtonSetting("Обновить прокси", self.run_check),
            TextSetting(f"Найдено рабочих прокси: {len(self.working_proxies)}")
        ]
    
    def log(self, message):
        """Вывод в лог плагина"""
        print(f"[MTProtoManager] {message}")

# Точка входа
plugin = MTProtoManagerPlugin()