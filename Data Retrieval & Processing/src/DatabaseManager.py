import sqlalchemy
import sys
from sqlalchemy import Column, Text, Integer, REAL, DateTime, select, text, bindparam, and_, cast, Date, any_, or_
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime, timedelta, date
from server import get_socketio_instance
import logger as log
import configuration
from SentimentAnalyser import SentimentAnalyser

__socketio = get_socketio_instance()

__config = configuration.get_config()
__connection_string = __config.generate_connection_string()
print(__connection_string)

__analyser = SentimentAnalyser()

__db = sqlalchemy.create_engine(__connection_string)
__engine = __db.connect()
__meta = sqlalchemy.MetaData(__engine)

# Define table schemas
__scotland_tweets = sqlalchemy.Table("scotland_tweets", __meta,
                                     Column('id', Integer, primary_key=True),
                                     Column('place', JSONB),
                                     Column('text', Text),
                                     Column('date', DateTime),
                                     Column('user', JSONB),
                                     Column('neg_sent', REAL),
                                     Column('neu_sent', REAL),
                                     Column('pos_sent', REAL),
                                     Column('compound_sent', REAL),
                                     Column('text_sentiments', ARRAY(REAL)),
                                     Column('text_sentiment_words', ARRAY(Text)),
                                     Column('area_id', Text),
                                     Column('ward_id', Text),
                                     Column('coordinates', Text))

# Creates tables if they don't already exist
__meta.create_all()


def save_scotland_tweet(tweet):
    if 'extended_tweet' in tweet:
        full_text = tweet.get('extended_tweet').get('full_text')
    else:
        full_text = tweet.get('text')

    # Tweet date & time
    float_ts = int(tweet.get('timestamp_ms')) / 1000
    date = datetime.fromtimestamp(float_ts)

    # Tweet sentiment scores
    sentiment_text = ' '.join(
        list(filter(lambda word: not word.startswith(('@', 'http://', 'https://', '&')), full_text.split(' '))))
    scores = __analyser.calculate_sentiment_scores(sentiment_text)
    sentiment_words = [word.lower() for word in __analyser.get_sentiment_words(sentiment_text)]
    sentiment_word_scores = __analyser.get_sentiment_word_scores(sentiment_text)

    if tweet.get('coordinates'):
        coord_array = tweet.get("coordinates").get("coordinates")
        coord_string = "(" + str(coord_array[1]) + "," + str(coord_array[0]) + ")"
        wkt_coords = "POINT(" + str(coord_array[0]) + " " + str(coord_array[1]) + ")"
    else:
        coord_string = None
        coord_array = tweet.get("place").get("bounding_box").get("coordinates")[0]

        if tweet.get('place').get('name') != 'Scotland':
            wkt_coords = 'POLYGON((' + ', '.join(map(lambda x: str(x[0]) + " " + str(x[1]), coord_array)) + ', ' + str(
                coord_array[0][0]) + ' ' + str(coord_array[0][1]) + '))'
        else:
            wkt_coords = None

    try:
        area_id = __engine.execute(
            text("select id " +
                 "from scotland_districts " +
                 "where ST_Contains(area, ST_Centroid(ST_GeomFromText('" + wkt_coords + "', 4326)))")
        ).fetchone()[0]
    except TypeError as e:
        area_id = None

    if coord_string is not None:
        try:
            ward_id = __engine.execute(
                text("select id " +
                     "from scotland_wards " +
                     "where ST_Contains(area, ST_Centroid(ST_GeomFromText('" + wkt_coords + "', 4326)))")
            ).fetchone()[0]
        except TypeError as e:
            ward_id = None
    else:
        ward_id = None

    if area_id is not None:
        __socketio.emit('district_geo_tweet', {
            'text': full_text,
            'user': tweet.get("user"),
            'ward': area_id,
            'coordinates': coord_array,
            'score': scores.get('compound'),
            'text_sentiments': sentiment_word_scores,
            'text_sentiment_words': sentiment_words
        })

    if ward_id is not None:
        __socketio.emit('ward_geo_tweet', {
            'text': full_text,
            'user': tweet.get("user"),
            'ward': ward_id,
            'coordinates': coord_array,
            'score': scores.get('compound'),
            'text_sentiments': sentiment_word_scores,
            'text_sentiment_words': sentiment_words
        })

    statement = __scotland_tweets.insert().values(
        place=tweet.get("place"),
        text=full_text,
        date=date,
        coordinates=coord_string,
        user=tweet.get("user"),
        neg_sent=scores.get('neg'),
        neu_sent=scores.get('neu'),
        pos_sent=scores.get('pos'),
        compound_sent=scores.get('compound'),
        text_sentiments=sentiment_word_scores,
        text_sentiment_words=sentiment_words,
        area_id=area_id,
        ward_id=ward_id
    )

    __engine.execute(statement)

    # logger.info(json.dumps(tweet, indent=4, sort_keys=True))
    # log.logger.info("added to scotland_tweets")
    # print("added to scotland tweets")
    # sys.stderr.write('added to scotland tweets \n')
    # print(tweet)


def get_scotland_district_tweets(area_ids, group, date, period):
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    if period is None:
        period = 3

    end_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)
    start_date = end_date - timedelta(days=int(period))

    sql = text("""
      SELECT t.text, t.user, x.day, x.avg_neg, x.avg_neu, x.avg_neg, x.avg_pos, x.avg_compound, x.total, t.text_sentiments,
      t.text_sentiment_words, t.{0}_id
      FROM scotland_tweets as t        
         INNER JOIN (
            SELECT date::date as day, MAX(date) as max_date, AVG(neg_sent) as avg_neg, AVG(neu_sent) as avg_neu,
              AVG(pos_sent) as avg_pos, AVG(compound_sent) as avg_compound, COUNT(*) as total
            FROM scotland_tweets
            WHERE {0}_id = ANY(:ids)
            AND date > {1}
            AND date <= {2}
            AND compound_sent != 0
            GROUP by day, {0}_id 
            ORDER BY day ASC
           ) as x ON t.date = x.max_date
        ORDER BY x.day ASC;
        """.format(group, "'" + start_date.strftime('%Y-%m-%d') + "'", "'" + end_date.strftime('%Y-%m-%d') + "'"))

    return __engine.execute(sql, {'ids': area_ids})


def get_scotland_district_common_words(ids, group, rdate, period):
    if rdate is None:
        rdate = datetime.now().strftime('%Y-%m-%d')
    if period is None:
        period = 3

    end_date = datetime.strptime(rdate, '%Y-%m-%d') + timedelta(days=1)
    start_date = end_date - timedelta(days=int(period))

    sql = text("""
          SELECT t.{0}_id as group_id, array_agg(word ||', ' || word_ct::text) word_arr
          FROM (
            SELECT {0}_id, word, count(*) word_ct
            FROM   scotland_tweets, unnest(text_sentiment_words, text_sentiments) AS u(word, word_score)
            WHERE  date > {1}
            AND    date <= {2}
            AND compound_sent != 0
            AND {0}_id = ANY(:ids)
            GROUP  BY word, {0}_id
            ORDER  BY {0}_id, count(*) DESC, word
          ) t
        GROUP BY t.{0}_id
    """.format(
        group,
        "'" + start_date.strftime('%Y-%m-%d') + "'",
        "'" + end_date.strftime('%Y-%m-%d') + "'"
        )
    )

    return __engine.execute(sql, {'ids': ids})


def get_scotland_tweets(date, period):
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    if period is None:
        period = 3

    end_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)
    start_date = end_date - timedelta(days=int(period))

    sql = text("""
      SELECT t.text, t.user, x.day, x.avg_neg, x.avg_neu, x.avg_neg, x.avg_pos, x.avg_compound, x.total, t.text_sentiments,
      t.text_sentiment_words
      FROM scotland_tweets as t 
         INNER JOIN (
            SELECT date::date as day, MAX(date) as max_date, AVG(neg_sent) as avg_neg, AVG(neu_sent) as avg_neu,
              AVG(pos_sent) as avg_pos, AVG(compound_sent) as avg_compound, COUNT(*) as total
            FROM scotland_tweets
            WHERE area_id IS NOT NULL
            AND date > {0}
            AND date <= {1}
            AND compound_sent != 0
            GROUP by day
            ORDER BY day ASC
         ) as x ON t.date = x.max_date
      ORDER BY x.day ASC;
      """.format("'" + start_date.strftime('%Y-%m-%d') + "'", "'" + end_date.strftime('%Y-%m-%d') + "'"))

    return __engine.execute(sql)


def get_scotland_common_words(rdate, period):
    if rdate is None:
        rdate = datetime.now().strftime('%Y-%m-%d')
    if period is None:
        period = 3

    end_date = datetime.strptime(rdate, '%Y-%m-%d') + timedelta(days=1)
    start_date = end_date - timedelta(days=int(period))

    sql = text(""" 
          SELECT array_agg(word ||', ' || word_ct::text) word_arr
          FROM (
            SELECT word, count(*) word_ct
            FROM   scotland_tweets, unnest(text_sentiment_words, text_sentiments) AS u(word, word_score)
            WHERE  date > {0}
            AND date <= {1}
            AND compound_sent != 0
            AND area_id IS NOT NULL
            GROUP  BY word
            ORDER  BY count(*) DESC, word
          ) t""".format("'" + start_date.strftime('%Y-%m-%d') + "'", "'" + end_date.strftime('%Y-%m-%d') + "'"))

    return __engine.execute(sql)


def get_all_scotland_tweets():
    return select([
        __scotland_tweets.c.id,
        __scotland_tweets.c.text
    ])\
        .where(__scotland_tweets.c.area_id.isnot(None))\
        .execute()


def __update_tweets_sentiment(table, tweet_id, sentiment, date):
    table.update() \
        .values(
        neg_sent=sentiment.get('neg'),
        neu_sent=sentiment.get('neu'),
        pos_sent=sentiment.get('pos'),
        compound_sent=sentiment.get('compound'),
        date=date
    ).where(table.c.id == tweet_id).execute()


def update_scotland_tweets_sentiment_arrays(values):
    stmt = __scotland_tweets.update(). \
        where(__scotland_tweets.c.id == bindparam('t_id')). \
        values({
        'text_sentiments': bindparam('scores'),
        'text_sentiment_words': bindparam('words')
    })

    __engine.execute(stmt, values)


def update_scotland_tweets_sentiment(tweet_id, sentiment, date):
    __update_tweets_sentiment(__scotland_tweets, tweet_id, sentiment, date)


def get_districts_tweets(udate):
    if udate is None:
        udate = datetime.now().strftime('%Y-%m-%d')

    start_date = datetime.strptime(udate, '%Y-%m-%d')
    end_date = start_date + timedelta(days=1)
    return select([
            __scotland_tweets.c.id,
            __scotland_tweets.c.area_id.label('area'),
            __scotland_tweets.c.ward_id.label('ward'),
            __scotland_tweets.c.text,
            __scotland_tweets.c.date,
            __scotland_tweets.c.user['name'].label('name'),
            __scotland_tweets.c.compound_sent.label('score'),
            __scotland_tweets.c.text_sentiments,
            __scotland_tweets.c.text_sentiment_words
        ]).where(
            (__scotland_tweets.c.date >= start_date) &
            (__scotland_tweets.c.date < end_date) &
            (__scotland_tweets.c.area_id.isnot(None)) &
            (__scotland_tweets.c.compound_sent != 0)
        ).execute()
