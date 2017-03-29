#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from pyweixin.robot import Robot
from pyweixin.client import MessageHandler,WxClient,isGroupId

class MyHandler(MessageHandler):
    def __init__(self):
        self.bot = Robot()
        self.autoreply = False
    def set_autoreply(self, enable):
        self.autoreply = enable

    def on_message(self, client, message):
        fromwxid = message['FromUserName'].encode('utf-8')
        towxid = message['ToUserName'].encode('utf-8')
        fromname = client.id2name(fromwxid)
        #toname = client.id2name(towxid)
        toname = 'ME'
        text = message['Content'].encode('latin1').replace('&lt;', '<').replace('&gt;', '>')
        mtype = message['MsgType']
        groupuser = ''
        if isGroupId(fromwxid):
            try:
                [groupuser, text] = text.split(':<br/>', 1)
                groupuser = client.id2name(groupuser)
            except Exception as e:
                if mtype == 10000:
                    mtype = 1
                else:
                    print '[x] text:' + text 
                    print '[x] except:' + str(e) 

        print '[+] [{} -> {}]{}:'.format(fromname, toname, groupuser),
        if mtype == 1:
            print('<Text Message>:' + text)
        elif mtype == 3:
            print('<Image Message>')
        elif mtype == 34:
            print('<Audio Message>')
        elif mtype == 42:
            print('<Name Card>')
        elif mtype == 43:
            print('<Video Message>')
        elif mtype == 47:
            print('<Sticker>')
        elif mtype == 49:
            print('<Share Link>')
        elif mtype == 51:
            print('<Update Contact>')
        elif mtype == 10000:
            print('<Luckey Money>')
        elif mtype == 10002:
            print('<Recalled A Message>')
        else:
            print('<Unknown Type:{}>'.format(mtype))

        if self.autoreply:
            if mtype == 1:
                reply = self.bot.askRandom(text)
                print '[+] autoreply: ' + reply
                client.webwxsendmsg(fromwxid, reply)
    def on_event(self, client, event):
        print '[+] <event>:' + event



if __name__ == '__main__':
    handler = MyHandler()
    wxclient = WxClient(handler)
    wxclient.start_background()
    while True:
        cmd = raw_input('CMD:')
        if cmd == 'auto on':
            # 开启自动回复
            handler.set_autoreply(True)
        elif cmd == 'auto off':
            # 关闭自动回复
            handler.set_autoreply(False)
        elif cmd == 'quit' or cmd == 'exit':
            wxclient.webwxlogout()
            break
        else:
            pass
