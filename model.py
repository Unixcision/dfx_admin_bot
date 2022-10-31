from sqlalchemy import Column, DateTime, BigInteger, String, Integer, Numeric, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv('.env')  # load main .env file
environment = os.getenv("ENVIRONMENT")
sub_env = '.env.' + environment
load_dotenv(sub_env)  # load main .env file
# Localhost url: postgresql://localhost/postgres
TELEGRAM_BOT_POSTGRES_URL = os.getenv("TELEGRAM_BOT_POSTGRES_URL")
postgres_url = TELEGRAM_BOT_POSTGRES_URL
print("POSTGRES URL", TELEGRAM_BOT_POSTGRES_URL)

'''
This model has been referenced from: https://www.pythoncentral.io/sqlalchemy-orm-examples/
'''

Base = declarative_base()


class User(Base):
    __tablename__ = 'telegram_users'
    id = Column(BigInteger, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String)
    message_count = Column(BigInteger)
    popularity = Column(BigInteger)
    reputation = Column(BigInteger)
    join_datetime = Column(DateTime, default=func.now())
    verified = Column(Boolean)
    captcha_message = Column(BigInteger)
    

class Message(Base):
    __tablename__ = 'telegram_messages'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('telegram_users.id'), nullable=False)
    message = Column(String)
    message_id = Column(BigInteger, unique=True)
    last_edit = Column(String)
    chat_id = Column(BigInteger)
    time = Column(DateTime, default=func.now())

class MessageHide(Base):
    __tablename__ = 'telegram_message_hides'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('telegram_users.id'), nullable=False)
    message = Column(String)
    time = Column(DateTime, default=func.now())


class UserBan(Base):
    __tablename__ = 'telegram_user_bans'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('telegram_users.id'), nullable=False)
    reason = Column(String)
    time = Column(DateTime, default=func.now())

class BotMessages(Base):
    __tablename__ = 'telegram_bot_messages'
    id = Column(BigInteger, primary_key=True)
    type = Column(String)
    sent_date = Column(DateTime, default=func.now())
    
class Captcha(Base):
    __tablename__ = 'telegram_bot_captcha'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('telegram_users.id'), nullable=False)
    attemps = Column(Numeric, default=3)
    solution = Column(String)   
 
class MiscData(Base):
    __tablename__ = 'misc_data'
    key = Column(String, primary_key=True)
    data = Column(String, nullable=False)    
    
class Tweets(Base):
    __tablename__ = 'tweet_urls'
    url = Column(String, primary_key=True) 
    
class UserReputation(Base):
    __tablename__ = 'telegram_user_reputation'
    owner_id = Column(BigInteger, ForeignKey('telegram_users.id'), nullable=False, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('telegram_messages.message_id'), nullable=False, primary_key=True)
    voter_id = Column(BigInteger, ForeignKey('telegram_users.id'), nullable=False, primary_key=True)

from sqlalchemy import create_engine
engine = create_engine(postgres_url)

from sqlalchemy.orm import sessionmaker
session = sessionmaker()
session.configure(bind=engine)
Base.metadata.create_all(engine)

print ("Created database model")

