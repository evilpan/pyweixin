# -*- encoding=utf-8 -*-
import requests
import logging
import json
import time
import random
from lxml import etree
class Robot(object):
    '''
    NLP Robot using different vendors
    Including Sim,Xiaoi,Tuling...
    Usage example:
        from pyweixin.robot import Robot
        bot = Robot()
        reply = bot.askSim('hello')
    '''

    def __init__(this):
        this.robotList = [this.askSim, this.askXiaoi, this.askTuling]
        random.seed(time.time())
        
    def askRandom(this, question):
        which = random.randint(0, len(this.robotList) - 1)
        return this.robotList[which](question)

    def askTuling(this, question):
        url = 'http://www.tuling123.com/api/product_exper/chat.jhtml'
        answer = ''
        post_data = {}
        post_data['info'] = question
        try:
            res = requests.post(url, data=post_data)
            if res.status_code == 200:
                xmlres = res.content
                root = etree.fromstring(xmlres)
                answer = root.find('Content').text
        except Exception as e:
            answer = 'Error:' + str(e)
        return answer
    
    def askXiaoi(this, question):
        if (len(question) > 30):
            question = question[:30]
        url = 'http://dev.cluster.xiaoi.com/robot/app/smarttoy/ask.action?platform=jinrong&userId=test&format=json&question=' + question
        answer = ''
        try:
            res = requests.get(url)
            jstr = res.content
            jdict = json.loads(jstr)
            answer = jdict['content']
        except Exception as e:
            answer = 'Error:' + str(e)
        return answer
    
    def askSim(this, question):
        uuid = 'S1kHkOMSuLP5i7nlqvpqupzYfcb2'
        lc = 'ch'
        url = 'http://simsimi.com/getRealtimeReq?uuid={0}&lc={1}&ft=1&reqText={2}'.format(uuid, lc, question)
        answer = ''
        try:
            res = requests.get(url)
            if(res.status_code == 200):
                jdict = res.json()
                if jdict['status'] == 200:
                    answer = jdict['respSentence']
        except Exception as e:
            answer = 'Error:' + str(e)
        return answer
    
if __name__ == '__main__':
    r = Robot()
    try:
        while True:
            question = raw_input('>>')
            if(len(question) > 0):
                logging.info(r.askRandom(question))
    except KeyboardInterrupt:
        logging.info('\nQuiting...')
        exit()
