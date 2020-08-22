import requests
import json
import time
from bs4 import BeautifulSoup

headers = {
    'authority': 'osu.ppy.sh',
    'accept': '*/*;q=0.5, text/javascript, application/javascript, application/ecmascript, application/x-ecmascript',
    'x-requested-with': 'XMLHttpRequest',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://osu.ppy.sh',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://osu.ppy.sh/home',
    'accept-language': 'en-US,en;q=0.9,tr-TR;q=0.8,tr;q=0.7',
}

session = requests.Session()


def get_user_detail(user_id):
    user_page = requests.get(
        f"https://osu.ppy.sh/users/{user_id}").content

    soup = BeautifulSoup(user_page, "html.parser")
    details = json.loads(soup.find(id="json-user").string)

    return details


def add_friend(user_id):
    time.sleep(5)
    new_friend_list = session.post(
        f"https://osu.ppy.sh/home/friends?target={user_id}", headers=headers)

    if new_friend_list.status_code == 200:
        return new_friend_list.json()
    elif new_friend_list.status_code == 429:
        print(f"Waiting: 10 sec")
        print(new_friend_list.headers)
        time.sleep(10)

        new_friend_list = session.post(
            f"https://osu.ppy.sh/home/friends?target={user_id}", headers=headers)

        return new_friend_list.json()
    else:
        if verify_email():
            new_friend_list = session.post(
                f"https://osu.ppy.sh/home/friends?target={user_id}", headers=headers)

            return new_friend_list.json()


def verify_email():
    verify_token = input("Key in mail:")
    status = session.post("https://osu.ppy.sh/home/account/verify",
                          data={"verification_key": verify_token}, headers=headers).status_code

    if not status == 200:
        print("Check if the key is correct.")
        verify_email()

    return True


def update_headers():
    page = session.get("https://osu.ppy.sh/home/friends").content
    soup = BeautifulSoup(page, "html.parser")
    token_after_login = soup.find(
        name="meta", attrs={"name": "csrf-token"})["content"]

    headers['X-CSRF-Token'] = token_after_login


def get_token():
    page = session.get("https://osu.ppy.sh/home").content
    soup = BeautifulSoup(page, "html.parser")
    token = soup.find(name="meta", attrs={"name": "csrf-token"})["content"]

    return token


def get_first_friend_list():
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            friend_list_config = json.loads(file.read())["friends_json"]

        print([friend_id["target_id"] for friend_id in friend_list_config])
        return [friend_id["target_id"] for friend_id in friend_list_config]
    except:
        resp = session.get("https://osu.ppy.sh/home/friends")
        soup = BeautifulSoup(resp.content, "html.parser")

        if resp.status_code != 200:
            print("Looks like you had to do verification. I guess??")
            verify_email()

        soup = BeautifulSoup(resp.content, "html.parser")
        friends_json = json.loads(soup.find(id="json-users").string)

        return [friend_id["id"] for friend_id in friends_json]


def get_config():
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            return json.loads(file.read())
    except FileNotFoundError:
        print("Generating new config file")
        username = input("Username:")
        password = input("Password:")
        with open("config.json", "w", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "username": username,
                        "password": password,
                        "country": ["TR"],
                        "start_from_page": 1,
                        "page_limit": 200
                    }, indent=4
                )
            )
        with open("config.json", "r", encoding="utf-8") as file:
            return json.loads(file.read())


def login(username, password):
    data = {
        '_token': get_token(),
        'username': username,
        'password': password
    }

    status = session.post('https://osu.ppy.sh/session',
                          headers=headers, data=data).status_code

    if status != 200:  # If can't login
        print("Cant Login")
        login(username, password)
        with open("log.txt", "a", encoding="utf-8") as file:
            file.write(f"Cant Login status code: {status} \n")


def main():
    configs = get_config()
    login(configs["username"], configs["password"])
    update_headers()
    first_friend_list = get_first_friend_list()

    for country in configs['country']:
        print(f"Country: {country}")

        for page_count in range(configs['start_from_page'], configs['page_limit'] + 1):
            print(f"Page: {page_count}")

            country_url_page = requests.get(
                f"https://osu.ppy.sh/rankings/osu/performance?country={country}&page={page_count}").content
            soup = BeautifulSoup(country_url_page, "html.parser")

            # users
            for user in soup.find_all(class_="ranking-page-table__user-link-text js-usercard"):
                user_id = int(user['data-user-id'])

                if user_id in first_friend_list:
                    print(f"Skipping {user_id}")
                    continue

                print(f"Checking {user_id}")
                for friend in add_friend(user_id):  # friend list after edded
                    if user_id == friend["target_id"]:  # find the user in list
                        if str(friend['mutual']) == "True":  # check if mutual
                            print(f"Found Mutual: {user_id}")
                            with open("mutuals.txt", "a") as file:
                                file.write(
                                    f"{user_id} - {get_user_detail(user_id)['username']} \n")
                            break
                        else:
                            session.delete(
                                f"https://osu.ppy.sh/home/friends/{user_id}", headers=headers)
                            break


if __name__ == "__main__":
    main()
