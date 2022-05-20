# !/usr/bin/env python
# -*- coding:utf-8 -*-

'''
outlook点选验证
'''

from chaojiying import Chaojiying_Client
import random
import time
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as serviceChrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

from config import ACCOUNT_CHAOJIYING
from logger_seat import logger

#CHAOJIYING_KIND = 9101  # 验证码类型，坐标选一,返回格式:x,y
CHAOJIYING_KIND = 9004  # 验证码类型，坐标多选,返回1~4个坐标,如:x1,y1|x2,y2|x3,y3


class SeatVerification(object):

    def __init__(self, driver):
        self.driver  = driver

        self.chaojiying = Chaojiying_Client(ACCOUNT_CHAOJIYING['user_name'], ACCOUNT_CHAOJIYING['password'], ACCOUNT_CHAOJIYING['soft_id'])
        #iframe元素对象
        self.ele_iframe = None

    '''检查元素是否存在'''
    def checkElementExists(self, driver, element, condition):
        try:
            if condition == 'class':
                driver.find_element_by_class_name(element)
            elif condition == 'id':
                driver.find_element_by_id(element)
            elif condition == 'xpath':
                driver.find_element_by_xpath(element)
            return True
        except Exception as e:
            return False

    '''1、获取验证码图片（剪切）'''
    def getImageShear(self):
        try:
            self.ele_iframe = self.driver.find_element(By.ID, 'layui-layer1')
            logger.info('layui-layer1 元素的坐标：{}'.format(self.ele_iframe.location))
            # 验证码区域大小，宽 360px，高 230px
            start_x = self.ele_iframe.location['x']
            start_y = self.ele_iframe.location['y']
            end_x = self.ele_iframe.location['x'] + 360
            end_y = self.ele_iframe.location['y'] + 230
            axis = (start_x, start_y, end_x, end_y)
            logger.info('layui-layer1 元素下，点选图片坐标：{}'.format(axis))

            time_curr = int(time.time())
            # 网页截屏
            self.driver.save_screenshot(f"./captcha/{time_curr}printscreen_click.png")
            time.sleep(0.5)
            im = Image.open(f"./captcha/{time_curr}printscreen_click.png")
            new_image = im.crop(axis)

            # 注册验证页面，点选验证码图片
            png_click = f"./captcha/{time_curr}click.png"
            new_image.save(png_click)
            return new_image
        except Exception as e:
            logger.info('获取点选验证码图片（剪切）异常，报错信息：{}'.format(e))
            logger.error('获取点选验证码图片（剪切）异常，报错信息：', e)
            return False

    '''2、上传图片到打码平台，上传图片(Byte)，返回点击的坐标。这里对返回的坐标进行了处理'''
    def uploadPicture(self, img):
        image = img
        byte_array = BytesIO()
        image.save(byte_array, format('PNG'))
        # 提交图片
        result = self.chaojiying.PostPic(byte_array.getvalue(), CHAOJIYING_KIND)
        if result['err_no'] != 0:
            logger.info('获取验证码失败：{}'.format(result))
            raise ValueError

        pic_str = result['pic_str']
        pic_list = [[i for i in x.split(',')] for x in pic_str.split('|')]
        logger.info('点选图片中的目标坐标：{}'.format(pic_list))
        return pic_list

    '''
    # 1、获取点选验证码图片
    # 2、上传图片到打码平台
    # 3、根据坐标点选验证码
    # 4、提交订单
    '''
    def revalidation(self):
        try:
            new_image = self.getImageShear()
            click_coordinates = self.uploadPicture(new_image)
            if len(click_coordinates) >= 2:
                xoffset = int(click_coordinates[0][0])
                yoffset = int(click_coordinates[0][1])
                xoffset2 = int(click_coordinates[1][0])
                yoffset2 = int(click_coordinates[1][1])
            else:
                return {'status': 0, 'msg': '继续点选验证'}
            logger.info('在 layui-layer1 元素下，点击坐标：{}, {}'.format(xoffset, yoffset))

            ActionChains(self.driver).move_to_element_with_offset(self.ele_iframe, xoffset, yoffset).perform()
            #time.sleep(1)
            ActionChains(self.driver).click().perform()
            time.sleep(random.uniform(1,3))
            ActionChains(self.driver).move_to_element_with_offset(self.ele_iframe, xoffset2, yoffset2).perform()
            #time.sleep(1)
            ActionChains(self.driver).click().perform()
            #time.sleep(5)

            #is_exsit = self.checkElementExists(self.driver, 'layui-layer1', 'id')
            #if is_exsit:
            #    logger.info('元素 layui-layer1 存在，点选图片验证未通过或多图片验证')
            #    return {'status': 0, 'msg': '继续点选验证'}
            #return {'status': 1, 'msg': '点选验证通过'}

            # <input type="button" class="verifyCode" onclick="clickVerifyCode('')" value="请点此进行验证">
            # <input type="button" class="verifyCode verifySucc" onclick="clickVerifyCode('')" value="验证通过" disabled="disabled">
            time_curr = time.time()
            time_end = time_curr + 5
            while time_curr < time_end:
                ele = self.driver.find_element(By.CLASS_NAME, 'verifyCode')
                if ele.get_attribute('value') == '验证通过':
                    return {'status': 1, 'msg': '点选验证通过'}
                time_curr = time.time()

            return {'status': 0, 'msg': '继续点选验证'}
        except WebDriverException as e:
            logger.info('操作点选验证码异常，报错信息：{}'.format(e))
        except Exception as e:
            logger.info('操作点选验证码异常，报错信息：{}'.format(e))
            logger.error('操作点选验证码异常，报错信息：', e)

        return {'status': -1, 'msg': '点选验证出现异常'}

    def run(self):
        logger.info('点选验证码验证启动')
        wait = WebDriverWait(self.driver, 10)
        # 登录按钮
        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="login"]/dd[4]/input')))
        time.sleep(3)
        # 获取验证码
        ele = self.driver.find_element(By.XPATH, '//*[@id="login"]/dd[3]/input')
        ActionChains(self.driver).move_to_element(ele).perform()
        time.sleep(1)
        ele.click()
        time.sleep(5)
        #wait.until(EC.visibility_of_element_located((By.ID, 'layui-layer-iframe1')))

        for i in range(5):
            res = self.revalidation()
            logger.info('点选验证码第 {} 次，验证结果：{}'.format(i, res))
            time.sleep(2)
            if res['status'] == 1:
                return True
            elif res['status'] == 0:
                continue #继续点选验证
            else:
                #self.driver.quit()
                time.sleep(random.uniform(1, 5))
                return False

    def runSubmit(self):
        logger.info('点选验证码验证启动')
        # 获取验证码
        ele = self.driver.find_element(By.XPATH, '//*[@id="reservationCaptcha"]/div/input')
        ele.click()
        time.sleep(5)

        for i in range(5):
            res = self.revalidation()
            logger.info('点选验证码第 {} 次，验证结果：{}'.format(i, res))
            #time.sleep(2)
            if res['status'] == 1:
                return True
            elif res['status'] == 0:
                continue #继续点选验证
            else:
                #self.driver.quit()
                time.sleep(random.uniform(1, 5))
                return False


def main():
    url = 'http://seat.ujn.edu.cn/'

    s = serviceChrome("./webdriver/chrome_win32_99.0.4844.51/chromedriver.exe")
    options = webdriver.ChromeOptions()
    # 设置反屏蔽
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=s, options=options)
    driver.get(url)
    #driver.maximize_window()
    driver.set_window_size(970, 800)

    #obj = SeatVerification(driver)
    #obj.run()

    #img = Image.open('./captcha/微信截图_20220407013414.png')
    #obj.uploadPicture(img)
    #js = 'var obj = document.getElementsByClassName("logo");obj[0].setAttribute("value", "{}");obj[0].innerHTML="{}";'.format('2022-04-24', '2022-04-24')
    #driver.execute_script(js)
    js = 'var obj=document.getElementById("login");return obj.innerHTML;'
    res = driver.execute_script(js)
    print(res)

    time.sleep(30)


if __name__ == '__main__':
    main()