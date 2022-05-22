# UJNLib
UJN图书馆座位自动预约

# 语言
python

# 使用方法
1.下载chrome driver对应版本的浏览器  
2.注册超级鹰账号 https://www.chaojiying.com/ 获取软件ID（这里也可以选择别的打码平台）  
3.在config.py内填写学号密码姓名座位号等信息  
4.在main.py中更改想要预约的阅览室和预约时间  
5.写一个crontab，每天定时提前两三分钟执行main.py（会有一个预登陆）    
