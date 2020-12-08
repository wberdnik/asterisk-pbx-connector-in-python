""" Class for planing material and route streams

  @author vlf <wberdnik@gmail.com>
""" 

import itertools
import uuid

import sys; sys.path.insert(0, sys.path[0]+'\\tele')
from config_trunks import trunks

#from collections import namedtuple
#TypeClass = namedtuple('region' , 'color mileage')


class MaterialRouter(object):
    __slots__=('_db','uid')

    def __init__(self,db):
        self._db = db
        self.uid = ''

    @property
    def maxdemand(self): #php $currentDemand = ['extra' => $analiticDemmand['extra'],'region_id' => $analiticDemmand['region_id'],'cnt'=>0];
         
        self._db<<'Select `region_id`, `extra`, -COUNT(`intphone`) as cnt FROM `tele_material` WHERE `start_dial` is NULL GROUP BY `region_id`, `extra`'
        totaldemand= {(row['region_id'],row['extra']):row.copy() for row in self._db.all()}# одеяло
       
        for trunk in trunks :
            capacity = trunk['capability']
            if(not capacity): continue
            
            decart = list(itertools.product(trunk['regions'],trunk['extra']))
            for region,extra in decart:
                if((region,extra) not in totaldemand.keys()):
                    totaldemand[(region,extra)] = {'extra' : extra,'region_id' :region,'cnt':0} #расширяем многообразие

                if(totaldemand[(region,extra)]['cnt'] <0): # перетягиваем на себя одеяло
                    delta = min(capacity,-totaldemand[(region,extra)]['cnt']) #minus stock
                    capacity -= delta
                    totaldemand[(region,extra)]['cnt'] += delta
            
            ln = len(decart)
            if(capacity and ln): # не хватило одеяла - размажем заказ c запасом по всему декарту, ибо может не быть чего-то, и мы будем гоняться за дефицитом
                part = int(capacity/2)
                for region,extra in decart:
                    totaldemand[(region,extra)]['cnt'] += part
        return list(x for x in totaldemand.values() if x['cnt']>0) # https://habr.com/ru/post/320288/
    
    def feedstock(self,dictTrunk):
        #проблема взаимоисключения звонка с разных транков/процессов.
        #пользуемся принципом атомарности команды UPDATE.Сначала бронируем пессимистично и жадно, берем свою норму, остальное возвращаем в материал
        #проблема - маркировать транком нельзя - может входить в коллизию с другим процессом, поэтому пользуемся сеансовым UID

        
        strRegions = ','.join(map(str, dictTrunk['regions']))
        strExtra = ','.join(map(str, dictTrunk['extra']))
        self._db << 'SELECT `region_id`, `extra`, MIN(`id`) start, MAX(`id`) stop, COUNT(`id`) cnt FROM `tele_material` ' + \
                    ' WHERE `trunk_dial` is NULL AND `start_dial` is NULL AND `region_id` in (0{}) AND `extra` in (0{}) '.format(', ' + strRegions, ', ' + strExtra) + \
                    ' GROUP BY `region_id`,`extra`'
        stockpile = self._db.all()
        if not stockpile: 
            print('Нет материалов для звонка')
            return list()
        divider = len(stockpile)
        if not divider: 
            print('Нет материала для звонка')
            return list()
        #запас в звонилку отдаем на 2 минуты
        needs = dictTrunk['cps']*120 #2минуты = 120 сек 
        if not needs: 
            print('У транка нулевой cps')
            return list()
       
        currentUID = str(uuid.uuid4())
        self.uid =currentUID
        for slice in stockpile:
            if not slice['cnt']: continue
            if slice['cnt'] <= needs:
                self._db<<'UPDATE `tele_material` SET `trunk_dial` = %s, `start_dial` = NOW() \
                WHERE `trunk_dial` IS NULL AND `start_dial` IS NULL AND `region_id` = %s AND `extra` = %s'
                self._db.execute(currentUID,slice['region_id'],slice['extra'])
            else:
                idRange = slice['stop'] - slice['start']
                ratio = float(needs)/slice['cnt']
                idRatio = int(idRange*ratio)
                if not idRatio: continue
                idEnd =slice['start'] +idRatio # почему с начала, а не с конца - в конец может прийти поставка и мы ее грохнем
                self._db<<'UPDATE `tele_material` SET `trunk_dial` = %s, `start_dial` = NOW()  \
                WHERE `id`< %s AND `trunk_dial` IS NULL AND `start_dial` IS NULL AND `region_id` = %s AND `extra` = %s'
                self._db.execute(currentUID,idEnd,slice['region_id'],slice['extra'])
        self._db.commit()

        self._db<<'SELECT `id` FROM `tele_material` WHERE `trunk_dial` = %s LIMIT %s'
        stockpile = self._db.all(currentUID,needs)
        ids = (str(x['id']) for x in stockpile)
        ids = list(ids)
        self._db<<('UPDATE `tele_material` SET `trunk_dial` = IF(`id` IN ({0}), `trunk_dial`, NULL), `start_dial` = IF(`id` IN ({0}) ,`start_dial`, NULL)  \
                WHERE `trunk_dial` = %s'.format(', '.join(ids))) #способ построения запроса - особенность работы mysql с большими таблицами
        self._db<currentUID
        return ids