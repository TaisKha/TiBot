import psycopg2
import datetime
from time import sleep
from communication import TinderAPI
import requests

TINDER_URL = "https://api.gotinder.com"


class Client:
    def __init__(self, person):
        self.id = person[0]
        self.name = person[1]
        self.surname = person[2]
        self.token = person[3]
        self.liking = person[4]
        self.writing = person[5]

    def __str__(self):
        return self.id + " " + self.name + " " + self.surname


def start_conversation_with_db(client, limit_n_matches=10, limit_pages=2):
    print("START writing for", client)
    # client = (person_id, name, surname, token, is_liking, is_writing)
    conn = psycopg2.connect(dbname='d18ei58b0f0hv7',
                            user='xlecmelfjobtes',
                            password='dcf3b17a5ff5fe2f845c24cd797d56ae072dd89359aa0966b618bcde37dc8d58',
                            host='ec2-54-154-101-45.eu-west-1.compute.amazonaws.com')
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(f'''SELECT message
                        FROM db_tinderbot.messageorder
                        JOIN db_tinderbot.messagetemplates
                        ON db_tinderbot.messageorder.msg_id = db_tinderbot.messagetemplates.id 
                        WHERE db_tinderbot.messageorder.person_id = \'{client.id}\'
                                AND db_tinderbot.messageorder.msg_num = 0''')
    init_msg = cursor.fetchone()[0] + ', '
    api = TinderAPI(client.token)
    cursor.execute(f'''SELECT * 
                        FROM db_tinderbot.matches 
                        WHERE person_id =  \'{client.id}\'''')
    if cursor is not None:
        old_matches = set(map(lambda x: (x[1], x[4], x[5]), cursor.fetchall())) # match_id,last_msg_id, msg_count
    else:
        old_matches = set()
    tmp_matches = requests.get(TINDER_URL + f"/v2/matches?count={limit_n_matches}",
                               headers={"X-Auth-Token": client.token}).json()
    page = 1
    go = True
    cursor.execute(f'''SELECT message 
                        FROM db_tinderbot.messageorder
                        JOIN db_tinderbot.messagetemplates
                        ON msg_id = id  
                        WHERE msg_num = 1 AND person_id = \'{client.id}\' ''')  # ищем первое сообщение для данного клиента
    first_question = cursor.fetchone()[0]
    while True:
        if page > limit_pages:
            break
        for match in tmp_matches['data']['matches']:
            match_id = match['id']
            print(match_id, match['message_count'])
            if match_id in set(map(lambda x: x[0], old_matches)): #x[0] это match_id
                go = False
                break
            if len(match['messages']) != 0:
                print(f'already have messages with {match_id}')
                break
            # api.write_to_id(match_id, msg=init_msg + match['person']['name'] + "!")
            api.write_to_id(match_id, msg=init_msg + match['person']['name'])
            api.write_to_id(match_id, msg=first_question)
            print("First message to ", match_id) # логирование, нужно перенести на телегу (?)
            cursor.execute(f'''INSERT INTO db_tinderbot.matches 
                                (match_id, person_id, date, last_msg_id, msg_count) 
                                VALUES (\'{match_id}\', \'{client.id}\', \'{match['created_date']}\', 1, 2)''')
            sleep(3)
        if not go or "next_page_token" not in tmp_matches["data"]:
            break
        tmp_matches = requests.get(TINDER_URL + f"/v2/matches?count={limit_n_matches}&page_token="
                                   + tmp_matches["data"]["next_page_token"],
                                   headers={"X-Auth-Token": client.token}).json()
        page += 1
        print(f'Page {page} was opened')
    print("start writing to old_matches")
    for match_id, lst_msg_id, msg_num_old in old_matches:
        print("old match", match_id, "check")
        # ЗДЕСЬ НУЖНА ПРОВЕРКА НА НЕПРОЧИТАННОЕ СООБЩЕНИЕ, ТОЧНЕЕ НА ТО, ЧТО ЧЕЛОВЕК НАМ ОТВЕТИЛ НА ПРОШЛЫЙ ВОПРОС
        # upd: верхнее вроде сделала
        # + ЗДЕСЬ НУЖНА ЗАПИСЬ ОТВЕТА В ТАБЛИЦУ С ПОЛУЧЕННЫМИ СООБЩЕНИЯМИ
        messages = api.get_messages(match_id=match_id)

        msg_num_tmp = len(messages)
        if msg_num_old != msg_num_tmp:
            # запись полученных сообщений
            for msg in messages[msg_num_old:]:
                print("add msg", msg['from'], msg['to'], msg['message'], "to incoming messages table")
                if msg['to'] == client.id:
                    cursor.execute(f'''INSERT INTO db_tinderbot.incomingmessages
                                        (from_id, to_id, message, question_id, date)
                                        VALUES
                                        (\'{msg['from']}\', \'{msg['to']}\', \'{msg['message']}\', {lst_msg_id}, \'{msg['sent_date']}\')''')

            # отправка нового сообщения
            cursor.execute(f'''SELECT message 
                                FROM db_tinderbot.messageorder 
                                JOIN db_tinderbot.messagetemplates 
                                ON msg_id = id  
                                WHERE msg_num = {lst_msg_id + 1} AND person_id = \'{client.id}\'''') # поиск следующего вопроса
            question = cursor.fetchone()[0]
            if question is not None: # если none (значит, больше вопросов, чтобы задать нет (вроде)), то что дальше? куда передавать эту инфу
                api.write_to_id(match_id, msg=question)
                cursor.execute(f'''UPDATE db_tinderbot.matches 
                                    SET last_msg_id = {lst_msg_id + 1}
                                    WHERE match_id = \'{match_id}\'''') # увеличиваем номер последнего написанного сообщения
                cursor.execute(f'''UPDATE db_tinderbot.matches 
                                    SET msg_count = {msg_num_tmp + 1}
                                    WHERE match_id = \'{match_id}\'''')  # увеличиваем количество написанных сообщений
                print("new message to ", match_id) # логирование, нужно перенести на телегу (?)
        sleep(5)
    cursor.close()
    conn.close()
    print("END writing for", client)


def like_and_write_to_db(client, wait_sek=3, limit=10):
    # ДОБАВИТЬ ТУТ ОСТАНОВКУ ПО ОКОНЧАНИЮ ЛЮДЕЙ ДЛЯ ЛАЙКОВ
    print("START liking for", client)
    conn = psycopg2.connect(dbname='d18ei58b0f0hv7',
                             user='xlecmelfjobtes',
                             password='dcf3b17a5ff5fe2f845c24cd797d56ae072dd89359aa0966b618bcde37dc8d58',
							 host='ec2-54-154-101-45.eu-west-1.compute.amazonaws.com')
    conn.autocommit = True
    cursor = conn.cursor()
    api = TinderAPI(client.token)
    cursor.execute(f'''SELECT p.tinder_id
                        FROM db_tinderbot.antipathy a INNER JOIN db_tinderbot.preferences p 
                        ON a.preference_id = p.id 
                        WHERE a.person_id = \'{client.id}\'''')
    ban_interests = set(map(lambda x: x[0], cursor.fetchall()))
    print(f'user: {client.id} \nban_interests: ' + ','.join(ban_interests))

    persons = api.nearby_persons()
    if len(persons) > limit:
        persons = persons[:limit]

    for person in persons:
        intersection = set(person.interests) & ban_interests
        if len(intersection) == 0:
            person.like()
            print('LIKE')

            cursor.execute('INSERT INTO db_tinderbot.likes (person_id, liked_person_id, date) VALUES (%s, %s, %s)',
                           (client.id, person.id, datetime.datetime.utcnow()))
            sleep(wait_sek)
            print(person)
        else:
            person.dislike()
            print("DISLIKE because of ", *intersection)
            print(person)
            sleep(wait_sek)

    conn.close()
    cursor.close()
    print("END liking for", client)


con_to_db = psycopg2.connect(dbname='d18ei58b0f0hv7',
                             user='xlecmelfjobtes',
                             password='dcf3b17a5ff5fe2f845c24cd797d56ae072dd89359aa0966b618bcde37dc8d58',
                             host='ec2-54-154-101-45.eu-west-1.compute.amazonaws.com')
cursor = con_to_db.cursor()
while True:
    cursor.execute('SELECT * FROM db_tinderbot.users')
    for client_arr in cursor:
        client = Client(client_arr)
        if client.liking:
            like_and_write_to_db(client)
        if client.writing:
            start_conversation_with_db(client, limit_pages=1)

cursor.close()
con_to_db.close()
