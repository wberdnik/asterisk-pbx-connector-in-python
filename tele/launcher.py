""" Just a collection of static methods of launcher

  @author vlf <wberdnik@gmail.com>
"""

import sys; sys.path.insert(0, sys.path[0]+'/tele')
from teleDB import TeleDB
import http.client
from makePack2leadinka import MakePack2Leadinka
from materialRouter import MaterialRouter
from parseLeadinka import ParseLeadinka
from caller import Caller
import os
import re
import uuid
#import requests
#import time
import json
from config_trunks import find as decipher
from config_trunks import trunks
from const import DIR_NAME
from productAnalysis import fillProduct

class Launcher(object):

    __slots__=()
    @staticmethod
    def migrate(namespace):
        with TeleDB() as db:
            db<<'CREATE TABLE `tele_material` (`id` BIGINT AUTO_INCREMENT, \
                `intphone` BIGINT NOT NULL, `region_id` integer, `extra` integer, `trunk_dial` varchar(50), `start_dial` TIMESTAMP DEFAULT NULL,\
                 PRIMARY KEY(`id`))ENGINE=InnoDB;'<None
            #db<<'CREATE INDEX ind_trunk_material ON `tele_material`(`trunk_dial`)'<None
            db<<'CREATE INDEX ind_dimensions_material ON `tele_material`(`region_id`,`extra`)'<None
            db<<'ALTER TABLE `tele_material` CHANGE `start_dial` `start_dial` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP'< None
            db<<'CREATE TABLE `tele_blacklist` (`id` INT AUTO_INCREMENT, `startintphone` bigint NOT NULL, `stopintphone` bigint NOT NULL, \
                `start_period` TIMESTAMP NOT NULL, `stop_period` TIMESTAMP, text varchar(100), PRIMARY KEY(`id`))ENGINE=InnoDB;'<None
            db<<'CREATE TABLE tele_production (`id` BIGINT AUTO_INCREMENT, `intphone` BIGINT NOT NULL, `material_id` BIGINT, `created` TIMESTAMP DEFAULT NOW(),\
                `inbound` boolean DEFAULT false, `success` boolean NOT NULL, `ringingtime` integer DEFAULT 0, `calltime` integer DEFAULT 0, `trunk` varchar(50) NOT NULL, \
                `redirected` boolean DEFAULT false, `keypress` varchar(5),PRIMARY KEY(`id`))ENGINE=InnoDB;'<None
            db<<'CREATE TABLE `tele_settings` (`id` INT AUTO_INCREMENT, `label` varchar(30), `str_value` varchar(200), PRIMARY KEY(`id`))ENGINE=InnoDB;'<None
            db<<'CREATE UNIQUE INDEX ind_key_setting ON `tele_settings`(`label`)'<None
            db.setting(receipt='')


    @staticmethod
    def fixdb(namespace):
        #import pdb; pdb.set_trace()
        with TeleDB() as db:
            db << 'UPDATE `tele_material` SET `trunk_dial` = NULL, `start_dial` = NULL WHERE `start_dial`< DATE_SUB(NOW(), INTERVAL 3 MINUTE)' < None
            db << 'DELETE FROM `tele_material` WHERE `id` IN (SELECT  `material_id` FROM `tele_production`)' < None
            
            param = {'tr'+str(tr['id']).strip():tr['actionButton'][0]+str(tr['background']).strip() for tr in trunks}
            db.setting(**param)
    @staticmethod
    def trunk(namespace):
        #import pdb; pdb.set_trace()
        trunk = decipher(namespace.trunk)
        if not trunk:
            print ('указан несуществующий транк - ошибка')
            return
        with TeleDB() as db:
            router = MaterialRouter(db)
            feedstock = router.feedstock(trunk)
            if feedstock and namespace.verbose:
                print('Запас '+str(len(feedstock)))
            caller = Caller(verbose=namespace.verbose)
            if not caller.produce(db, trunk,feedstock):
                db << 'UPDATE `tele_material` SET `trunk_dial`=NULL,`start_dial`=NULL WHERE `trunk_dial` = %s' < router.uid

    @staticmethod
    def call(namespace):
        caller = Caller(verbose = True)
        phone = namespace.phone if namespace.phone is not None else 9023618802
        trunk = namespace.trunk if namespace.trunk is not None else '2' 
        phone2 = namespace.phone2 if namespace.phone2 is not None else None
    
        trunk = decipher(trunk)
        if not trunk:
            print ('указан несуществующий транк - ошибка')
            return
    
        muid = str(uuid.uuid4())
        with TeleDB() as db:
            db << 'INSERT INTO `tele_material` (`intphone`, `region_id`, `extra`, `start_dial`,`trunk_dial`) \
               VALUES (%s,33,2,NOW(),%s)' < (int(phone),muid)
            db << 'SELECT last_insert_id() as id'
            ids = [db.one()['id']]
            if phone2:
                db << 'INSERT INTO `tele_material` (`intphone`, `region_id`, `extra`, `start_dial`,`trunk_dial`) \
                   VALUES (%s,33,2,NOW(),%s)' < (int(phone2),muid)
                db << 'SELECT last_insert_id() as id'
                ids.append(db.one()['id'])
                
            #import pdb; pdb.set_trace()
               
            if not caller.produce(db, trunk, ids):
                db << 'UPDATE `tele_material` SET `trunk_dial`=NULL,`start_dial`=NULL WHERE `id` = %s' < muid

            # в случае обрывая связи, что бы не получилось отсроченного звонка
            # Затирает до звонка db << 'DELETE FROM `tele_material` WHERE `id` = %s' < ids[0]
            # db << 'DELETE FROM `tele_production` WHERE `material_id` = %s' < ids

    @staticmethod
    def leadinka(namespace):
        
        # Подготовим POST_BODY
        # `intphone` BIGINT NOT NULL, `created` TIMESTAMP DEFAULT NOW(), `inbound` boolean DEFAULT false, `success` boolean NOT NULL, \
        #                     `ringingtime` integer DEFAULT 0, `calltime` integer DEFAULT 0, `trunk` varchar(50) NOT NULL, \
        #                     `redirected` boolean DEFAULT false, `keypress` varchar(5)
        # посчитать потребности

        #Выборка. Запомнить id-s для удаления из БД при успешном выполнении запроса (транзакция)
        #Упаковать. Отдать квитанцию
        #Принять
        #принять квитанцию и сохранить
        # принять материал
        # принять правила ?? установка правил в Астериск
        with TeleDB() as db:
            bodypack2leadinka = MakePack2Leadinka(db.setting('receipt'), MaterialRouter(db).maxdemand)
            #db.CreateCommand('Select * FROM `tele_production` LIMIT 5000')
            #for row in db.all(): bodypack2leadinka << row
            fillProduct(db,bodypack2leadinka)
            
            conn = http.client.HTTPSConnection("leadinka.com")      
            headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
            zipcontent = bodypack2leadinka.pack()

            try:
                conn.request("POST","/telemarket/api/index",zipcontent,headers)           
            except Exception as ex:
                print('Ошибка чтения ресурса ', ex)
                os._exit(10)
            
            bodypack2leadinka.unlinkFiles(zipcontent)

            response = conn.getresponse()
            headerName = response.getheader('Content-Disposition', None)
    
            if (response.status>=300) :
                print('Ошибка на сервере',response.status, response.reason) 
                os._exit(10)
            if(response.length<5):
                print('Пустой ответ от сервера') 
                os._exit(10)
            if( (headerName is None) or ('attachment' not in headerName) or ('filename' not in headerName)):
                print('Сервер не передал имя файла') 
                os._exit(10)
            uid_pack = next(iter(re.findall('filename\s*\=\s*\"(.+)\.zip\s*"',headerName)),None)
            if( uid_pack is None):
                print('не удачная попытка выделения имени файла с сервера') 
                os._exit(10)

            db.setting(receipt = uid_pack)
            parser = ParseLeadinka(response.read())
            conn.close()
            
            #запрос успешны (транзакция) - удаляем production
            db.CreateCommand('DELETE FROM `tele_production` WHERE `id` =%s')
            for id in bodypack2leadinka.ids:
                db.execute(id) # особенность мускула с большими данными
            
            if(parser.hasRules):
                db << 'TRUNCATE TABLE `tele_blacklist`' < None
                db.CreateCommand('INSERT INTO `tele_blacklist` (`startintphone`, `stopintphone`, `start_period`, `stop_period`, `text`)\
               VALUES (%s,%s,%s,%s,%s)').\
                    many([(row['startintphone'],row['stopintphone'],row['start_period'],row['stop_period'],row['text']) for row in parser.rules])
            if(len(parser)):
                db << 'INSERT INTO `tele_material` (`id`,`intphone`, `region_id`, `extra`) \
               VALUES (%s,%s,%s,%s) on duplicate key UPDATE `intphone` = %s, `region_id` = %s, `extra` = %s'
                for row in parser:
                    db < (row['material_id'],row['intphone'],row['region_id'],row['extra'],row['intphone'],row['region_id'],row['extra'])
