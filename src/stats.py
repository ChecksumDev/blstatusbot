from datetime import datetime, timedelta


HOURLY_SCORES = []
HOURLY_USERS = {}
HOURLY_MAPS = {}

def score_add():
    HOURLY_SCORES.append(datetime.utcnow())
    HOURLY_SCORES[:] = [score for score in HOURLY_SCORES if score > datetime.utcnow() - timedelta(hours=1)]

def user_add(user_id: int):
    if user_id in HOURLY_USERS:
        HOURLY_USERS[user_id].append(datetime.utcnow())
    else:
        HOURLY_USERS[user_id] = [datetime.utcnow()]

    HOURLY_USERS[user_id][:] = [score for score in HOURLY_USERS[user_id] if score > datetime.utcnow() - timedelta(hours=1)]

def map_add(map_id: int):
    if map_id in HOURLY_MAPS:
        HOURLY_MAPS[map_id].append(datetime.utcnow())
    else:
        HOURLY_MAPS[map_id] = [datetime.utcnow()]

    HOURLY_MAPS[map_id][:] = [score for score in HOURLY_MAPS[map_id] if score > datetime.utcnow() - timedelta(hours=1)]
