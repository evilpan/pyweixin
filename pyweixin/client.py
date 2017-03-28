#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import json
import random
import logging
import requests
import threading
import qrcode
from lxml import etree


logging.basicConfig()
SPECIAL_USERS = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail', 'tmessage',
                 'qmessage', 'qqsync', 'floatbottle', 'lbsapp', 'shakeapp', 'medianote',
                 'qqfriend', 'readerapp', 'blogapp', 'facebookapp', 'masssendapp', 'meishiapp',
                 'feedsapp', 'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
                 'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'officialaccounts', 
                 'wxitil', 'userexperience_alarm', 'notification_messages']
def timestamp():
    return int(time.time() * 10**6)
def isGroupId(wxid):
    return wxid[:2] == '@@' and (len(wxid) - 2) % 32 == 0
def isContactId(wxid):
    return wxid[0] == '@' and (len(wxid) - 1) % 32 == 0

class MessageHandler(object):
    def on_login(self, client):
        print('[+] Initialize done. '
        '{} special accounts, '
        '{} official accounts, '
        '{} groups, '
        '{} persons.'.format(len(client.special_accounts),
            len(client.official_accounts),
            len(client.groups),
            len(client.contacts)))
    def on_logout(self, client):
        print '[+] User logout'

    def on_event(self, client, event):
        print '[+] <event>:' + event
    def on_message(self, client, message):
        pass


class WxClient(object):
    def __init__(self, handler=MessageHandler(), loglevel=logging.INFO):
        self.logger = logging.getLogger('WxClient')
        self.logger.setLevel(loglevel)
        self.handler = handler

        self.uri = ''
        self.base = ''
        self.skey = ''
        self.sid = ''
        self.uin = ''
        self.pass_ticket = ''
        self.deviceid = 'e' + ''.join([str(random.randint(0,9)) for i in range(15)])
        self.jsonsynckeys = []
        self.session = requests.Session()

        self.special_accounts = []
        self.official_accounts = []
        self.contacts = []
        self.groups = []

    def start_background(self):
        uuid = self.get_uuid()
        code = self.get_qrcode(uuid)
        self.show_qrcode(code)
        print '[+] Please Scan ...'
        self.wait_scan(uuid)
        print '[+] Please Comfirm ...'
        self.wait_comfirm(uuid)

        print '[+] Initializing ...'
        self.webwxlogin()
        self.webwxinit()
        self.webwxgetcontact()
        #self.webwxbatchgetcontact()
        loopthread = threading.Thread(target=self.syncloop)
        loopthread.daemon = True
        loopthread.start()

    def syncloop(self):
        running = True
        while running:
            (retcode, selector) = self.syncheck()
            if retcode == '0':
                if selector == '0':
                    self.handler.on_event(self, 'SYN_CHECK')
                    continue
                else:
                    self.handler.on_event(self, 'SYN_UPDATE')
                    self.webwxsync()
            elif retcode == '1101':
                self.handler.on_logout(self)
                running = False
            else :
                self.handler.on_event(self, 'SYN_ERROR {}'.format(retcode))
                running = False

    def get_uuid(self):
        uuid = ''
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
                    'appid':'wx782c26e4c19acffb',
                    'fun':'new',
                    'lang':'en_US',
                    '_': timestamp() 
                 }
        response = self.session.post(url, data=params)
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        match = re.search(regx, response.content)
        if match and match.group(1) == '200':
            uuid = match.group(2)
            self.logger.debug('Get uuid:' + uuid)
        else:
            self.logger.warn('Fail to get uuid, response:\n' + response.text)
        return uuid

    def get_qrcode(self, uuid):
        data = 'https://login.weixin.qq.com/l/' + uuid
        code = qrcode.QRCode(
            version=1,#Range from 1 to 40, controls the size of qr code, 1 = smallest = 21x21 matrix
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        code.add_data(data)
        return code
    def show_qrcode(self, code):
        if sys.platform.startswith('win'):
            img = code.make_image()
            imgpath = 'login.png';
            with open(imgpath, 'wb') as f:
                img.save(f, kind='PNG')
            os.startfile(imgpath)
        else:
            mat = code.get_matrix()
            for i in mat:
                BLACK = '\033[40m  \033[0m'
                WHITE = '\033[47m  \033[0m'
                print ''.join([BLACK if j else WHITE for j in i])

    def wait_scan(self, uuid):
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip={}&uuid={}&_={}'.format(
                1, uuid, timestamp() )
        response = self.session.get(url)
        match = re.search(r'window.code=(\d+);', response.content)
        status = False
        if match :
            code = match.group(1)
            self.logger.debug('Scan response:' + response.content)
            if '201' == code:
                self.handler.on_event(self, 'SCAN_SUCCESS')
                status = True
            elif '408' == code:
                self.handler.on_event(self, 'SCAN_TIMEOUT')
            else:
                self.handler.on_event(self, 'SCAN_ERROR')
        return status
    def wait_comfirm(self, uuid):
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip={}&uuid={}&_={}'.format(
                0, uuid, timestamp() )
        response = self.session.get(url)
        match = re.search(r'window.code=(\d+);', response.content)
        status = False
        if match :
            code = match.group(1)
            self.logger.debug('Comfirm response:' + response.content)
            if '200' == code:
                self.handler.on_event(self, 'COMFIRM_SUCCESS')
                status = self.init_url(response.text)
            elif '408' == code:
                self.handler.on_event(self, 'COMFIRM_TIMEOUT')
            else:
                self.handler.on_event(self, 'COMFIRM_ERROR')
        return status

    def init_url(self, text):
        match = re.search(r'window.redirect_uri="(\S+?)";', text)
        status = False
        if match :
            self.uri = match.group(1)
            self.base = self.uri[:self.uri.rfind('/')]
            self.logger.debug('Comfirmed, base={}'.format(self.base))
            self.logger.debug('Comfirmed, uri={}'.format(self.uri))
            status = True
        return status
    
    def webwxlogin(self):
        success = True
        url = self.uri + '&fun=new&version=v2'
        response = self.session.get(url)
        if(response.status_code == 200):
            self.logger.debug('login response:' + response.text)
            root = etree.fromstring(response.text)
            for node in root:
                if node.tag == 'skey':
                    self.skey = node.text
                elif node.tag == 'wxsid':
                    self.sid = node.text
                elif node.tag == 'wxuin':
                    self.uin = node.text
                elif node.tag == 'pass_ticket':
                    self.pass_ticket = node.text
                else:
                    pass
            if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
                success = False
        else:
            success = False
            self.logger.warn('webwxlogin error:{}'.format(response.status_code))
        return success

    def update_contacts(self, clist):
        for contact in clist:
            uid = contact['UserName']
            nick = contact['NickName']
            remark = contact['RemarkName']
            numMembers = contact['MemberCount']
            vflag = contact['VerifyFlag'] 
            if uid[0:2] == '@@' and numMembers > 0:
                self._update(self.groups, contact)
            elif uid[0] != '@':
                self._update(self.special_accounts, contact)
            elif vflag != 0 and vflag % 8 == 0:
                self._update(self.official_accounts, contact)
            else:
                self._update(self.contacts, contact)

    def _update(self, cachedlist, element):
        incache = False
        for i in xrange(0,len(cachedlist)):
            if cachedlist[i]['UserName'] == element['UserName']:
                cachedlist[i] = element
                incache = True
                break
        if not incache:
            cachedlist.append(element)

    def webwxinit(self):
        url = self.base + '/webwxinit?r={}&pass_ticket={}'.format(
               timestamp(), self.pass_ticket )
        params = { 
                    'BaseRequest': self._getBaseRequest()
                }
        self.logger.debug('webwxinit request:' + url)
        self.logger.debug('webwxinit params:' + str(params))
        response = self.session.post(url, json=params)
        if(response.status_code == 200):
            if self.logger.getEffectiveLevel() <= logging.DEBUG:
                dumpfile = 'webwxinit.json'
                with open(dumpfile, 'w') as f:
                    f.write(response.content)
                self.logger.debug('saving webwxinit response to ' + dumpfile)
            rjson = response.json()
            self.jsonsynckeys = rjson['SyncKey']
            self.update_contacts(rjson['ContactList'])
            self.myid = rjson['User']['UserName'].encode('utf-8')
            self.logger.debug('synckeys:' + self._getSyncKeyStr())
            
        else:
            self.logger.warn('webwxinit error:{}'.format(response.status_code))

    def webwxgetcontact(self):
        url = self.base + '/webwxgetcontact?lang=en_US&r={}&pass_ticket={}&skey={}'.format(
                timestamp(), self.pass_ticket, self.skey)
        response = self.session.get(url)
        if(response.status_code == 200):
            if self.logger.getEffectiveLevel() <= logging.DEBUG:
                dumpfile = 'webwxgetcontact.json'
                self.logger.debug('saving webwxinit response to ' + dumpfile)
                with open(dumpfile, 'w') as f:
                    f.write(response.content)
            rjson = response.json()
            self.update_contacts(rjson['MemberList'])
            self.handler.on_login(self)
        else:
            self.logger.warn('webwxgetcontact error:{}'.format(response.status_code))


    def webwxbatchgetcontact(self):
        # Not needed right now
        url = self.base + '/webwxbatchgetcontact?type=ex&r={}&pass_ticket={}'.format(
                timestamp(), self.pass_ticket)
        params = {
            'BaseRequest': self._getBaseRequest(),
            "Count": len(self.groups),
            "List": [{"UserName": g['UserName'], "EncryChatRoomId":""} for g in self.groups]
        }
        response = self.session.post(url, data=params)
        if response.status_code == 200:
            pass

    def syncheck(self):
        retcode = -1
        selector = -1
        url = 'https://webpush.wx2.qq.com/cgi-bin/mmwebwx-bin/synccheck'
        params = {
                'r': timestamp(),
                'skey': self.skey,
                'sid': self.sid,
                'uin': self.uin,
                'deviceid': self.deviceid,
                'synckey': self._getSyncKeyStr(),
                '_': timestamp()
                }
        response = self.session.get(url, params=params)
        self.logger.debug('syncheck get:' + response.url)
        if(response.status_code == 200):
            regx = r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}'
            match = re.search(regx, response.content)
            if match:
                retcode = match.group(1)
                selector = match.group(2)
            else:
                self.logger.warn('syncheck response:{}'.format(response.content))
        else:
            self.logger.warn('syncheck error:{}'.format(response.status_code))

        self.logger.debug('retcode:{}, selector:{}'.format(retcode, selector))
        return (retcode, selector)

    def webwxsync(self):
        url = self.base + '/webwxsync?sid={}&skey={}&pass_ticket={}'.format(
                self.sid, self.skey, self.pass_ticket)
        params = {
                'BaseRequest': self._getBaseRequest(),
                'SyncKey': self.jsonsynckeys,
                'rr': ~timestamp()
                }
        response = self.session.post(url, json=params)
        self.logger.debug('webwxsync post:' + response.url)
        if response.status_code == 200:
            jresp = response.json()
            if jresp['BaseResponse']['Ret'] == 0:
                self.jsonsynckeys = jresp['SyncKey']
                if jresp['AddMsgCount'] > 0:
                    for msg in jresp['AddMsgList']:
                        self.handler.on_message(self, msg)
                if jresp['ModContactCount'] > 0:
                    self.update_contacts(jresp['ModContactList'])
                if 'SyncKey' in jresp:
                    self.jsonsynckeys = jresp['SyncKey']
            else:
                self.logger.warn('webwxsync repsonse:{}'.format(jresp['BaseResponse']['Ret']))
        else:
            self.logger.warn('webwxsync error:{}'.format(response.status_code))


    def name2id(self, alias):
        if alias in SPECIAL_USERS:
            return alias
        wxid = 'filehelper'
        for contact in self.groups + self.official_accounts + self.contacts:
            if contact['NickName'].encode('latin1') == alias or contact['RemarkName'].encode('latin1') == alias:
                wxid = contact['UserName']
                break
        return wxid

    def id2name(self, wxid):
        name = wxid[:6]
        cacheMissed = True
        if isGroupId(wxid):
            for group in self.groups:
                if group['UserName'] == wxid:
                    name = group['NickName']
                    cacheMissed = False
                    break
        elif isContactId(wxid):
            for contact in self.official_accounts + self.contacts:
                if contact['UserName'] == wxid:
                    if contact['RemarkName'] != '':
                        name = contact['RemarkName']
                    else:
                        name = contact['NickName']
                    cacheMissed = False
                    break
        elif wxid in SPECIAL_USERS:
            name = wxid
            cacheMissed = False


        if cacheMissed:
            self.logger.debug('Unknow id:{}'.format(wxid))
        return name.encode('latin1')

    def webwxsendmsg(self, wxid, text):
        url = self.base + '/webwxsendmsg?pass_ticket={}'.format(self.pass_ticket)
        msgid = str(timestamp()) + str(int(random.random() * 10))
        if type(text) == str:
            utext = text.decode('utf-8')
        else:
            utext = text
        params = {
                'BaseRequest': self._getBaseRequest(),
                'Msg': {
                    'Type': 1,
                    'Content': utext,
                    'FromUserName': self.myid,
                    'ToUserName': wxid,
                    'LocalID': msgid,
                    'ClientMsgId': msgid
                    }
                }
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        data = json.dumps(params,ensure_ascii=False)
        response = self.session.post(url, data=data.encode('utf-8'), headers=headers)
        if response.status_code == 200:
            self.logger.debug('webwxsendmsg response len: {}'.format(len(response.content)))
        else:
            self.logger.warn('webwxsendmsg error {}'.format(response.status_code))


    def webwxlogout(self):
        url = self.base + '/webwxlogout?sid={}&skey={}&pass_ticket={}'.format(
                self.sid, self.skey, self.pass_ticket)
        self.session.get(url)

            
    def _getSyncKeyStr(self):
        return '|'.join([str(kv['Key']) + '_' + str(kv['Val']) for kv in self.jsonsynckeys['List']])

    def _getBaseRequest(self):
        baserequest = {
                        'Uin': self.uin,
                        'Sid': self.sid,
                        'Skey': self.skey,
                        'DeviceID': self.deviceid,
                      }
        return baserequest

if __name__ == '__main__':
    client = WxClient()
    try:
        client.start_background()
        while True:
            time.sleep(60)

    except Exception as e :
        client.webwxlogout()
        print str(e)

