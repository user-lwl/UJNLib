# !/usr/bin/env python
# -*- coding:utf-8 -*-

'''
学校图书馆座位
自动化预约
'''
import random
import re

import requests
import time

from datetime import datetime, timedelta

from logger_seat import logger
from threading import Thread
from config import ACCOUNTS, send_wechat, USER_AGENTS
from verifyClick import SeatVerification

from selenium import webdriver
from selenium.webdriver import ActionChains
#from seleniumwire import webdriver
#from selenium.webdriver.firefox.service import Service as serviceFirefox
from selenium.webdriver.chrome.service import Service as serviceChrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


class GrabNumber(Thread):
    def __init__(self, wechat, date_appointment, start_time, end_time, seconds_execute, time_execute, user_agent, proxies):
        super(GrabNumber, self).__init__()  # 重写写父类的__init__方法
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'seat.ujn.edu.cn',
            #'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Mobile Safari/537.36',
            'User-Agent': user_agent,
            'X-Requested-With': 'XMLHttpRequest',
        }

        #requests.adapters.DEFAULT_RETRIES = 5  # 增加重连次数
        requests.DEFAULT_RETRIES = 5  # 增加重连次数
        self.session = requests.session()
        self.session.keep_alive = False  # 关闭多余连接

        self.wechat = wechat
        self.date_appointment = date_appointment
        self.start_time = start_time
        self.end_time = end_time
        self.seconds_execute = seconds_execute
        self.time_execute = time_execute
        self.user_agent = user_agent
        self.proxies = proxies

        #proxy = proxies['http'].rstrip('/')

        '''
        s = serviceFirefox("./webdriver/geckodriver-v0.30.0-win64/geckodriver.exe")
        options = webdriver.FirefoxOptions()
        #options.add_argument('--headless')
        options.add_argument('user-agent="' + user_agent + '"')
        options.add_argument(('--proxy-server=' + proxy)) #开启代理IP
        self.browser = webdriver.Firefox(service=s, options=options)
        '''
        s = serviceChrome("./webdriver/chrome_win32_99.0.4844.51/chromedriver.exe")
        options = webdriver.ChromeOptions()
        options.add_argument('user-agent="' + user_agent + '"')
        if proxies['http'] != '':
            options.add_argument(('--proxy-server=' + proxies['http'])) #开启代理IP
        options.add_argument('--ignore-certificate-errors')
        # 设置反屏蔽
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        # 关闭保存密码弹窗提示
        prefs = {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False
        }
        options.add_experimental_option('prefs', prefs)

        options.add_argument("--disable-blink-features")
        options.add_argument("disable-blink-features=AutomationControlled")  # 去掉chrome的webdriver痕迹

        self.browser = webdriver.Chrome(service=s, options=options)
        self.browser.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })

        #self.browser.maximize_window()  # 将浏览器最大化
        #self.browser.set_window_size(970, 800)
        self.browser.set_window_size(1240, 800)

        self.list_cookies = []

    '''登录'''
    def login(self, cert_no, pwd):
        try:
            url = "http://seat.ujn.edu.cn/"
            self.browser.get(url)

            wait = WebDriverWait(self.browser, 10)
            # 登录按钮
            ele_login = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="login"]/dd[4]/input')))
            # 输入学号、密码
            ele = self.browser.find_element(By.NAME, 'username')
            ActionChains(self.browser).move_to_element(ele).perform()
            time.sleep(1)
            ele.send_keys(cert_no)
            time.sleep(2)
            ele = self.browser.find_element(By.NAME, 'password')
            ActionChains(self.browser).move_to_element(ele).perform()
            time.sleep(1)
            ele.send_keys(pwd)
            time.sleep(1)

            # 截图登录页面，截取图片验证码，点选验证
            verify_code = False
            for i in range(1):
                obj_verify = SeatVerification(self.browser)
                verify_code = obj_verify.run()
                if bool(verify_code):
                    break
            if not bool(verify_code):
                return False

            # 登录
            ActionChains(self.browser).click(ele_login).perform()
            time.sleep(5)

            current_url = self.browser.current_url
            if self.browser.page_source.find(self.wechat['name']) > 0: #登录成功
                # 获取cookie
                list_cookies = self.browser.get_cookies()
                logger.info('{}，对应的cookies：{}'.format(cert_no, list_cookies))
                self.list_cookies = list_cookies
                logger.info('{}，登录成功，URL：{}'.format(cert_no, current_url))
                return True
            else:
                logger.info('登录失败，当前URL：{}'.format(current_url))
                time.sleep(1.5)
                return False
        except TimeoutException as e:
            logger.info('登录超时异常，报错信息：{}'.format(e))
            logger.error('登录超时异常，报错信息：', e)
            for i in range(3):
                time.sleep(1.5)
                self.browser.get(url)
            return False
        except WebDriverException as e:
            logger.info('登录WebDriver异常，报错信息：{}'.format(e))
            logger.error('登录WebDriver异常，报错信息：', e)
            for i in range(3):
                time.sleep(1.5)
                self.browser.get(url)
            return False
        except Exception as e:
            logger.info('登录异常，报错信息：{}'.format(e))
            logger.error('登录异常，报错信息：', e)
            return False

    '''获取房间列表'''
    def listRoom(self):
        wechat = self.wechat
        wait = WebDriverWait(self.browser, 10)
        try:
            # 选择预约日期
            #ele_click = self.browser.find_element(By.ID, 'onDate_select')
            #ele_click.click()
            #time.sleep(1)
            #ele = self.browser.find_element(By.ID, 'options_onDate')
            #ele = wait.until(EC.presence_of_element_located((By.ID, 'options_onDate')))
            #print('可选日期---', ele.text)
            #if ele.text.find(self.date_appointment) < 0:
            #    logger.info('{}，没有找到指定的预约日期：{}'.format(wechat['name'], self.date_appointment))
            #    time.sleep(1)
            #    return False
            js = 'var obj = document.getElementById("display_onDate");obj.setAttribute("value", "{}");obj.innerHTML="{}";'.format(self.date_appointment, self.date_appointment)
            self.browser.execute_script(js)
            self.browser.execute_script('document.getElementById("onDate").setAttribute("value", "{}")'.format(self.date_appointment))
            #time.sleep(1)
            #ele_click.click()
            #time.sleep(3)

            # 选择场馆（西校区 building，ID=2）
            building_id = '2'
            building_name = '西校区'
            #ele_click = self.browser.find_element(By.ID, 'building_select')
            #ele_click.click()
            #time.sleep(1)
            js = 'var obj = document.getElementById("display_building");obj.setAttribute("value", "{}");obj.innerHTML="{}";'.format(building_id, building_name)
            self.browser.execute_script(js)
            self.browser.execute_script('document.getElementById("building").setAttribute("value", "{}")'.format(building_id))
            #time.sleep(1)
            #ele_click.click()
            #time.sleep(3)

            # 选择开始时间
            #ele_click = self.browser.find_element(By.ID, 'startMin_select')
            #ele_click.click()
            #time.sleep(1)
            js = 'var obj=document.getElementById("options_startMin");return obj.innerHTML;'
            txt_html = self.browser.execute_script(js)
            #print('start_times_html---', txt_html)
            start_times = re.findall('<a\s+href="javascript:void\(0\)"\s+value="(\d+)">(.*?)</a>', txt_html, re.I | re.M | re.S)
            #print('start_times---', start_times)
            start_time_selected = None
            for start_time in start_times:
                if start_time[1] == self.start_time:
                    start_time_selected = start_time
                    break
            if start_time_selected == None:
                logger.info('{}，{}，没有指定的开始时间：{}'.format(wechat['name'], self.date_appointment, self.start_time))
                return False
            js = 'var obj = document.getElementById("display_startMin");obj.setAttribute("value", "{}");obj.innerHTML="{}";'.format(start_time_selected[0], start_time_selected[1])
            self.browser.execute_script(js)
            self.browser.execute_script('document.getElementById("startMin").setAttribute("value", "{}")'.format(start_time_selected[0]))
            #time.sleep(1)
            #ele_click.click()
            #time.sleep(3)

            # 选择结束时间
            #ele_click = self.browser.find_element(By.ID, 'endMin_select')
            #ele_click.click()
            #time.sleep(1)
            js = 'var obj=document.getElementById("options_endMin");return obj.innerHTML;'
            txt_html = self.browser.execute_script(js)
            #print('end_times_html---', txt_html)
            end_times = re.findall('<a\s+href="javascript:void\(0\)"\s+value="(\d+)">(.*?)</a>', txt_html, re.I | re.M | re.S)
            #print('end_times---', end_times)
            end_time_selected = None
            for end_time in end_times:
                if end_time[1] == self.end_time:
                    end_time_selected = end_time
                    break
            if end_time_selected == None:
                logger.info('{}，{}，没有指定的结束时间：{}'.format(wechat['name'], self.date_appointment, self.end_time))
                return False
            js = 'var obj = document.getElementById("display_endMin");obj.setAttribute("value", "{}");obj.innerHTML="{}";'.format(end_time_selected[0], end_time_selected[1])
            self.browser.execute_script(js)
            self.browser.execute_script('document.getElementById("endMin").setAttribute("value", "{}")'.format(end_time_selected[0]))
            time.sleep(1)
            #ele_click.click()
            #time.sleep(3)

            # 获取房间列表
            # ele = self.browser.find_element(By.ID, 'options_room')
            # txt_html = ele.text
            js = 'var obj=document.getElementById("options_room");return obj.innerHTML;'
            txt_html = self.browser.execute_script(js)
            # print('rooms_html---', txt_html)
            rooms = re.findall('<a\s+href="javascript:void\(0\)"\s+value="(\d+)">(.*?)</a>', txt_html, re.I | re.M | re.S)
            #print('rooms---', rooms)
            rooms_reserve = []
            for room in rooms:
                if room[1].find('第五') >= 0 or room[1].find('第六') >= 0 or room[1].find('第七') >= 0 or room[1].find('第八') >= 0:
                    rooms_reserve.append(room)
            if len(rooms_reserve) <= 0:
                logger.info('{}，{}，没有查到房间'.format(wechat['name'], self.date_appointment))
                return False
            logger.info('{}，{}，待预约房间：{}'.format(wechat['name'], self.date_appointment, rooms_reserve))
            return rooms_reserve
        except Exception as e:
            time_curr = int(time.time())
            with open(f"./html/reserveSeat{time_curr}.html", 'w', encoding='utf-8') as file_html:
                file_html.write(self.browser.page_source)
            self.browser.save_screenshot(f"./pic_error/reserveSeat{time_curr}.png")
            logger.info('获取房间列表异常，报错信息：{}'.format(e))
            logger.error('获取房间列表异常，报错信息：', e)
            return False

    '''预约座位'''
    def reserveSeat(self, room):
        wechat = self.wechat
        try:
            # 选择房间
            #ele_click = self.browser.find_element(By.ID, 'room_select')
            #ActionChains(self.browser).move_to_element(ele_click).perform()
            #time.sleep(1)
            #ele_click.click()
            #time.sleep(1)
            js = 'var obj = document.getElementById("display_room");obj.setAttribute("value", "{}");obj.innerHTML="{}";'.format(
                room[0], room[1])
            self.browser.execute_script(js)
            self.browser.execute_script('document.getElementById("room").setAttribute("value", "{}")'.format(room[0]))
            #time.sleep(1)
            #ele_click.click()
            #time.sleep(3)

            # 查询座位
            ele = self.browser.find_element(By.ID, 'searchBtn')
            ActionChains(self.browser).move_to_element(ele).perform()
            #time.sleep(1)
            ele.click()
            #time.sleep(5)

            # 选择座位（并判断座位是否加载出来）
            # ele = self.browser.find_element(By.ID, 'seats')
            # txt_html = ele.text
            time_curr = time.time()
            time_end = time_curr + 5
            has_seats = False
            while time_curr < time_end:
                items = self.browser.find_elements(By.CLASS_NAME, 'item')
                if len(items) > 1:
                    has_seats = True
                    break
                time_curr = time.time()
            if not has_seats:
                logger.info('{}，{}，{}，没有座位'.format(wechat['name'], self.date_appointment, room[1]))
                return False
            js = 'var obj=document.getElementById("seats");return obj.innerHTML;'
            txt_html = self.browser.execute_script(js)
            #print('seats_html----', txt_html)
            # seat_ids = re.findall('<li\s+class="using"\s+id="seat_(\d+)"\s+title="座位空闲">.*?</li>', txt_html, re.I | re.M | re.S)
            seats = re.findall('<li\s+class="free"\s+id="seat_(\d+)"\s+title="座位空闲">.*?<dt>(\d+)</dt>.*?</li>', txt_html, re.I | re.M | re.S)
            #print(seats)
            if len(seats) <= 0:
                logger.info('{}，{}，{}，没有空闲座位'.format(wechat['name'], self.date_appointment, room[1]))
                return False
            logger.info('{}，{}，{}，待预约座位：{}'.format(wechat['name'], self.date_appointment, room[1], seats))
            logger.info('{}，{}，指定的座位 {}'.format(wechat['name'], self.date_appointment, self.wechat['seat_nos']))
            # 随机排序可约座位，降低多账号约同一个座位
            random.shuffle(seats)
            for seat in seats:
                # 过滤未指定的座位号
                if self.wechat['seat_nos'] != '' and (seat[1] not in self.wechat['seat_nos'].split(',')):
                    continue
                logger.info('{}，{}，{}，准备预定座位 {}'.format(wechat['name'], self.date_appointment, room[1], seat[1]))
                # 点选座位
                ele = self.browser.find_element(By.ID, 'seat_' + seat[0])
                ActionChains(self.browser).move_to_element(ele).perform()
                #time.sleep(1)
                ele.click()
                #time.sleep(5)

                # 选择时间窗口是否出现
                wait = WebDriverWait(self.browser, 10)
                wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'seatTime')))

                # 选择开始时间 08:00
                # ele = self.browser.find_element(By.ID, 'startTime')
                # txt_html = ele.text
                js = 'var obj=document.getElementById("startTime");return obj.innerHTML;'
                txt_html = self.browser.execute_script(js)
                # res = re.findall('<a\s+href="#"\s+time="\d+">08:00</a>', txt_html, re.I | re.M | re.S)
                #list_startTime = re.findall(f'<a\s+href="#"\s+time="\d+">{self.start_time}</a>', txt_html, re.I | re.M | re.S)
                list_startTime = re.findall('<a\s+href="#"\s+time="\d+">(.*?)</a>', txt_html, re.I | re.M | re.S)
                if len(list_startTime) <= 0:
                    logger.info('{}，{}，{}，没有开始时间 {}'.format(wechat['name'], self.date_appointment, room[1], self.start_time))
                    # 取消时间选择窗口
                    ele = self.browser.find_element(By.XPATH, '//*[@id="reservationAction"]/a[2]')
                    ActionChains(self.browser).move_to_element(ele).perform()
                    #time.sleep(1)
                    ele.click()
                    #time.sleep(3)
                    continue
                # //*[@id="startTime"]/dl/ul/li[2]/a
                # ele = self.browser.find_element(By.XPATH, '//*[@id="startTime"]/dl/ul/li[2]/a')
                # 获取指定开始时间在模块元素中的位置
                pos_startTime = 0
                for i, start_time in enumerate(list_startTime):
                    if start_time == self.start_time:
                        pos_startTime = i + 1
                if pos_startTime == 0:
                    logger.info('{}，{}，{}，没有开始时间 {}'.format(wechat['name'], self.date_appointment, room[1], self.start_time))
                    # 取消时间选择窗口
                    ele = self.browser.find_element(By.XPATH, '//*[@id="reservationAction"]/a[2]')
                    ActionChains(self.browser).move_to_element(ele).perform()
                    #time.sleep(1)
                    ele.click()
                    #time.sleep(3)
                    continue
                if pos_startTime == 1:
                    ele = self.browser.find_element(By.XPATH, '//*[@id="startTime"]/dl/ul/li/a')
                else:
                    ele = self.browser.find_element(By.XPATH, f'//*[@id="startTime"]/dl/ul/li[{pos_startTime}]/a')
                ActionChains(self.browser).move_to_element(ele).perform()
                #time.sleep(1)
                ele.click()
                #time.sleep(5)

                # 选择结束时间 22:00
                # 等待结束时间加载出来
                wait = WebDriverWait(self.browser, 10)
                wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[@id="endTimeCotent"]/li')))
                # ele = self.browser.find_element(By.ID, 'endTime')
                # txt_html = ele.text
                js = 'var obj=document.getElementById("endTime");return obj.innerHTML;'
                txt_html = self.browser.execute_script(js)
                # res = re.findall('<a\s+href="#"\s+time="\d+">22:00</a>', txt_html, re.I | re.M | re.S)
                # res = re.findall(f'<a\s+href="#"\s+time="\d+">{self.end_time}</a>', txt_html, re.I | re.M | re.S)
                list_endTime = re.findall('<a\s+href="#"\s+time="\d+">(.*?)</a>', txt_html, re.I | re.M | re.S)
                if len(list_endTime) <= 0:
                    logger.info('{}，{}，{}，没有结束时间 {}'.format(wechat['name'], self.date_appointment, room[1], self.end_time))
                    # 取消时间选择窗口
                    ele = self.browser.find_element(By.XPATH, '//*[@id="reservationAction"]/a[2]')
                    ActionChains(self.browser).move_to_element(ele).perform()
                    #time.sleep(1)
                    ele.click()
                    #time.sleep(3)
                    continue
                # 获取指定结束时间在模块元素中的位置
                pos_endTime = 0
                for i, end_time in enumerate(list_endTime):
                    if end_time == self.end_time:
                        pos_endTime = i + 1
                if pos_endTime == 0:
                    logger.info('{}，{}，{}，没有结束时间 {}'.format(wechat['name'], self.date_appointment, room[1], self.end_time))
                    # 取消时间选择窗口
                    ele = self.browser.find_element(By.XPATH, '//*[@id="reservationAction"]/a[2]')
                    ActionChains(self.browser).move_to_element(ele).perform()
                    #time.sleep(1)
                    ele.click()
                    #time.sleep(3)
                    continue
                if pos_endTime == 1:
                    ele = self.browser.find_element(By.XPATH, '//*[@id="endTime"]/dl/ul/li/a')
                else:
                    ele = self.browser.find_element(By.XPATH, f'//*[@id="endTime"]/dl/ul/li[{pos_endTime}]/a')
                ActionChains(self.browser).move_to_element(ele).perform()
                #time.sleep(1)
                ele.click()
                #time.sleep(5)

                # 验证 //*[@id="reservationCaptcha"]/div/input
                # 截图预约页面，截取图片验证码，点选验证
                verify_code = False
                for i in range(1):
                    obj_verify = SeatVerification(self.browser)
                    verify_code = obj_verify.runSubmit()
                    if bool(verify_code):
                        break
                if not bool(verify_code):
                    continue
                #time.sleep(5)
                logger.info('{}，{} {}，{} {}-{}，准备发起预约'.format(wechat['name'], room[1], seat[1], self.date_appointment,
                                                            self.start_time, self.end_time))
                # 发起预约
                ele = self.browser.find_element(By.ID, 'reserveBtn')
                ActionChains(self.browser).move_to_element(ele).perform()
                #time.sleep(1)
                ele.click()
                #time.sleep(5)
                # 选择时间窗口是否隐藏
                wait = WebDriverWait(self.browser, 10)
                wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, 'seatTime')))

                if self.browser.page_source.find('系统已经为您预定好了') > 0:
                    # alert_sound() # 语音提醒
                    logger.info('{}，{} {}，{} {}-{}，预约成功'.format(wechat['name'], room[1], seat[1], self.date_appointment, self.start_time, self.end_time))
                    send_wechat('预约成功，校园图书馆座位', wechat['name'], self.date_appointment + ' ' + self.start_time + '-' + self.end_time, room[1] + ' ' + seat[1])
                    return True
                else:
                    logger.info('{}，{} {}，{} {}-{}，预约失败'.format(wechat['name'], room[1], seat[1], self.date_appointment, self.start_time, self.end_time))
                    if self.browser.page_source.find('预约失败') > 0:
                        # /html/body/div[3]/div[2]/ul/li[1]/a
                        # /html/body/div[4]/div[1]/ul/li[1]/a
                        # 跳转自选座位
                        ele = self.browser.find_element(By.XPATH, '/html/body/div[3]/div[2]/ul/li[1]/a')
                        ActionChains(self.browser).move_to_element(ele).perform()
                        #time.sleep(1)
                        ele.click()
                        time.sleep(1)
                    # 重新初始化查询条件
                    self.listRoom()
                    break  # 跳出座位选择
            return False
        except Exception as e:
            time_curr = int(time.time())
            with open(f"./html/reserveSeat{time_curr}.html", 'w', encoding='utf-8') as file_html:
                file_html.write(self.browser.page_source)
            self.browser.save_screenshot(f"./pic_error/reserveSeat{time_curr}.png")
            logger.info('预约座位异常，报错信息：{}'.format(e))
            logger.error('预约座位异常，报错信息：', e)
            return False

    def doLogin(self):
        wechat = self.wechat

        res_login = self.login(wechat['cert_no'], wechat['pwd'])
        if not bool(res_login):
            return False #登录失败
        # 登录成功后，设置cookie
        for cookies_update in self.list_cookies:
            self.session.cookies.set(cookies_update['name'], cookies_update['value'])
        return True

    def run(self):
        wechat = self.wechat
        logger.info('发起预约的账号信息：{}，使用代理IP：{}，使用请求头：{}'.format(wechat, self.proxies, self.user_agent))

        # 登录
        res = self.doLogin()
        if not bool(res):
            return
        #print('登录成功')
        #return

        # 执行N秒结束
        start_time = time.time()
        end_time = start_time + self.seconds_execute
        while start_time < end_time:
            start_time = time.time()

            if start_time < self.time_execute:
                #logger.info('执行时间未到：{}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.time_execute))))
                time.sleep(1)
                continue
            # 刷新下页面
            self.browser.refresh()

            wait = WebDriverWait(self.browser, 10)
            # 查询按钮
            wait.until(EC.presence_of_element_located((By.ID, 'searchBtn')))

            # 获取西校区房间列表
            rooms_reserve = self.listRoom()
            if not bool(rooms_reserve):
                continue
            rooms_reserve.reverse()

            is_reserve = False
            for i, room in enumerate(rooms_reserve):
                logger.info('{}，{}，{}，准备预定该房间座位'.format(wechat['name'], self.date_appointment, room[1]))

                # 选择房间、查询座位、选择座位
                res = self.reserveSeat(room)
                if bool(res):
                    is_reserve = True
                    break   # 跳出房间选择

                #if is_reserve:
                #    break  # 跳出房间选择
            if is_reserve:
                break  # 跳出执行时间
            #time.sleep(1)
        logger.info('{}，等待2分钟后结束'.format(wechat['name']))
        time.sleep(120)


def main():
    wechats = ACCOUNTS

    dict_proxies = [
        {'http': ''},
        {'http': ''},
        {'http': ''},
        {'http': ''},
        #{'http': 'http://112.74.202.247:16818/', 'https': 'http://112.74.202.247:16818/'},
        #{'http': 'http://112.74.108.33:16818/', 'https': 'http://112.74.108.33:16818/'},
    ]


    day_curr = datetime.now()
    date_curr = day_curr.strftime("%Y-%m-%d")
    # 执行时间
    time_execute = time.mktime(time.strptime(f'{date_curr} 07:00:00', "%Y-%m-%d %H:%M:%S"))
    # 执行N秒结束
    seconds_execute = 600
    # 预约日期
    tomorrow = day_curr + timedelta(1)
    date_appointment = tomorrow.strftime("%Y-%m-%d")
    start_time = '08:00'
    end_time = '22:00'
    # 周二约半天
    if day_curr.isoweekday() == 1:
        end_time = '12:00'
    #end_time = '12:00'

    # 保存线程
    Thread_list = []
    for i, wechat in enumerate(wechats):
        '''发起多线程'''
        p = GrabNumber(wechat, date_appointment, start_time, end_time, seconds_execute, time_execute, USER_AGENTS[i], dict_proxies[0])
        p.start()
        Thread_list.append(p)

    while Thread_list:
        for i in Thread_list:
            if not i.is_alive():
                Thread_list.remove(i)

    logger.info('自动预约处理完成')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

