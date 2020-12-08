import struct
import base64
import json
import zipfile
from os import unlink
import sys; sys.path.insert(0, sys.path[0]+'\\tele')
from const import DIR_NAME
from config_trunks import trunks


class MakePack2Leadinka(object):    
    
    def __init__(self, receipt, maxdemand):
        self._content = list() # type: list of dict
        self._ids = set()
        self._receipt = '0000-0000-0000-0000-0000' if receipt == '' else receipt
        self._maxdemand = maxdemand if maxdemand else [] # type: list потребность в материале [{region_id:int,extra:int, cnt:int}]

    def __lshift__(self,row): 	# like cout << {keypress: '4'}
        self._content.append(row)
        self._ids.add(str(row['id']))

    @property
    def ids(self):
        return self._ids

    def pack(self):
       # import pdb; pdb.set_trace()
        otvet = {'receipt':self._receipt, 'maxdemand':self._maxdemand, 'trunks': trunks,'data':[]}
        for row in self._content:           
            bzero = 0b00000000
            trunk = row['trunk'] if row['trunk'] is not None else ''
            bitfields = bzero | (bzero,0b0000001)[bool (row['inbound'])] | (bzero,0b00000010)[bool(row['success'])] | (bzero,0b00000100)[bool(row['redirected'])]
            intphone = int(row['intphone'] if row['intphone'] is not None else 0)
            hb = int(intphone/1000000000)
            bin =struct.pack("=BBLLHH",bitfields, hb, intphone -1000000000*hb,
                             row['material_id'] if row['material_id'] is not None else 0, # предполагается, что число звонков не превысит 4 млрд, для всех сотовых - 1 млрд
                             row['ringingtime'] if row['ringingtime'] is not None else 0,
                             row['calltime'] if row['calltime'] is not None else 0) # выравнивание https://tirinox.ru/python-struct/

            base64Data = base64.b64encode(bin).decode('ascii') # 24 символа
           # decode b->str кодировки, а затем в нашу... encode: str->byte нашу кодировку в заданную, а затем в бату
            packRow = {'k':row['keypress'] if row['keypress'] is not None else '','t':trunk, 'd':base64Data}
            otvet['data'].append(packRow);
        jsonStr = json.dumps(otvet)
        filename = DIR_NAME+'pack.bin'
        with open(filename, 'wb') as file_to_save:
            file_to_save.write(jsonStr.encode('utf8'))
            file_to_save.close()
            #__init__(self, file, mode="r", compression=ZIP_STORED, allowZip64=True,  НЕТУ !!!  compresslevel=None):
    
        with zipfile.ZipFile(DIR_NAME+'read.zip', 'w', zipfile.ZIP_DEFLATED,True) as newZip:
            newZip.write(filename,'pack.bin')
            newZip.setpassword(b'*****') # Шифруем https://stackoverflow.com/questions/43439979/python-zipfile-how-to-set-a-password-for-a-zipfile
                        
        unlink(filename)
        return open(DIR_NAME+'read.zip', 'rb')

    @staticmethod
    def unlinkFiles(zipcontent):
        zipcontent.close()
        unlink(DIR_NAME+'read.zip')
