import os
import re
import sqlite3

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


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
    exec_query(con, f"INSERT INTO TIMETRACK(user, StartTime) VALUES('{user}', datetime('now','localtime'))")

def record_finish_time(con, user):
    exec_query(con, f"UPDATE TIMETRACK SET FinishTime=datetime('now','localtime') WHERE rowid=(SELECT rowid FROM TIMETRACK WHERE user = '{user}' AND FinishTime IS NULL ORDER BY StartTime DESC LIMIT 1)")

def record_finish_time_user(con, user, time):
    exec_query(con, f"UPDATE TIMETRACK SET FinishTime=datetime(date(StartTime,'localtime')||' {time}') WHERE rowid=(SELECT rowid FROM TIMETRACK WHERE user = '{user}' AND FinishTime IS NULL ORDER BY StartTime DESC LIMIT 1)")

def get_stats(ack, con, startPeriod, endPeriod):
    cursorObj = con.cursor()
    cursorObj.execute(f"SELECT user, (Cast (( SUM(JulianDay(FinishTime) - JulianDay(StartTime))) * 24 * 60 * 60 As Integer)/3600) || ':' || strftime('%M:%S', Cast ((SUM(JulianDay(FinishTime) - JulianDay(StartTime))) * 24 * 60 * 60 As Integer)/86400.0) AS Time FROM TIMETRACK WHERE StartTime > date('now','localtime','weekday 5', '-7 days') GROUP BY user")
    rows = cursorObj.fetchall()
    stats = ''
    for row in rows:
        stats += f"<@{row[0]}>\t{row[1]}\n"
    ack(stats)

def acknowledge(message, say):
    response = f"Хорошо, <@{message['user']}>!"
    if 'thread_ts' in message.keys():
        say(text=response, thread_ts=message['thread_ts'])
    else:
        say(response)

if not os.path.isfile(db_path):
    init_db(sql_connection())

# Install the Slack app and get xoxb- token in advance
app = App(token=os.environ["SLACK_BOT_TOKEN"])


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


@app.message(re.compile(r'(закончил)(а)?\s+(в)\s+\d{2}[-,:,.]\d{2}', re.IGNORECASE))
def message_okay_finish_user(message, say):
    p = re.compile(r'\d{2}[-,:,.]\d{2}')
    time = p.findall(message['text'])
    time = re.sub(r'[-,.]', r':', time[0])
    acknowledge(message, say)
    record_finish_time_user(sql_connection(), message['user'], time)

@app.message(re.compile("(Перерыв|закончил)", re.IGNORECASE))
def message_okay_finish(message, say):
    acknowledge(message, say)
    record_finish_time(sql_connection(),message['user'])

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
