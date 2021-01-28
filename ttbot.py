import os
import re
import sqlite3

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from sqlite3 import Error

db_path = 'track.db'

def sql_connection():

    try:
        con = sqlite3.connect(db_path)
        return con

    except Error:
        print(Error)

def init_db(con):
    exec_query(con, f"CREATE TABLE TIMETRACK(user text, StartTime date, FinishTime date)")

def exec_query(con, query):
    cursorObj = con.cursor()
    cursorObj.execute(query)
    con.commit()
    con.close()

def record_start_time(con, user):
    exec_query(con, f"INSERT INTO TIMETRACK(user, StartTime) VALUES('{user}', datetime('now'))")

def record_finish_time(con, user):
    exec_query(con, f"UPDATE TIMETRACK SET FinishTime=datetime('now') WHERE rowid=(SELECT rowid FROM TIMETRACK WHERE user = '{user}' AND FinishTime IS NULL ORDER BY StartTime DESC LIMIT 1 )")

def get_stats(ack, con, startPeriod, endPeriod):
    cursorObj = con.cursor()
    cursorObj.execute(f"SELECT user, (Cast (( SUM(JulianDay(FinishTime) - JulianDay(StartTime))) * 24 * 60 * 60 As Integer)/3600) || ':' || strftime('%M:%S', Cast ((SUM(JulianDay(FinishTime) - JulianDay(StartTime))) * 24 * 60 * 60 As Integer)/86400.0) AS Time FROM TIMETRACK GROUP BY user")
    rows = cursorObj.fetchall()
    for row in rows:
        result = client.users_info(
                user=row[0]
        )
        ack(f"{result['user']['real_name']} \t {row[1]}")

def acknowledge(message, say):
    response = f"Хорошо, <@{message['user']}>!"
    if 'thread_ts' in message.keys():
        say(text=response, thread_ts=message['thread_ts'])
    else:
        say(response)

if not os.path.isfile(db_path):
    init_db(sql_connection())

app = App(token=os.environ["SLACK_BOT_TOKEN"])
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.command("/start")
def start_command(ack, body):
    user_id = body["user_id"]
    record_start_time(sql_connection(),message['user'])
    ack(f"Хорошо, <@{user_id}>!")

@app.command("/stop")
def start_command(ack, body):
    user_id = body["user_id"]
    record_finish_time(sql_connection(),message['user'])
    ack(f"Хорошо, <@{user_id}>!")

@app.command("/stats")
def stats_command(ack, body):
    get_stats(ack,sql_connection(),0,0)

@app.event("app_mention")
def event_test(say):
    say("Привет! Я тут!")

@app.message(re.compile("(В работе|Начал|Возобнов)", re.IGNORECASE))
def message_okay_start(message, say):
    acknowledge(message, say)
    record_start_time(sql_connection(),message['user'])

@app.message(re.compile("(Перерыв|закончил)", re.IGNORECASE))
def message_okay_finish(message, say):
    acknowledge(message, say)
    record_finish_time(sql_connection(),message['user'])

if name == "main":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
