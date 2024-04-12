import mysql.connector
import pycurl_requests as requests
from bs4 import BeautifulSoup
import time
import datetime
#import json
import os
from dotenv import load_dotenv

# load .env file
load_dotenv()


def init_db():  # Initialise Database with mysql.connector
    return mysql.connector.connect(
        host=os.environ.get("DATABASE_HOST"),
        user=os.environ.get("DATABASE_USER"),
        password=os.environ.get("DATABASE_PASSWORD"),
        database=os.environ.get("DATABASE_ID"))


db = init_db()


def get_cursor():  # Get cursor if one doesn't already exist
    global db
    try:
        db.ping(reconnect=True, attempts=3, delay=5)
    except mysql.connector.Error as err:
        # reconnect your cursor as you did in __init__ or wherever
        db = init_db()
    return db.cursor()


# Base URL
default_url = "https://www.hyunsdojo.com/community/viewforum.php?"

# URL extensions
search_links = [
    # "73&attr_id=15",  # written_duel_official
    "73",  # written_duel
    "81",  # comic_duel
    "49",  # anim_duel
    "51",  # anim_duel_official
    "82",  # comic_duel_official
    "71",  # written_duelist
    "79",  # comic_duelist
    "47",  # anim_duelist
    "72",  # written_duelist_official
    "80",  # comic_duelist_official
    "48",  # anim_duelist_official
    "61",  # faction_nw
    "62",  # faction_sw
    "68",  # faction_ne
    "69",  # faction_ne
    "64"  # dojo_duels_general
]

# Pages to ignore (May not be needed)
ignore_links = [
    "./viewtopic.php?f=49&t=6181",
    "./viewtopic.php?f=47&t=6678",
    "./viewtopic.php?f=51&t=6204",
    "./viewtopic.php?f=48&t=6180",
    "./viewtopic.php?f=47&t=6178",
    "./viewtopic.php?f=79&t=24094",
    "./viewtopic.php?f=80&t=24093",
    "./viewtopic.php?f=81&t=24095",
    "./viewtopic.php?f=82&t=24096",
    "./viewtopic.php?f=71&t=23267",
    "./viewtopic.php?f=71&t=23265",
    "./viewtopic.php?f=72&t=23299",
    "./viewtopic.php?f=73&t=23266"
]

# tbl of months
months = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
# dict of am/pm hours added
AM_PM = {"am": 0, "pm": 12}

# Search headers to disguise the scraper
headers = {
    'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.3'
}

bool_bin = {"True": 1, "False": 0}
def bool_to_bin(bool): return bool_bin[str(bool)]


# Convert dojo site format to SQL format
def dojo_date(date):
    date = date.replace(",", "")
    date = date.split(" ")

    if (date[0] == "Today" or date[0] == "Yesterday"):
        if date[0] == "Today":
            output_date = datetime.date.today()
        else:
            output_date = datetime.date.today() - datetime.timedelta(days=1)
        output_date = output_date.strftime("%y-%m-%d")
        time = date[1].split(":")
        output_date = output_date + " " + \
            str(int(time[0])+AM_PM[date[2]]) + ":" + str(time[1]) + ":00"
    elif date[0] in months:
        output_date = date[2]
        try:
            output_date = output_date + "-" + \
                str(0.01*months.index(date[0])+1)[2:]
        except:
            print(date)
        placeholder = "0" if len(date[1][:-2]) <= 1 else ""
        output_date = output_date + "-" + placeholder + date[1][:-2]
        time = date[3].split(":")
        output_date = output_date + " " + \
            str(int(time[0])+AM_PM[date[4]]) + ":" + str(time[1]) + ":00"
    else:
        output_date = datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S")

    return output_date


def remove_dupes(init_list):  # Remove duplicate dictionaries from list of dictionaries
    res_list = []
    for i in range(len(init_list)):
        if init_list[i] not in init_list[i + 1:]:
            res_list.append(init_list[i])
    return res_list


def find_num(txt):  # Find number of pages
    return [int(s) for s in txt.split() if s.isdigit()][0]


# Store forum of each page along with link info and base "official" check
def write_link_info(forum, soup, official, i):
    return [[forum, item, official, search_links[i]] for item in soup.findAll("tr", {"class": "view_forum_bod"})]


# Get all link info
def get_link_info():
    result_links = []
    for i in range(len(search_links)):
        # append link extension with base url
        link = default_url+"f="+search_links[i]
        print(link)
        # request page info
        response = requests.get(link, headers=headers)
        content = response.content
        # convert page info to html info
        soup = BeautifulSoup(content, 'html.parser')
        try:
            # get forum page name
            forum = soup.find("div", {"id": "viewforum_page_header"}).find(
                "a").get_text()
            # for pages such as "Animation Duel Results" and "Comic Duelist Roster"
            official = True if ("results" in forum.lower()
                                or "roster" in forum.lower()) else False
            # Store forum of each page along with link info and base "official" check
            result_links = [*result_links, *
                            write_link_info(forum, soup, official, i)]
            # Get total number of pages
            page_num = find_num(
                soup.find('div', {"class": "view_forum_pag"}).prettify().split("</strong>")[1])
            print("get_pagenum:", page_num)

            # loop through each page
            for k in range(1, page_num):
                # request info using previous link and "&start=" + 25 * current page
                response = requests.get(link + "&start=" +
                                        str(25 * k),
                                        headers=headers)
                content = response.content
                # get soup
                soup = BeautifulSoup(content, "html.parser")
                link_info = write_link_info(forum, soup, official, i)

                # if search_links[i] == "51":
                #     print(k, "search")

                # write info to table
                result_links = [*result_links, *link_info]

            # if search_links[i] == "51":
            #     print(len(result_links))

            print(f"{forum} (Page {search_links[i]}) Complete")
        except:
            print(f"{forum} (Page {search_links[i]}) Failed")
    return result_links


# Extract all link info
def format_link_info(result_links):
    link_list = []
    for link in result_links:
        # get the header with the post link
        full_link = link[1].find("a", {"class": "topictitle"})
        # get the header with the user name
        user = link[1].findNext("a").findNext("a")
        # get link to page
        link_ref = full_link.get("href")[1:]
        # Check if there's a thingy that says "recorded" or "finished"
        tag_img = link[1].find("span", {"class": "gen"})

        date = link[1].find("span", {"class": "topic_username"}).find(
            "span").find("a").find_next("a").get_text()

        try:  # if the bit with the image exists
            official = tag_img.find("img").get("alt")
            official = True if official == "Recorded" or official == "[Finished]" else False
        except:  # if the bit with the image doesn't exist
            official = link[2]

        if not official:  # can't be in voting if it's official
            try:  # if the bit with the image exists
                voting = tag_img.find("img").get("alt")
                voting = True if voting == "[Voting]" else False
            except:  # if the bit with the image doesn't exist
                voting = False
        else:
            voting = False

        info = {
            # combine default url and cleaned up link
            "link": default_url[:-15] + link_ref[:link_ref.find("&sid=")],
            "forum": link[0],  # forum title
            "forum_id": link[3],  # forum number
            "title": full_link.get_text(),  # page title
            "user": user.get_text(),  # user posted
            # convert site date to SQL formatted date
            "date": dojo_date(date),
            "official": bool_to_bin(official),  # official or not
            "voting": bool_to_bin(voting)  # voting or not
        }
        # append to list of dictionaries
        link_list.append(info)
    return link_list


# Store all code in a function
def update_database():
    # Start time (to calculate response time)
    start_time = time.time()

    # get all info
    result_links = get_link_info()
    link_list = format_link_info(result_links)

    # Remove duplicate link info
    result = remove_dupes(link_list)

    # # Write final info to json file
    # with open("duels_links.json", "w") as fout:
    #     json.dump(result, fout)

    final_list = []

    for item in result:
        new_tuple = (result.index(item), item["link"], item["forum"], item["forum_id"], " " +
                     item["title"]+" ", item["user"], item["date"], item["official"], item["voting"])
        final_list.append(new_tuple)

    # temp_counter = 0
    # for item in final_list:
    #     if item[3] == "51":
    #         temp_counter += 1
    # print(temp_counter)

    print("Download Complete")

    # """ SQL Stuff

    sql = "REPLACE INTO dojo_links (id, link, forum, forum_id, title, user, date, official, voting) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"

    cursor = get_cursor()

    # cursor.execute("DROP TABLE dojo_links")
    # cursor.execute("CREATE TABLE dojo_links (id INT, link VARCHAR(255) PRIMARY KEY, forum VARCHAR(255), forum_id INT, title VARCHAR(255), user VARCHAR(255), date DATETIME, official INT(1), voting INT(1))")

    print("Database connected")

    cursor.executemany(sql, final_list)

    db.commit()

    print("Upload Complete")

    update_time()

    # Give response time
    print("Response time:", round(time.time()-start_time, 4))
    # """


def update_time():
    with open("./last_update.txt", "w") as f:
        f.write(datetime.datetime.now().strftime("%d/%m/%Y, %I:%M %p"))

# Actual code
# update_database() # Run once


# Run indefinitely
while True:
    update_database()
    time.sleep(60*15)
