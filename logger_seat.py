import logging
import logging.handlers
import time

'''
日志模块
'''
#LOG_FILENAME = 'robots.log'
date_curr = time.strftime("%Y%m%d", time.localtime())
LOG_FILENAME = './log/seat{}.log'.format(date_curr)
logger = logging.getLogger()

def set_logger():
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(process)d-%(threadName)s - '
                                  '%(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    file_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=512000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

set_logger()