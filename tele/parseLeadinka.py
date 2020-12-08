import zipfile
import struct
import json
from os import unlink
import sys; sys.path.insert(0, sys.path[0]+'/tele')
from const import DIR_NAME


class ParseLeadinka(object):
    
    __slots__=('_content','_rules','_limit','_counter') 

    def __init__(self,httpBody):
        nameZip = DIR_NAME + 'write.zip'
        nameBin = 'pack.bin'
        nameRules = 'blacklist.json'
        pwdZip = b'****'

        with open(nameZip, 'wb') as file_to_save:
            file_to_save.write(httpBody)
            file_to_save.close()
       
        if(not(zipfile.is_zipfile(nameZip))):
           raise Exception('В теле запроса не Zip')
        self._rules = []       
        with zipfile.ZipFile(nameZip, 'r', ) as newZip:
            newZip.setpassword(pwdZip) #https://stackoverflow.com/questions/43439979/python-zipfile-how-to-set-a-password-for-a-zipfile
            filelist = newZip.namelist() #type:tuple
            if(nameBin in filelist):
                contents = newZip.read(nameBin,pwdZip)
                self._content = [{'intphone':hb* 1000000000 + p, 'material_id':id, 'region_id':r, 'extra':e} for hb, p, id, r, e in struct.iter_unpack('=BLLHH', contents)]
            if(nameRules in filelist):
                contents = newZip.read(nameRules,pwdZip)
                self._rules = json.loads(contents)
    
        self._limit = len(self._content)
        self._counter = -1
        unlink(nameZip)

    def __len__(self):
        return len(self._content)

    def __iter__(self):
        return self
        
    def __next__(self):
        if self._counter < self._limit-1:
            self._counter += 1
            return self._content[self._counter]
        else:
            self._counter = -1
            raise StopIteration

# generator for rules
# for (rule in parseLeadinkaObject.rules):
    def rules(self, rcounter):
        while(rcounter < len(self._rules)):
            rcounter += 1
            yield self._rules[rcounter-1]
    @property
    def hasRules(self):
        return bool(self._rules)
