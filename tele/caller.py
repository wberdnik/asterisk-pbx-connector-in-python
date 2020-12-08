#Bridge to Asterisk
#@author vlf <wberdnik@gmail.com>

import socket
import time
import select
from teleDB import TeleDB
from config_trunks import find as findTrunk
import uuid
#import asyncio

class AmiSocket(object):
    def __init__(self, verbose):
        self._sock = socket.socket()
        self._verbose = verbose
        self._sock.connect(('localhost', 5038))
        self._sock.setblocking(0)
        self._start = time.time()


    def send_command(self, collection):
        for key,value in collection:
            res =  key+': '+value+"\r\n"
            if self._verbose:
                print(key+': '+value)
            self._sock.send(res.encode('utf8'))
            
        res = "\r\n"
        self._sock.send(res.encode('utf8'))
        ready = select.select([self._sock], [], [], 1)
        if ready[0]:
            data = self._sock.recv(1024)
            if self._verbose and data:
                print('>>> '+data.decode('utf8'))
        self._start = time.time()
        
    def amiWait(self):
        waswait = time.time() - self._start
        if waswait > 3:
            self._sock.close()
            return
            
        while(True):
            ready = select.select([self._sock], [], [], 120)
            if ready[0]:
                data =  self._sock.recv(1024)
                if data:
                    self._start = time.time()
                if  self._verbose and data:
                     print('Async: '+data.decode('utf8'),'')
            waswait = time.time() - self._start
            if waswait > 3:
                self._sock.close()
                return
            else:
                print('...waiting({}) AMI ...'.format(waswait))
                time.sleep((10-waswait)%3)
        
                

def AMI_command(function_to_decorate):
    def a_wrapper(self,*arg):
        self._connector.send_command([("Action", "login"),("Events", "off"),('Username', self.asteriskUser),('Secret',self.pwd)]) 
        self._connector.send_command(function_to_decorate(self,*arg))
        self._connector.send_command([('Action', 'Logoff')])
    return a_wrapper

class Caller(object):
    asteriskUser = 'web_user'
    pwd = '****'

    def __init__(self,**args):
        self._verbose = False
        for key,val in args.items():
            if key == 'verbose': self._verbose = bool(val)
        self._connector = None
    
    def __del__(self):
        if self._connector:
            self._connector.amiWait() # Если сразу разрывать канал - звонки снимаются
        
    @AMI_command
    def _call(self,prefix, material_collection,  context = 'tele-dialer', contextWait = 'post-tele-dialer', extra =0):           
        #http://asterisk.ru/knowledgebase/Asterisk+Manager+API+Action+Originate
        sz = len(material_collection)
        if sz > 10 :
            print('Ошибка отправки: нельзя отправить больше 10 номеров')
            raise SystemExit
        #http://www.voip.rus.net/tiki-index.php?page=Asterisk+Local+channels
        dictTrunk = findTrunk(prefix)
        
        if self._verbose:
            print('Call by ' + prefix)
            
        background = 'man' if not dictTrunk['background'] else dictTrunk['background']
        actionbutton = '1' if not dictTrunk['actionButton'] else str(dictTrunk['actionButton'])[0:1]
        
        #import pdb; pdb.set_trace()
        try:
            if extra and dictTrunk['voices']:
                voiceRule = dictTrunk['voices'][extra]
                background = voiceRule[0]
                actionbutton = voiceRule[1]
        except Exception :
            pass
        
        result = [('Action', 'originate'), # это и есть Dial
                            ('Channel', 'Local/s@{}/n'.format(context)),
                            ('Async', 'true'), # Если указано “true” исходящий вызов будет производиться асинхронно.
                           # ('Action', 'WaitEvent'), - для Async
                           # ('Timeout', '60'),
                            ('Exten', 's'),# контекст совершения вызова
                            ('Priority', '1'),
                            ('Context', contextWait),
                            ('Variable', 'PREFIX={}'.format(prefix)),
                            ('Variable', 'UID={}'.format(str(uuid.uuid4()))),
                            ('Variable', 'BACKGROUND={}'.format(background)),
                            ('Variable', 'ACTIONBUTTON={}'.format(actionbutton)),
                             ]
        for double in enumerate(material_collection, start =1):
            result.append(('Variable', 'ID{}={}'.format(*double)))
        return result

    def produce(self, db, dictTrunk, iterMaterial_id):
        if not dictTrunk or not isinstance(dictTrunk,dict): return False
        currentTrunk = dictTrunk
        
        if currentTrunk['cps'] <=0: return False
        
        db << 'UPDATE `tele_material` SET `trunk_dial` = NULL, `start_dial` = NULL WHERE `start_dial`< DATE_SUB(NOW(), INTERVAL 3 MINUTE) AND `trunk_dial` = %s' 
        db.execute_commit(currentTrunk['id'])
        db << 'DELETE FROM `tele_material` WHERE `id` IN (SELECT  `material_id` FROM `tele_production`)' < None
        
        cnt = min(10, currentTrunk['channels'])
        #tenpacks = list(zip(*[iter(iterMaterial_id)] * cnt)) -не работает
        #https://ru-asterisk.livejournal.com/30209.html - AMI штука загадочная и работает своеобразно. у меня были ситуации, 
        #когда вываливалось непонятно что вперемешку. как я понял, главный залог устойчивой работы в том, чтобы был всего 
        # 1 коннект из вашего приложения в AMI (1 поток) в 1 момент времени. если попытаете распараллеливание, то может быть всё что угодно вплоть до падения астера
        cnt = 1 
        
        #костылим
        tenpacks = []
        ten = []
        for id_ in iterMaterial_id:
            if len(ten) >=cnt:
                tenpacks.append(ten)
                ten = []
            ten.append(id_)
        if len(ten) >0:
            tenpacks.append(ten)
        J = 0
        for ten in tenpacks:
            start = time.time()
            
            for i in range(20):
                if i ==19:
                    return False
                # после звонка, астериск удалит материал и добавит выработку. Наличие trunk_dial с нашим транком - это нагрузка на транк, выполняемая сейчас
                db.commit()
                result = db.CreateCommand('SELECT COUNT(`id`) as load1 FROM `tele_material` WHERE `trunk_dial` = %s').one(currentTrunk['id'])
                if (result['load1'] <= max(currentTrunk['channels'] - len(ten), 1)): break
                if self._verbose:
                    print('Waiting for overload ({})'.format(result['load1']))
                time.sleep(5)
        
            db << ('UPDATE `tele_material` SET `trunk_dial` = %s, `start_dial` = NOW() WHERE `id` IN ({})'.format(','.join(map(str,ten))))
            db < currentTrunk['id']
            
            db << 'SELECT extra FROM tele_material WHERE id = %s'
            extra = db.one(ten[0])
            extra = extra['extra']

            self._connector = AmiSocket(self._verbose)
            self._call(currentTrunk['id'], ten, currentTrunk['context'], currentTrunk['contextWait'],extra)
            J = J + 1
            waswait = time.time() - start
            cpswait= len(ten) * max(1 / currentTrunk['cps'] - waswait, 0)
        
            if cpswait:
                if self._verbose: 
                    print('cps waiting ....')
                time.sleep(cpswait) #обеспечиваем cps
                
            self._connector.amiWait() # Если сразу разрывать канал - звонки снимаются
            
        if self._verbose: 
            print('success exit (in {}/pack {}/i {})....'.format(len(iterMaterial_id), len(tenpacks), J))
        
            
        return True
