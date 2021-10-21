import psycopg2
import requests
TINDER_URL = "https://api.gotinder.com"

# 1 - добавить клиента в таблицу users
# 2 - добавить непеносимости
# 3 - добавить шаблон диалога


def add_to_users(person_id, name, surname, auth_token):
    conn = psycopg2.connect(dbname='d18ei58b0f0hv7',
                                user='xlecmelfjobtes',
                                password='dcf3b17a5ff5fe2f845c24cd797d56ae072dd89359aa0966b618bcde37dc8d58',
                                host='ec2-54-154-101-45.eu-west-1.compute.amazonaws.com')
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(f'''INSERT INTO db_tinderbot.users
                        (id, name , surname, auth_token)
                        VALUES
                        (\'{person_id}\', \'{name}\', \'{surname}\', \'{auth_token}\')''')
    cursor.close()
    conn.close()


def add_antipathy(person_id, antipathies, locale='ru'):
    # antipathies - лист с названиями preferences, которые нужно избегать
    # в бущущем нужно еще как то добавлять сходные предпочтения, которые тоже стоит избегать
    conn = psycopg2.connect(dbname='d18ei58b0f0hv7',
                            user='xlecmelfjobtes',
                            password='dcf3b17a5ff5fe2f845c24cd797d56ae072dd89359aa0966b618bcde37dc8d58',
                            host='ec2-54-154-101-45.eu-west-1.compute.amazonaws.com')
    conn.autocommit = True
    cursor = conn.cursor()
    prefix = 'rus'
    if locale != 'ru':
        prefix = 'eng'
    ids_for_antipathies = list()
    for name in antipathies:
        cursor.execute(f'''SELECT id
                            FROM db_tinderbot.preferences
                            WHERE {prefix}_name = \'{name}\'''')
        pref_id = cursor.fetchone()
        ids_for_antipathies.append(pref_id[0])
    for pref_id in ids_for_antipathies:
        cursor.execute(f'''INSERT INTO db_tinderbot.antipathy
                                (person_id, preference_id)
                                VALUES
                                (\'{person_id}\', \'{pref_id}\')''')
    cursor.close()
    conn.close()


def initialization(name, surname, auth_token, antipathies):
    conn = psycopg2.connect(dbname='d18ei58b0f0hv7',
                            user='xlecmelfjobtes',
                            password='dcf3b17a5ff5fe2f845c24cd797d56ae072dd89359aa0966b618bcde37dc8d58',
                            host='ec2-54-154-101-45.eu-west-1.compute.amazonaws.com')
    conn.autocommit = True
    cursor = conn.cursor()
    response_id = requests.get(TINDER_URL + "/profile", headers={"X-Auth-Token": auth_token}).json()
    person_id = response_id['_id']
    add_to_users(person_id, name, surname, auth_token)
    add_antipathy(person_id, antipathies)
    cursor.close()
    conn.close()
