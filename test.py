#!/usr/bin/python3
#coding:utf-8


from selenium import webdriver


ch_options = webdriver.ChromeOptions()

#为Chrome配置无头模式
ch_options.add_argument("--headless")  
ch_options.add_argument('--no-sandbox')
ch_options.add_argument('--disable-gpu')
ch_options.add_argument('--disable-dev-shm-usage')
# 在启动浏览器时加入配置
dr = webdriver.Chrome(options=ch_options)
#这是测试网站
url = "https://www.baidu.com"
dr.get(url)
#打印源码
print(dr.page_source)
