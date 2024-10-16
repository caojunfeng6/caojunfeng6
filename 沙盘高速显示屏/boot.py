from machine import Pin, SPI
from package import st7789py as st
from package import vga1_16x32 as font
from package import font_gb_16x16 as font_gb
import time
from time import sleep
import usocket as socket
import _thread
import network
import ujson

# 接线说明：屏幕为ST7789-240x320，开发板为ESP32
# VCC -> 3.3V
# GND -> GND
# CS -> GPIO5
# RES -> GPIO15
# DC -> GPIO2
# MOSI -> GPIO23
# SCK -> GPIO18
# BLC -> GPIO22

def read_config(file_path):
    try:
        with open(file_path, 'r') as f:
            config = ujson.load(f)
        return config
    except Exception as e:
        print("读取配置文件时发生错误:", e)
        return None
# 从 config.json 读取 Wi-Fi 配置
config = read_config('config.json')
if not config:
    raise Exception("配置文件读取失败")

wifi_ssid = config.get('wifi_ssid')
wifi_password = config.get('wifi_password')
# 设置服务器的IP地址和端口号
SERVER_IP = config.get('server_ip')
SERVER_PORT = config.get('server_port')
print(wifi_ssid,wifi_password,SERVER_IP,SERVER_PORT)

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        print('连接到网络...')
        wlan.active(True)
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    print('网络已连接')
    print('网络配置:', wlan.ifconfig())

def ping_thread(sock):
    last_ping_time = time.time()
    while True:
        current_time = time.time()
        if current_time - last_ping_time >= 15:
            print("ping")
            sock.send(b"PING")
            last_ping_time = current_time
        time.sleep(1)  # 每秒检查一次时间

device_no = "l_parking_led_2"

class Display():
    def __init__(self):
        self.tft = st.ST7789(SPI(2, 10000000), 320, 240, reset=Pin(17), dc=Pin(2), cs=Pin(5), backlight=Pin(22), rotation=0)
        self.WHITE = st.color565(255, 255, 255)#BRG
        self.BLACK = st.color565(0, 0, 0)
        self.RED = st.color565(0, 255, 0)
        self.GREEN = st.color565(0, 0, 255)
        self.BLUE = st.color565(255, 0, 0)
        self.YELLOW = st.color565(0, 255, 255)
        print(self.RED,self.GREEN,self.BLUE,1234)
        self.last_hour = 0
        self.last_minute = 0
        self.last_second = 0
        self.last_year = 0
        self.last_month = 0
        self.last_day = 0
        self.init_show()
    def init_show(self):
        '''
        初始化显示画面
        '''
        self.tft.text_gb48(font_gb,32, '鄂HH7T07', 30, 190, self.WHITE, self.BLACK)
        self.tft.text_gb48(font_gb,32, '欢迎光临', 70, 260, self.RED, self.BLACK)
        #self.tft.text_gb48(font_gb,32, ':', 20+24*5, 100, self.WHITE, self.BLACK)
        #self.tft.text_gb48(font_gb,32, '00', 20, 100, self.WHITE, self.BLACK)
        #self.tft.text_gb48(font_gb,32, '00', 20+24*3, 100, self.WHITE, self.BLACK)
        #self.tft.text_gb48(font_gb,32, '00', 20+24*6, 100, self.WHITE, self.BLACK)
        self.text_gb('湖北高速欢迎您')
        #self.wl('Entrance')
        self.zl('ETC专用自助缴费')
        self.sl('一车一杆 保持车距')
    def text_gb(self,text):
        self.tft.text_gb32(font_gb,32, text, 5, 15, self.YELLOW, self.BLACK)
    def text(self,text):
        self.tft.text_gb32(font_gb,32, text, 30, 70, self.GREEN, self.BLACK)
    def wl(self,text):
        self.tft.text(font,32, text, 0, 50, self.GREEN, self.BLACK)
    def zl(self,text):
        self.tft.text_gb24(font_gb,24, text, 5, 80, self.GREEN, self.BLACK)
    def sl(self,text):
        self.tft.text_gb24(font_gb,24, text, 5, 130, self.GREEN, self.BLACK)
    def park(self,text):
        self.tft.text_gb48(font_gb,32, text, 30, 190, self.WHITE, self.BLACK)
    def state(self,text):
        self.tft.text_gb32(font_gb,32, text, 55, 240, self.GREEN, self.BLACK)
        #self.tft.text(font,32, text, 5, 260, self.BLUE, self.BLACK)
    def connect_wifi(self,ssid, password):
        wlan = network.WLAN(network.STA_IF)
        if not wlan.isconnected():
            print('连接到网络...')
            wlan.active(True)
            wlan.connect(ssid, password)
            
            while not wlan.isconnected():
                pass
        print('网络配置:', wlan.ifconfig())
    def show_time(self,t):
        '''
        显示时间
        '''
        year = t[0]
        month = t[1]
        day = t[2]
        hour = t[3]
        minute = t[4]
        second = t[5]
        ti = "{:0>2d}:{:0>2d}:{:0>2d}".format(hour,minute,second)
        #print(ti)
        if hour != self.last_hour:
            self.tft.text_gb48(font_gb,32, '{:0>2d}'.format(hour), 20, 100, self.BLUE, self.BLACK)
            self.last_hour = hour
        if minute != self.last_minute:
            self.tft.text_gb48(font_gb,32, '{:0>2d}'.format(minute), 20+24*3, 100, self.RED, self.BLACK)
            self.last_minute = minute
        if second != self.last_second:
            self.tft.text_gb48(font_gb,32, '{:0>2d}'.format(second), 20+24*6, 100, self.GREEN, self.BLACK)
            self.last_second = second
        #self.tft.text_gb48(font_gb,32, ti, 20, 100, self.WHITE, self.BLACK)

    def receive_and_process_socket_data(self):
        sock = None
        while True:
            try:
                # 创建一个 TCP Socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                # 连接到服务器
                sock.connect((SERVER_IP, SERVER_PORT))
                print("成功连接到服务器")
                while True:

                    # 接收响应
                    response = sock.recv(1024)  # 一次最多接收1024字节的数据
                    json_pong = response.decode('utf-8')
                    print("recive:"+json_pong)
                    json_strings = response.decode('utf-8').replace('PONG', '').split('\n')
                    if json_pong == 'PONG' or json_pong == '':
                        # 如果服务器响应pong，则无需处理
                        continue
                    else:
                        print(device_no)
                        for json_str in json_strings:
                            if json_str.strip():
                                data = ujson.loads(json_str)
                                print("json data:", data)
                                if data['from'] == 'system' and data['command'] == 'input_device_no':
                                    cdata = {"from":data['to'],"to":"system","command":device_no} #定义设备编号
                                    modified_json_str = ujson.dumps(cdata)
                                    sock.send(modified_json_str)
                                    _thread.start_new_thread(ping_thread, (sock,))
                                # 外界控制包括web端和其他设备
                                elif data['to'] == device_no and data['command'] == 'plate':
                                    print("rms")
                                    self.park(data['data']['result'])

            except OSError as e:
                print("发送或接收数据时发生错误:", e)
                time.sleep(0.5)  # 等待0.5秒后重试
                continue
            except Exception as e:
                print("发生未知错误:", e)
                time.sleep(0.5)  # 等待0.5秒后重试
                continue
            finally:
                # 关闭 Socket 连接
                try:
                    sock.close()
                except:
                    pass
   
    def __del__(self):
        pass
D = Display()
D.connect_wifi(wifi_ssid, wifi_password)
D.receive_and_process_socket_data()


