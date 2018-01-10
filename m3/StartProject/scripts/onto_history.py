import sqlite3
import os
import datetime
import jsondiff
import json


class DB():
    def __init__(self, db_path=None):
        self.connection = None
        self.cursors = None
        if db_path != None:
            self.connect(db_path)

    def connect(self, db_path):
        self.connection = sqlite3.connect(db_path)
        self.cursors = self.connection.cursor()

    def execute(self, cmd, values=''):
        self.cursors.execute(cmd, values)
        self.commit()

    def commit(self):
        self.connection.commit()

    def exit(self, commmit=False):
        if commmit is not False:
            self.commit()
        self.connection.close()

    def insert_into_table(self, ontology):
        self.cursors.execute("select ontology from version order by date_added desc limit 1")
        last_version = self.cursors.fetchone()[0]
        last_version = json.loads(last_version)
        difference = jsondiff.diff(last_version, ontology)
        self.cursors.execute("insert into version(ontology, date_added, differences) values(?, ?, ?)",
                             (str(json.dumps(ontology)), datetime.datetime.now(), str(difference)))


def create_table(conn):
    conn.execute('''create table version (ontology text, date_added date, differences text)''')
    d = dict()
    conn.execute("insert into version(ontology, date_added, differences) values(?, ?, ?)", (json.dumps(d),datetime.datetime.now(),''))

def addDataToJson():
    dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
    dbObj = DB(os.path.join(dir_path, "history.db"))
    dbObj.execute('select * from version')
    json_data = dict()
    for i in dbObj.cursors.fetchall():
        json_data[str(i[1])] = i[2]
    return json_data

if __name__ == '__main__':
    dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
    dbObj = DB(os.path.join(dir_path, "history.db"))
    j1 = json.load(open(r'D:\work\Anul3\AI\GIT\AI-M3\m3\StartProject\resources\input.json'))
    j2 = json.load(open(r'D:\work\Anul3\AI\GIT\AI-M3\m3\StartProject\resources\input2.json'))
    dbObj.execute('select * from version')
    #for i in dbObj.cursors.fetchall():
    #print(i[2])  
    #create_table(dbObj)
    #dbObj.insert_into_table(j2)
    
