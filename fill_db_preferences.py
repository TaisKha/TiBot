import psycopg2
import datetime
import time
from communication import TinderAPI
import requests

TINDER_URL = "https://api.gotinder.com"

	# cursor.execute('INSERT INTO db_tinderbot.likes (person_id, liked_person_id, date) VALUES (%s, %s, %s)',
	# 				(client[0], person.id, datetime.datetime.utcnow()))


con_to_db = psycopg2.connect(dbname='d18ei58b0f0hv7',
							 user='xlecmelfjobtes',
							 password='dcf3b17a5ff5fe2f845c24cd797d56ae072dd89359aa0966b618bcde37dc8d58',
							 host='ec2-54-154-101-45.eu-west-1.compute.amazonaws.com')
con_to_db.autocommit = True
cursor = con_to_db.cursor()
cursor.execute('SELECT * FROM db_tinderbot.users')
client = cursor.fetchone()
api = TinderAPI(client[3])
prefs_rus = api.interests_available('ru')
prefs_eng = api.interests_available('en')
for id, rus_name in prefs_rus.items():
    cursor.execute('INSERT INTO db_tinderbot.preferences (tinder_id, eng_name, rus_name) VALUES (%s, %s, %s)',
                   (id, prefs_eng[id], rus_name))
cursor.close()
con_to_db.close()
