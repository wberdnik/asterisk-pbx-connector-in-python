import pymysql
"""Wrap of mysql library. It will possible in future to use ODBC 
  Below is an example showing some typical usage of teleDB
 python3
  result = teleDB().CreateCommand('SELECT * FROM table WHERE (id, status) in (%s,%s)').all((1034,false))

  @method teleDB CreateCommand(sql_text) take SQL request
  @methods None execute(tuple), dictonary one(tuple), list of dict all(tuple) - execute request 
  WARNING Commands INSERT INTO, UPDATE should be COMPLITED with execite_commit(), because Its are cashing !!!!
  @author vlf <wberdnik@gmail.com>
  @see https://pymysql.readthedocs.io/en/latest/user/examples.html
"""
class TeleDB(object):
    __slots__ = ('_db','_sql_text')
   
    def __init__(self):        
        self._sql_text = '' #type:str
        try:
            self._db = pymysql.connect(host="localhost",
                                        user = "root",
                                       ***
                                        charset = "utf8",
                                        cursorclass = pymysql.cursors.DictCursor)
        except pymysql.Error as er:
            print('Ошибка подключения к БД {}'.format(er))
            raise SystemExit

    def CreateCommand(self, sql_text):
        self._sql_text = sql_text
        return self
        
    def __lshift__(self,sql_text):
        self._sql_text = sql_text
        return self

    def __lt__(self,params):
        if params is None:
            self.execute_commit()
        elif isinstance(params,tuple):
            self.execute_commit(*params)
        else:
            self.execute_commit(params)

    def execute(self,*params): #tuple
        try:
            with self._db.cursor() as cursor: #cursor = self._db.cursor()
                cursor.execute(self._sql_text,params) # для нескольких запросов - использовать executemany
            #cursor.close() # капкан - не закрывает транзакцию
        except Exception as err:
            print('Ошибка выполнения запроса execute() {}:'.format(self._sql_text),'\n{}'.format(err),'')

    def execute_commit(self,*params): #tuple
        try:
            with self._db.cursor() as cursor: #cursor = self._db.cursor()
                cursor.execute(self._sql_text,params) # для нескольких запросов - использовать executemany
                self._db.commit() # !!close на __exit__
            #cursor.close() # капкан - не закрывает транзакцию

        except Exception as err:
            print('Ошибка выполнения запроса execute_commit() {}:'.format(self._sql_text),'\n{}'.format(err),'')

    def many(self,*params): #tuple
        try:
            with self._db.cursor() as cursor: #cursor = self._db.cursor()
                cursor.executemany(self._sql_text,params) # для нескольких запросов - использовать executemany
                self._db.commit() # !!close на __exit__
            #cursor.close() # капкан - не закрывает транзакцию

        except Exception as err:
            print('Ошибка выполнения запроса many() {}:'.format(self._sql_text),'\n{}'.format(err),'')

    def commit(self):
        self._db.commit()

    def one(self,*params): #tuple
        try:
            with self._db.cursor() as cursor:
                cursor.execute(self._sql_text,params)
                return cursor.fetchone() 
        except Exception as err:
            print('Ошибка выполнения запроса one() {}:'.format(self._sql_text),'\n{}'.format(err),'')

    def all(self,*params): #tuple
        try:
            with self._db.cursor() as cursor:
                cursor.execute(self._sql_text,params)
                return cursor.fetchall()
        except Exception as err:
            print('Ошибка выполнения запроса all() {}:'.format(self._sql_text),'\n{}'.format(err),'')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._db.commit()
#     return isinstance(value, TypeError) - подавление исключения typeerror

    def __del__(self): 
        #self._db.commit()
        self._db.close()

    def setting(self,read=None,**writeParams):
        for label,value in writeParams.items():
           self << "INSERT INTO `tele_settings` (`label`,`str_value`) VALUES(%s,%s) on duplicate key UPDATE `str_value` = %s"
           self.execute_commit(label,value,value)
        if(read is None):
            return None
        result = self.CreateCommand('SELECT `str_value` FROM `tele_settings` WHERE `label` = %s').one((read))
        return '' if result is None else result['str_value']
