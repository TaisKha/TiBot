import datetime
from geopy.geocoders import Nominatim
import requests
import pandas as pd
import time
import psycopg2

my_token = "84ec8546-985d-4fa0-abb9-0b5b4dea3e6e"
#my_id = "5eaf2cc8edc8f10100910b94" #Kira's ID
my_id = "5f03999449d33d01001a1c3c" # Taya's ID


TINDER_URL = "https://api.gotinder.com"
geolocator = Nominatim(user_agent="auto-tinder")
PROF_FILE = "./images/unclassified/profiles.txt"


class Person(object):
    def __init__(self, data, api, interests = None):
        self._api = api
        self.id = data["_id"]
        self.name = data.get("name", "Unknown")
        self.bio = data.get("bio", "")
        self.interests = dict() if interests == None else {x["id"] : x["name"] for x in interests}
        self.distance = data.get("distance_mi", 0) / 1.60934
        self.birth_date = datetime.datetime.strptime(data["birth_date"], '%Y-%m-%dT%H:%M:%S.%fZ') if data.get(
            "birth_date", False) else None
        self.gender = ["Male", "Female", "Unknown"][data.get("gender", 2)]
        self.images = list(map(lambda photo: photo["url"], data.get("photos", [])))
        self.jobs = list(
            map(lambda job: {"title": job.get("title", {}).get("name"), "company": job.get("company", {}).get("name")}, data.get("jobs", [])))
        self.schools = list(map(lambda school: school["name"], data.get("schools", [])))
        if data.get("pos", False):
            self.location = geolocator.reverse(f'{data["pos"]["lat"]}, {data["pos"]["lon"]}')

    def __repr__(self):
        return f"{self.id}  -  {self.name} ({self.birth_date.strftime('%d.%m.%Y')})"

    def __eq__(self, other):
        return str(self.id) == str(other.id)

    def __hash__(self):
        return hash(self.id)

    def like(self):
        return self._api.like(self.id)

    def dislike(self):
        return self._api.dislike(self.id)

#     def write(self, msg):
#         return self._api.write_to_id(self.id, msg)

# На самом деле наша API-обертка - это не более, чем причудливый способ вызова Tinder API с использованием нашего класса:


class TinderAPI:

    def __init__(self, token):
        self._token = token

    def profile(self):
        data = requests.get(TINDER_URL + "/v2/profile?include=account%2Cuser", headers={"X-Auth-Token": self._token}).json()
        return Person(data["data"]["user"], self)

    def matches(self, limit=10):
        data = requests.get(TINDER_URL + f"/v2/matches?count={limit}", headers={"X-Auth-Token": self._token}).json()
        return list(map(lambda match: Person(match["person"], self), data["data"]["matches"]))

    def matches_with_match_id(self, limit=10):
        data = requests.get(TINDER_URL + f"/v2/matches?count={limit}", headers={"X-Auth-Token": self._token}).json()
        return list(map(lambda match: {"person" : Person(match["person"], self), "match_id" : match["_id"]}, data["data"]["matches"]))

    def like(self, user_id):
        data = requests.get(TINDER_URL + f"/like/{user_id}", headers={"X-Auth-Token": self._token}).json()
        #print(data)
        return data
#         return {
#             "is_match": data["match"],
#             "liked_remaining": data["likes_remaining"]
#         }

    def dislike(self, user_id):
        data = requests.get(TINDER_URL + f"/pass/{user_id}", headers={"X-Auth-Token": self._token}).json()
        print(data)
        return True

    def write_to_id(self, match_id, msg):
            response = requests.post(TINDER_URL + f"/user/matches/{match_id}", data={"message": msg},
                                     headers={"X-Auth-Token": self._token})
            return response

    def nearby_persons(self):
        data = requests.get(TINDER_URL + "/v2/recs/core?", headers={"X-Auth-Token": self._token}).json()
#       print(data["data"]["results"][0].keys()) # позволяет посмотреть какие ключи в словаре с данными есть у каждого user поблизости
        def interests_info(user): # иногда у пользователя может не существовать ключа experiment info (видимо когда он не выбрал интересы)
            info = user.get("experiment_info", None)
            if info == None:
                return info
            else:
                return info["user_interests"]["selected_interests"]
        return list(map(lambda user: Person(user["user"], self, interests_info(user)), data["data"]["results"]))

    def get_messages(self, match_id, count=10):
        data = requests.get(TINDER_URL + f"/v2/matches/{match_id}/messages?locale=ru&count={count}", headers={"X-Auth-Token": self._token}).json()
        return list(data["data"]["messages"])

    def convert_user_messages_to_table(self, user_id, count=100):
        messages = self.get_messages(user_id, count)
        cols_to_keep = ['_id', 'sent_date', 'message', 'to', 'from']
        df = pd.DataFrame.from_records(messages, columns=cols_to_keep)
        df.rename(columns={"_id": "message_id", "sent_date": "sent_date", "message": "message", "to": "to", "from": "from"}, inplace=True)
        df.to_csv(f'messages_{user_id}.csv')
        print(df)
        
    def interests_available(self, loc='ru'): #возвращает словарь {id of interest: name of interest}
        data = requests.get(TINDER_URL + f"/v2/profile?locale={loc}&include=account%2Cuser", headers={"X-Auth-Token": self._token}).json()
#         return list(data["data"]["user"]["user_interests"]["available_interests"])
        return {elem[0]: elem[1] for elem in(map(lambda x: (x["id"], x["name"]), data["data"]["user"]["user_interests"]["available_interests"]))}



# n_matches - сколько мэтчей будет рассматривать
def start_conversation(token, n_matches):
    api = TinderAPI(token)
    my_id = api.profile().id
    # print(*api.matches_with_match_id(10), sep='\n')
    matches = api.matches_with_match_id(n_matches)
    id_name = {x['match_id']: x['person'].name for x in matches} # найти по id имя человека
    print(id_name)
    num_messages = {x['match_id']: len(api.get_messages(match_id=x['match_id'])) for x in matches} #найти по id кол-во сообщений в переписке

    # print(*num_messages.items(), sep='\n')

    init_msg = "Привет, "
    question = ["Хотела бы сразу узнать. Отношения или секс на одну ночь?", "Поняла. А чаще принимаешь себя или алкоголь)?"]
    ids = {}
    question_num = 0
    # пишем первые два сообщения
    for id_, name in id_name.items():
        if num_messages[id_] < 2:
            question_num = 0 #пока не задали ни одного вопроса
            api.write_to_id(id_, msg=init_msg+name+"!")
            api.write_to_id(id_, msg=question[question_num])
            question_num += 1 #задали первый вопрос из нашего списка
            ids[id_] = question_num
            num_messages[id_] += 2
            print(id_, name, num_messages[id_])

    # пишем все остальные сообщения
    i = -1
    while ids:
        i = (i + 1) % len(ids)
        id_ = list(ids.keys())[i]
        question_num = ids[id_]
        current_chat_length = len(api.get_messages(match_id=id_))
        if question_num == len(question):
            api.convert_user_messages_to_table(id_, count=100)
            print(ids.pop(id_, "id not found"))

        elif current_chat_length > num_messages[id_]:
            api.write_to_id(id_, msg=question[question_num]) #задаем следующий вопрос
            print(f"question asked: '{question[question_num]}' id: {id_} name: {id_name[id_]}")
            question_num += 1 #
            ids[id_] = question_num #зафиксировали в словаре, что был задан следующий вопрос
            num_messages[id_] = current_chat_length + 1 #обновили кол-во сообщений
        time.sleep(5)


def like_and_write_to_file(token, filename, wait_sek):
    api = TinderAPI(token)
    with open(filename, "w") as fout:
        while True:
            persons = api.nearby_persons()
            for person in persons:
                person.like()
                print(person.id, datetime.datetime.utcnow(), file=fout, flush=True)
                time.sleep(wait_sek)
                print(person)


def like_to_match_conversion(token, filename_with_likes, filename_with_matches, limit):
    with open(filename_with_matches, "w") as fout:
        with open(filename_with_likes, "r") as fin:
            likes = dict()
            for line in fin.readlines():
                likes[line[:24]] = line[24:-1]
        matches = requests.get(TINDER_URL + f"/v2/matches?count={limit}",
                               headers={"X-Auth-Token": token}).json()
        while True:
            if "next_page_token" not in matches["data"]:
                break
            matches = requests.get(
                TINDER_URL + f"/v2/matches?count={limit}&page_token=" + matches["data"]["next_page_token"],
                headers={"X-Auth-Token": token}).json()
            for i in range(len(matches["data"]["matches"])):
                match_id = matches["data"]["matches"][i]["_id"][24:]
                if match_id == my_id:
                    match_id = matches["data"]["matches"][i]["_id"][:24]
                if match_id in likes:
                    print(match_id, likes[match_id],
                          matches["data"]["matches"][i]["created_date"],
                          file=fout, flush=True)


def check_and_add(nb_people, all_interests): # добавление нового интереса в словарь, если его не существует
    for person in nb_people:
        interests = list(person.interests.keys())
        for interest_id in interests:
            if not all_interests.get(interest_id, None):
                all_interests[interest_id] = person.interests[interest_id] # добавили новый интерес
                print('added :',interest_id, person.interests[interest_id]) # выводим сообщение, что добавили новый интерес


 # def like_or_dislike_because_of_interests(token):
 #     api = TinderAPI(token)
 #     all_interests = api.interests_available() # словарь со всеми интересами {interest id: interest name}
 #     nb = api.nearby_persons()
 #
 #     check_and_add(nb, all_interests) # проверяем все ли интересы существуют в all_interests, если нет, то добавляем
 #
 #     ban_interests = {'it_7', 'it_88', 'it_2050', 'it_2006', 'it_2010'} #задаем множество интересов, которые нас не устраивают
 #     print("banned interests : ", *map(lambda x: all_interests[x], ban_interests)) # выводим сообщение с запрещенными интересами
 #
 #     for person in nb:
 #         intersection = set(person.interests) & ban_interests
 #         if len(intersection) == 0:
 #             print("like")
 #         else:
 #             print("dislike because of ", *map(lambda x: all_interests[x], intersection))

#like_and_write_to_file(my_token, "likess.txt", 3)
#like_to_match_conversion(my_token, "likess.txt", "matchess.txt", 3)
#start_conversation(my_token, 60)
#like_or_dislike_because_of_interests(my_token)
#print("The end")

