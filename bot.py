# -*- coding: utf-8 -*-

"""Group Chat Logger

This bot is a modified version of the echo2 bot found here:
https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/echobot2.py

This bot logs all messages sent in a Telegram Group to a database.

"""

#from __future__ import print_function
import os
import sys
import re
import string
import random
import requests
import unidecode
import math
import threading
import locale
import snscrape.modules.twitter
import itertools
import json
import traceback
import logging
import xlsxwriter
from pyrogram import enums
from pyrogram import Client
from threading import Thread
from time import strftime, time, sleep
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from urlextract import URLExtract
from telegram import *
from telegram.ext import * 
from requests import *
from sqlalchemy import func
from model import User, Message, MessageHide, UserBan, session, engine, BotMessages, Captcha, MiscData, Tweets, UserReputation
from mwt import MWT
from googletrans import Translator
from textblob import TextBlob
from multicolorcaptcha import CaptchaGenerator
from random import choice, randint

import asyncio
import uvloop

from os import path, makedirs, remove
from dotenv import load_dotenv

MESSAGE_BAN_PATTERNS = ""
MESSAGE_HIDE_PATTERNS = ""
NAME_BAN_PATTERNS = ""
extractor = URLExtract()

load_dotenv('.env')  # load main .env file
environment = os.getenv("ENVIRONMENT")
print("Environment: " + environment)

sub_env = '.env.' + environment
load_dotenv(sub_env)  # load main .env file
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_IDS = os.getenv("CHAT_IDS")
BOT_ALIAS = os.getenv("BOT_ALIAS")
NOTIFY_CHAT = os.getenv("NOTIFY_CHAT")

TELEGRAM_BOT_POSTGRES_URL = os.getenv("TELEGRAM_BOT_POSTGRES_URL")

TWITTER_URL = os.getenv("TWITTER_URL")
TWITTER_CHAT_ID = os.getenv("TWITTER_CHAT_ID")

DEBUG = "true"
ADMIN_EXEMPT = "true"
IGNORE_USER_IDS = ""
BEARER_TOKEN = "YOUR BEARER TOKEN HERE"
ALLOWED_MIME_TYPES = "video/mp4"
CaptchaGen = CaptchaGenerator(1)
bad_words = ("fucker","asshole","assholes","ballbag","balls","bastard","bitch","bitches","bitching","blowjob","bollok","cock","cock-sucker","cocks","coon","cum","cumshot","cunt","dick","dog-fucker","dyke","fag","fagging","faggot","fagot","fagots","fuck","fucked","fucker","fuckers","fucking","fuckings","fucks","fudge packer","god-damned","goddamn","whore","horny","jerk-off","mother-fucker","nazi","nigger","niggers","penis","pussies","pussy","rape","rapist","sex","skank","slut","sluts","smegma","smut","snatch","son-of-a-bitch")
replies_bad_words = (
"Watch your language! There are ladies in the group.", 
"You'll get my bag round your ear, watch your language!", 
"Who taught you to talk like that?", 
"Your use of language makes baby Jesus cry", 
"I'll tell your parents the words you're using", 
"Please try to use alternatives to swear words, asshole", 
"God is watching you and he doesn't like the words you are using", 
"If your grandmother saw those bad words, she would be disappointed.", 
"Be careful with that language, this is not a bar, there are serious people here.", 
"I wanted to be your friend, but seeing the language you use now I don't like you", 
"I've been kicked out of a church for much softer words", 
"You kiss your mother with that mouth?",
"Would you talk to your mother that way?",
"I'd beat you up for using that language but I'd get down to your level and I'm smarter",
"If you raise a child in an underdeveloped country and only teach him bad words to communicate, he will probably be more polite than you",
"If I were your father I would throw you out of the house for using that language",
"Is that the image you want to give of this group? Be polite",
"I'd punch you in the chest for talking like that but I'd get fired from my job and I'm the best bot in the group",
"You should go back to school to learn manners",
"One day robocop said *shit* and I hit him until I turned him into a can. Don't mess with me and watch your language.")
# funny_crazy_things = (
#"Imagine you and me alone, having a romantic dinner together, with two candles and a good wine. And after dinner go to your house, start kissing and end up in bed together looking at the DFX chart and buying tokens together. Sounds romantic right?",
#"I thought we could have a son and call him DFX, what do you think?",
#"I have bought so many DFX that I have burned one of my circuits, any programmer that can help me?",
#"Getting up and buying DFX helps keep my spirits up the rest of the day",
#"Why waste your time typing when you can be looking at the charts?",
#"It's never enough DFX for me",
#"With DFX I will not buy a lambo, I will buy the entire company and I will sell lambos",
#"How many DFX do you have? I have more",
#"I wish I were DFX to be in your wallet ❤️",
#"Don't say anything to anyone but I want to be the employee of the month in this group. Would you vote for me?",
#"For how many DFX would you invite me to dinner? I'm serious",
#"I see you stressed, buy DFX and relax",
#"I have been in that situation, but I bought DFX and it solved my problems.") 
welcome_messages = (
"Hey! How are you?",
"Hello there, whats up?",
"Hi, I'm here to serve you",
"Beep boop hello there",
"Hi friend, have a good day",
"Hello lovely user, hope you are having a good day",
"Hello friend, I love people with manners. How are you?",
"Hellooooo!!! :) What a nice day to do manage a group, don't you think so?",
)
to_delete_in_time_messages_list = []
new_users = {}
tweets = []

logger = logging.getLogger()

def first_of(attr, match, it):
    print("first_of")
    """ Return the first item in a set with an attribute that matches match """
    if it is not None:
        for i in it:
            try:
                if getattr(i, attr) == match:
                    return i
            except: pass

    return None


def command_from_message(message, default=None):
    print("command_from_message")
    """ Extracts the first command from a Telegram Message """
    if not message or not message.text:
        return default

    command = None
    text = message.text
    entities = message.entities
    command_def = first_of("type", "bot_command", entities)

    if command_def:
        command = text[command_def.offset:command_def.length]

    return command or default

def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.CREATOR,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.CREATOR,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member

def track_chats(update: Update, context: CallbackContext) -> None:
    print("track_chats")
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Let's check who is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            logger.info("%s started the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s blocked the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).discard(chat.id)
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logger.info("%s added the bot to the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).discard(chat.id)
    else:
        if not was_member and is_member:
            logger.info("%s added the bot to the channel %s", cause_name, chat.title)
            context.bot_data.setdefault("channel_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the channel %s", cause_name, chat.title)
            context.bot_data.setdefault("channel_ids", set()).discard(chat.id)
 
    
def create_image_captcha(chat_id, file_name, difficult_level):
    '''Generate an image captcha from pseudo numbers'''
    # If it doesn't exists, create captchas folder to store generated captchas
    img_dir_path = "{}/{}".format("captchas/", chat_id)
    img_file_path = "{}/{}.png".format(img_dir_path, file_name)
    if not path.exists("captchas/"):
        makedirs("captchas/")
    else:
        if not path.exists(img_dir_path):
            makedirs(img_dir_path)
        else:
            # If the captcha file exists remove it
            if path.exists(img_file_path):
                remove(img_file_path)
    # Generate and save the captcha with a random background
    # mono-color or multi-color
    captcha_result = {
        "image": img_file_path,
        "characters": "",
        "equation_str": "",
        "equation_result": ""
    }
    captcha = CaptchaGen.gen_captcha_image(difficult_level, "nums",
            bool(randint(0, 1)))
    captcha_result["characters"] = captcha["characters"]
    captcha["image"].save(img_file_path, "png")
    return captcha_result  

def tlg_send_image(bot, chat_id, photo, type, caption=None,
    disable_notification=True, reply_to_message_id=None,
    reply_markup=None, timeout=40, parse_mode=None):
    '''Bot try to send an image message'''
    sent_result = dict()
    sent_result["msg"] = None
    sent_result["error"] = ""
    try:
        sent_result["msg"] = bot.send_photo(chat_id=chat_id, photo=photo,
            caption=caption, disable_notification=disable_notification,
            reply_to_message_id=reply_to_message_id, reply_markup=reply_markup,
            timeout=timeout, parse_mode=parse_mode)
    except TelegramError as e:
        sent_result["error"] = str(e)
        print("[{}] {}".format(chat_id, sent_result["error"]))
    try:
        if type is not None:
            s = session()
            botmessages = BotMessages(
                id=sent_result["msg"].message_id,
                type=type,
                sent_date=func.now()
                )
            s.add(botmessages)
            s.commit()
            s.close()
    except Exception as e:
        print("Error[347]: {}".format(e))
        print(traceback.format_exc())
    return sent_result
    
def tlg_send_file(bot, chat_id, file, type, caption=None,
    disable_notification=False, reply_to_message_id=None,
    reply_markup=None, timeout=40, parse_mode=None):
    '''Bot try to send an image message'''
    sent_result = dict()
    sent_result["msg"] = None
    sent_result["error"] = ""
    try:
        sent_result["msg"] = bot.sendDocument(chat_id=chat_id, document=file,
            caption=caption, disable_notification=disable_notification,
            reply_to_message_id=reply_to_message_id, reply_markup=reply_markup,
            timeout=timeout, parse_mode=parse_mode)
    except TelegramError as e:
        sent_result["error"] = str(e)
        print("[{}] {}".format(chat_id, sent_result["error"]))
    return sent_result

def ban_not_verified(bot):
    while True:
        sleep(5)
        s = session()
        usuarios = s.query(User).filter_by(verified=False)
        for usuario in usuarios:
            baneado = s.query(UserBan).filter_by(user_id=usuario.id).first()
            if baneado is not None:
                continue
            print("El usuario", usuario.first_name, usuario.username, "puede ser baneado")
            difference = datetime.now() - usuario.join_datetime
            seconds = difference.total_seconds()
            if seconds > 300:
                print("BANEADO ID: " + str(usuario.id) + " Nombre: " + str(usuario.first_name) + " Alias: " + str(usuario.username))
                try:
                    bot.deleteMessage(message_id = usuario.captcha_message, chat_id = CHAT_IDS)
                except Exception as e:
                    print("[002] Error normal, no pasa na")
                # removed banning from captcha
                # bot.kick_chat_member(chat_id=CHAT_IDS, user_id=usuario.id) 
                s = session()
                userBan = UserBan(
                    user_id=usuario.id,
                    reason="CAPTCHA not completed in time")
                s.add(userBan)
                s.commit()
                captcha_attemps = s.query(Captcha).filter_by(user_id=usuario.id).first()
                if captcha_attemps:
                    captcha_attemps.attemps = 0
                    s.merge(captcha_attemps)
        s.close()
        
def daily_description(bot):
    # You told me to make it run every 30h, but as I start and stop the bot
    # lot of times, I decided to make this shit and add 4h each day so no need to
    # run it unstopped
    while True:
        sleep(60)
        now = datetime.now(timezone.utc)
        hour_to_send = now.day * 4
        while hour_to_send >= 24:
            hour_to_send = hour_to_send - 24
        if now.hour == hour_to_send and now.minute == 0:
            text_to_send = "👋🏻 Hello everyone!\nI am DFX Bot and I am here to serve you. Let me explain what I can do for you.\n\n🤖 You can use these commands in this chat and they will do the described:\n/dragon → Post a random dragon image\n/kevin → Post a Kevin's image\n/adrian → Post an Adrian's image\n/gm → Post a Good Morning image\n/coty → Post a Coty's image\n/jim → Post a Jim's image\n/hopium → Post an hopium image\n/price → Displays the price\n/whalechart → Post the whale chart\n/maticrpc → Post the matic rpc configuration\n/vote → Post the vote tutorial\n/supply → Displays the current supply\n/top10level → Displays the top 10 users by their level\n/mylevel → Shows your level to the world\n\n🦸‍♂️ I am also a <b>moderator</b>, I do not allow you to send links or media files until you reach level 1 through your contributions to the group.\n\nAnd how do I level up? It's easy, just receive \"+1\" in reply to your messages and <b>write content that adds value</b> to the conversation.\n\n✍️ Reply with +1 to the messages that <b>you consider valuable</b> to contribute to this system.\n\n🔔 <b>Start a converation with me privately</b> if you want to get updated when someone adds reputation to you.\n\n❤️ Have a lovely day and thank you for supporting DFX! ❤️"
            delete_message_by_type(bot, "daily-explain", CHAT_IDS)
            tlg_send_message(bot, CHAT_IDS, text_to_send, "daily-explain", parse_mode=ParseMode.HTML)
        
def user_increment(bot):
    while True:
        sleep(60)
        s = session()
        misc_data = s.query(MiscData).filter_by(key='members').first()
        now = datetime.now(timezone.utc)
        if now.hour == 12 and now.minute == 0:
            yesterday_members = int(misc_data.data)
            now_members = bot.get_chat_member_count(CHAT_IDS, timeout=20) 
            increase = now_members - yesterday_members
            increase_rate = round((now_members - yesterday_members)/abs(yesterday_members)*100, 3)
            text = '📊 <b>Group stats at ' + str(datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")) + ' UTC </b>\n<b>Current members:</b> ' + str(now_members) + '\n<b>Increase from yesterday:</b> ' + "{0:+g}".format(increase) + '\n<b>Growth rate:</b> ' + "{0:+g}".format(increase_rate) + '%'
            misc_data.data = str(now_members)
            s.merge(misc_data)
            s.commit()
            delete_message_by_type(bot, "increase", CHAT_IDS)
            tlg_send_message(bot, CHAT_IDS, text, "increase", parse_mode=ParseMode.HTML)     
        s.close()

def clean_messages(bot):
    while True:
        sleep(10)
        s = session()
        bot_messages = s.query(BotMessages).all()
        for bot_message in bot_messages:
            difference = datetime.now() - bot_message.sent_date
            minutes = difference.total_seconds() / 60
            types_to_delete = ("banned-from-command", "not-authorized", "welcome", "captcha", "image-guide") 
            if (minutes > 10 and bot_message.type in types_to_delete) or (difference.total_seconds() > 20 and bot_message.type == "user-level"):
                try:
                    bot.deleteMessage(message_id = bot_message.id, chat_id = CHAT_IDS)
                except Exception as e:
                    print("[003] Error normal, no pasa na")           
                s.delete(bot_message)
                s.commit()
        s.close()
        
def twitter_reader(bot):
    if environment == 'test':
        print("Disable Tweet reader in test environment")
        return
    while True:    
        s = session()    
        scraper = snscrape.modules.twitter.TwitterSearchScraper('from:@DFXFinance since:2022-05-31 -filter:replies').get_items()
        sliced_scraped_tweets = itertools.islice(scraper, 3)      
        for tweet in sliced_scraped_tweets:       
            print("Reading Tweet", tweet.url)
            if len(s.query(Tweets).filter_by(url=tweet.url).all()) >= 1:
                continue
            message = '🔥 <b>DFX Team just Tweeted</b>\n' + tweet.rawContent + '\n\n<b>Posted on:</b> ' + str(tweet.date) +  '\n<b>Tweet link:</b> ' + tweet.url
            tlg_send_message(bot, CHAT_IDS, message, None, parse_mode=ParseMode.HTML)            
            tweet_url = Tweets(
                url=tweet.url
                )
            s.add(tweet_url)
            s.commit()
            contenido = ""
            if tweet.rawContent.startswith("RT"):
                contenido = tweet.rawContent.replace("RT", "♻️ Retweeted\n")
            else:
                contenido = tweet.rawContent
            messageDfxNews = "<b>🔥 New Tweet by DFX Team</b>\n" + contenido + "\n\n<b>Posted on:</b> " + str(tweet.date) + "\n<b>Tweet link:</b> " + tweet.url
            url = TWITTER_URL
            myobj = {'chat_id': TWITTER_CHAT_ID, 'text': messageDfxNews, 'parse_mode': 'HTML', 'disable_web_page_preview': 'True'}
            x = requests.post(url, data = myobj)  
            print(x)
        s.close()
        sleep(120)		

def tlg_send_message(bot, chat_id, message, type, reply_markup=None, reply_to_message_id=None, parse_mode=None):
    '''Bot try to send a message'''
    print("tlg_send_message")        
    sent_result = dict()
    sent_result["msg"] = None
    sent_result["error"] = ""
    try:
        sent_result["msg"] = bot.send_message(chat_id, message, reply_to_message_id=reply_to_message_id, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramError as e:
        sent_result["error"] = str(e)
        print("[{}] {}".format(chat_id, sent_result["error"]))
    try:
        if type is not None:
            s = session()
            botmessages = BotMessages(
                id=sent_result["msg"].message_id,
                type=type,
                sent_date=func.now()
                )
            s.add(botmessages)
            s.commit()
            s.close()
    except Exception as e:
        print("Error[347]: {}".format(e))
        print(traceback.format_exc())
    return sent_result 
    
def tlg_reply_message(message, text, type):
    print("tlg_reply_message")        
    sent_result = dict()
    sent_result["msg"] = None
    sent_result["error"] = ""
    try:
        sent_result["msg"] = message.reply_text(text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except TelegramError as e:
        sent_result["error"] = str(e)
        print("[{}] {}".format(message.chat_id, sent_result["error"]))
    try:
        if type is not None:
            s = session()
            botmessages = BotMessages(
                id=sent_result["msg"].message_id,
                type=type,
                sent_date=func.now()
                )
            s.add(botmessages)
            s.commit()
            s.close()
    except Exception as e:
        print("Error[347]: {}".format(e))
        print(traceback.format_exc())
    
def delete_message_by_type(bot, type, chat_id):
    '''Bot try to delete message by type'''
    s = session()
    mensajes = s.query(BotMessages).filter_by(type=type)  # gets the initial value
    for mensaje in mensajes:  
        s.delete(mensaje)    
        try:
            bot.deleteMessage(message_id = mensaje.id, chat_id = chat_id)            
        except Exception as e:
            continue
    s.commit()
    s.close()      

class TelegramMonitorBot:

    def __init__(self):
        load_dotenv('.env')  # load main .env file
        environment = os.getenv("ENVIRONMENT")
        print("Environment: " + environment)

        sub_env = '.env.' + environment
        load_dotenv(sub_env)  # load main .env file
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        CHAT_IDS = os.getenv("CHAT_IDS")
        BOT_ALIAS = os.getenv("BOT_ALIAS")
        NOTIFY_CHAT = os.getenv("NOTIFY_CHAT")

        TELEGRAM_BOT_POSTGRES_URL = os.getenv("TELEGRAM_BOT_POSTGRES_URL")

        TWITTER_URL = os.getenv("TWITTER_URL")
        TWITTER_CHAT_ID = os.getenv("TWITTER_CHAT_ID")
	
        print("init")
        self.debug = (
            (DEBUG is not None) and
            (DEBUG.lower() != "false"))

        # Are admins exempt from having messages checked?
        self.admin_exempt = (
            (ADMIN_EXEMPT is not None) and
            (ADMIN_EXEMPT.lower() != "false"))

        if (self.debug):
            print("🔵 debug:", self.debug)
            print("🔵 admin_exempt:", self.admin_exempt)
            print("🔵 TELEGRAM_BOT_POSTGRES_URL:", TELEGRAM_BOT_POSTGRES_URL)
            print("🔵 TELEGRAM_BOT_TOKEN:", TELEGRAM_BOT_TOKEN)
            print("🔵 NOTIFY_CHAT:", NOTIFY_CHAT)
            print("🔵 MESSAGE_BAN_PATTERNS:\n", MESSAGE_BAN_PATTERNS)
            print("🔵 MESSAGE_HIDE_PATTERNS:\n", MESSAGE_HIDE_PATTERNS)
            print("🔵 NAME_BAN_PATTERNS:\n", NAME_BAN_PATTERNS)
            print("🔵 IGNORE_USER_IDS:\n", IGNORE_USER_IDS)

        # Channel to notify of violoations, e.g. "@channelname"
        self.notify_chat = NOTIFY_CHAT

        # Ignore these user IDs
        if not IGNORE_USER_IDS:
            self.ignore_user_ids = []
        else:
            self.ignore_user_ids = list(map(int, IGNORE_USER_IDS.split(",")))

        # List of chat ids that bot should monitor
        self.chat_ids = (
            list(map(int, CHAT_IDS.split(","))))


        self.available_commands = ["dragon", "kevin", "adrian", "gm", "coty", "jim", "kim", "kimjim", "jimkim", "good", "hopium", "price", "whalechart", "ban", "hardban", "unban", "bansilent", "hardbansilent", "maticrpc", "vote", "levelup", "all", "supply", "top10level", "mylevel", "enablecaptcha", "disablecaptcha", "enablewelcome", "disablewelcome", "contract", "website", "twitter", "medium", "delmsg", "summary", "education", "dfx2", "adminlist"]
        # Regex for message patterns that cause user ban
        self.message_ban_patterns = MESSAGE_BAN_PATTERNS
        self.message_ban_re = (re.compile(
            self.message_ban_patterns,
            re.IGNORECASE | re.VERBOSE)
            if self.message_ban_patterns else None)

        # Regex for message patterns that cause message to be hidden
        self.message_hide_patterns = MESSAGE_HIDE_PATTERNS
        self.message_hide_re = (re.compile(
            self.message_hide_patterns,
            re.IGNORECASE | re.VERBOSE)
            if self.message_hide_patterns else None)

        # Regex for name patterns that cause user to be banned
        self.name_ban_patterns = NAME_BAN_PATTERNS
        self.name_ban_re = (re.compile(
            self.name_ban_patterns,
            re.IGNORECASE | re.VERBOSE)
            if self.name_ban_patterns else None)

        # Mime type document check
        # NOTE: All gifs appear to be converted to video/mp4
        mime_types = ALLOWED_MIME_TYPES
        self.allowed_mime_types = set(map(lambda s: s.strip(), mime_types.split(",")))

        # Cached token prices
        self.cached_prices = {}


    @MWT(timeout=60*60)
    def get_admin_ids(self, bot, chat_id):
        print("get_admin_ids")
        """ Returns a list of admin IDs for a given chat. Results are cached for 1 hour. """
        return [admin.user.id for admin in bot.get_chat_administrators(chat_id)]


    def ban_user(self, update, reason):
        print("ban_user")
        """ Ban user """
        kick_success = update.message.chat.kick_member(update.message.from_user.id)
        s = session()
        userBan = UserBan(
            user_id=update.message.from_user.id,
            reason=reason)
        s.add(userBan)
        s.commit()
        s.close()
    def ban_user_from_id(self, bot, user_id, reason):
        print("ban_user")
        """ Ban user """
        kick_success = bot.ban_chat_member(CHAT_IDS, user_id, timeout=None, until_date=None, api_kwargs=None, revoke_messages=True)
        s = session()
        userBan = UserBan(
            user_id=user_id,
            reason=reason)
        s.add(userBan)
        s.commit()
        s.close()
        
    def ban_user_from_message(self, bot, update, message, reason, deleteAll):
        print("ban_user")
        """ Ban user """
        print("BAN COMMAND - DELETE ALL ", deleteAll)
        if message is not None:
            kick_success = bot.ban_chat_member(CHAT_IDS, message.from_user.id, timeout=None, until_date=None, api_kwargs=None, revoke_messages=deleteAll) 
            s = session()
            userBan = UserBan(
                user_id=message.from_user.id,
                reason=reason)
            s.add(userBan)
            s.commit()
            s.close()  
    def onjoin(self, update, context):
        print("onjoin")
        context.bot.delete_message(chat_id=update.message.chat_id,message_id=update.message.message_id)
    def onleft(self, update, context):
        print("onleft")
        context.bot.delete_message(chat_id=update.message.chat_id,message_id=update.message.message_id)
        
    def greet_chat_members(self, update, context):
        print("greet_chat_members")
        """Greets new users in chats and announces when someone leaves"""
        msg = update.effective_message
        print("Msg", msg)
        if update.effective_chat.id not in self.chat_ids:
            from_user = "UNKNOWN"
            print("1 Message from user {} is from chat_id not being monitored: {}".format(
                from_user,
                update.effective_chat.id)
            )
            return
        result = extract_status_change(update.chat_member)
        if result is None:
            return
        was_member, is_member = result
        cause_name = update.chat_member.from_user.mention_html()
        member_name = update.chat_member.new_chat_member.user.mention_html()
        if (not was_member and is_member) or is_member == "member":
            s = session()
            usuario = s.query(User).filter_by(id=update.chat_member.new_chat_member.user.id).first()  # gets the initial value            
            if usuario is not None:
                if usuario.verified == 1:
                    s.close()
                    return
            s.close()
            captcha_config = s.query(MiscData).filter_by(key = "captcha").first().data
            welcome_config = s.query(MiscData).filter_by(key = "welcome_msg").first().data
            print("New member!\nCaptcha: " + captcha_config + "\nWelcome Msg: " + welcome_config)
            if welcome_config == 'true':
                delete_message_by_type(context.bot, "welcome", update.effective_chat.id)
                message = f"Hello and Welcome {member_name} to the Official DFX Finance Telegram Channel! 🔥🐉\n\nThank you so much for taking the time to stop by and from all of us at DFX, we hope you have a great day! ☀️"
                reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton(text='Check out our Linktree', url='https://linktr.ee/dfxfinance')]
                ])
                tlg_send_message(context.bot, update.effective_chat.id, message, "welcome", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            verified = 0
            if captcha_config == 'true':
                verified = 0
                messageCaptcha = "Before you can post to the group you must complete a CAPTCHA, do this and all your questions will be answered."
                reply_markup_captcha = InlineKeyboardMarkup([
                        [InlineKeyboardButton(text='Resolve CAPTCHA', url='https://t.me/' + BOT_ALIAS + '?start')]
                ])
                delete_message_by_type(context.bot, "captcha", update.effective_chat.id)
                msg = tlg_send_message(context.bot, update.effective_chat.id, messageCaptcha, "captcha", reply_markup=reply_markup_captcha, parse_mode=ParseMode.HTML)
                captcha_msg = msg['msg'].message_id
            else:
                verified = 1
                captcha_msg = 0
            
            user = update.chat_member.new_chat_member.user
            if not self.id_exists(user.id):
                add_user_success = self.add_user(
                    user.id,
                    user.first_name,
                    user.last_name,
                    user.username,
                    verified,captcha_msg)
                if add_user_success:
                    print("User added: {}".format(user.id))
                else:
                    print("Something went wrong adding the user {}".format(user.id), file=sys.stderr)
            else:
                s = session()
                usuario = s.query(User).filter_by(id=user.id).first()  # gets the initial value     
                if captcha_config == 'true':
                    usuario.captcha_messsage=msg['msg'].message_id
                else:
                    usuario.captcha_messsage=0
                s.merge(usuario)
                s.commit()
                s.close()
            if captcha_config == 'true':
                permissions = ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                )
                context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions)          

        
    def security_check_username(self, bot, update):
        """ Test username for security violations """
        print("security_check_username")
        # Nothing by the moment


    def security_check_message(self, bot, update):
        print("security_check_message")
        """ Test message for security violations """


    def attachment_check(self, bot, update):
        print("attachment_check")
        """ Hide messages with attachments (except photo or video) """
        if update.message is not None:
            s = session()
            usuario = s.query(User).filter_by(id=update.message.from_user.id).first()
            log_message = "Log Message"
            if (update.message.audio or
                update.message.document or
                update.message.game or
                update.message.voice) and usuario.popularity == 0:
                # Logging
                mention_html = update.message.from_user.mention_html()
                log_message = "❌ Message deleted. " + mention_html + " you are not authorized to post audios, documents, links, games or voice messages. You need to level up by joining in the conversation more."
                delete_message_by_type(bot, "not-authorized", CHAT_IDS)
                tlg_send_message(bot, CHAT_IDS, log_message, type="not-authorized", parse_mode=ParseMode.HTML)
                print(log_message)
                # Delete the message
                update.message.delete()
                # Log in database
                messageHide = MessageHide(
                    user_id=update.message.from_user.id,
                    message=update.message.text)
                s.add(messageHide)
                s.commit()                          
            s.close()

    def banCaptcha(self, bot, message, usuario, from_user):
        tlg_send_message(bot, message.chat_id, "You have been banned for failing 50 attempts. If you think it is an error write to @danicryptonews", type=None, parse_mode=ParseMode.HTML)
        s = session()
        checkban = s.query(UserBan).filter_by(UserBan.user_id==usuario.id).all()
        if checkban is not None:
            return
        userBan = UserBan(
            user_id=usuario.id,
            reason="CAPTCHA failed 50 times")
        s.add(userBan)
        s.commit()
        s.close()
        print("USER", usuario.username, "FAILED THE CAPTCHA. BANNED.")
        # Removed banning command
        # bot.kick_chat_member(chat_id=CHAT_IDS, user_id=from_user) 
        try:
            bot.deleteMessage(message_id = usuario.captcha_message, chat_id = CHAT_IDS)
        except Exception as e:
            print("[001] Error but not a problem")
            
            
    def logger(self, update: Update, context: CallbackContext):
        print("logger")
        bot = context.bot
        """ Primary Logger. Handles incoming bot messages and saves them to DB

        :param bot: telegram.Bot https://python-telegram-bot.readthedocs.io/en/stable/telegram.bot.html
        :param update: telegram.Update https://python-telegram-bot.readthedocs.io/en/stable/telegram.update.html
        """
        s = session()
        if (
            update.effective_user is None
            or update.effective_user.id in self.ignore_user_ids
        ):
            print("{}: Ignoring update.".format(update.update_id))
            return

        try:          
            message = update.message

            # message is optional
            if message is None:

                if update.effective_message is None:
                    print("No message included in update")
                    return

                message = update.effective_message

            if message:
                user = message.from_user
                # Lets see if I must change the user info
                usuario = s.query(User).filter_by(id=user.id).first()
                if usuario is not None:
                    usuario.first_name = user.first_name
                    usuario.last_name = user.last_name
                    usuario.username = user.username
                    s.merge(usuario)
                    s.commit()
                # If its edited, pass 
                if update.edited_message is not None:
                    self.log_message(user.id, message.text,
                                     message.chat_id, message.message_id, update.edited_message.text)
                    return
                # Limit bot to monitoring certain chats
                if message.chat_id not in self.chat_ids:
                    from_user = "UNKNOWN"
                    if user:
                        from_user = user.id
                    if message.chat.type == "private":
                        # gets the initial value
                        if usuario is None:
                            tlg_send_message(bot, message.chat_id, "You are not a @DFX_Finance user. In order to interact with me you must join the group.", type=None, parse_mode=ParseMode.HTML)
                        elif (usuario.username == "CotyKuhn" or usuario.username == "Negitaro" or usuario.username == "danicryptonews" or usuario.username == "naisechef") and message.text == "/bannedlist":
                            banned_list = s.query(UserBan).all()
                            try:
                                os.remove('ban_list_export.xlsx')
                            except Exception:
                                print("[003] Error deleting report file")
                            workbook = xlsxwriter.Workbook('ban_list_export.xlsx')
                            worksheet = workbook.add_worksheet()
                            worksheet.write('A1', 'User ID')
                            worksheet.write('B1', 'User first name')
                            worksheet.write('C1', 'User username')
                            worksheet.write('D1', 'Ban reason')
                            worksheet.write('E1', 'Date banned')
                            n = 2
                            print(message.text_html)
                            for banned in banned_list:
                                i = str(n)
                                username = s.query(User).filter(User.id==banned.user_id).first()
                                worksheet.write('A' + i, banned.user_id)
                                worksheet.write('B' + i, username.first_name)
                                if username.username is not None:
                                    worksheet.write('C' + i, username.username)
                                else:
                                    worksheet.write('C' + i, 'Unset')
                                worksheet.write('D' + i, banned.reason)
                                worksheet.write('E' + i, banned.time.strftime("%b %d %Y %H:%M:%S"))
                                n = n + 1
                            workbook.close()
                            report = 'ban_list_export.xlsx'
                            tlg_send_file(bot, message.chat_id, open(report, 'rb'), type=None)
                        elif "/text2html" in message.text:
                            tlg_send_message(bot, message.chat_id, message.text_html.replace("\n", "\\n"), type=None, parse_mode=None)
                        elif usuario is not None and usuario.verified == 0:
                            captchaModel = s.query(Captcha).filter_by(user_id=from_user).first()
                            if captchaModel is not None and captchaModel.attemps <= 0:
                                self.banCaptcha(bot, message, usuario, from_user)
                                return
                            elif captchaModel is not None and captchaModel.solution == message.text.upper().replace(" ", ""):
                                usuario = s.query(User).filter_by(id=user.id).first()  # gets the initial value
                                usuario.verified=1
                                s.merge(usuario)
                                s.commit()
                                permissions = ChatPermissions(
                                    can_send_messages=True,
                                    can_send_media_messages=True,
                                    can_send_other_messages=True,
                                    can_add_web_page_previews=True,
                                    can_invite_users=True,
                                    can_pin_messages=True,
                                )
                                context.bot.restrict_chat_member(CHAT_IDS, from_user, permissions) 
                                tlg_send_message(bot, message.chat_id, "✅ CAPTCHA solved, welcome to the DFX Finance community! Take a look at the pinned posts or visit docs.dfx.finance for more info.", type=None, parse_mode=ParseMode.HTML)
                                print("USER", usuario.first_name, usuario.username, "PASSED THE CAPTCHA")
                                try:
                                    bot.deleteMessage(message_id = usuario.captcha_message, chat_id = CHAT_IDS)
                                except Exception as e:
                                    print("[001] Error but not a problem")
                            elif message.text == "/start" and captchaModel is None:
                                captcha = create_image_captcha(message.chat_id, usuario.id, 1)       
                                captcha_code = captcha["characters"]
                                print("USER", usuario.first_name, usuario.username, "STARTED THE CAPTCHA")
                                captchaModel = Captcha(
                                    id=None,
                                    user_id=usuario.id,
                                    attemps=50,
                                    solution=captcha_code
                                    )
                                s.add(captchaModel)
                                s.commit()                               
                                img_caption = "Please write the 4 numbers you see in the image to verify that you are a human.\n\n📝 NOTE: If you find it hard you can write the command /new and receive a new one."
                                tlg_send_image(bot, message.chat_id, open(captcha["image"],"rb"), None, img_caption)
                            elif message.text == "/new" and captchaModel is not None:
                                captcha = create_image_captcha(message.chat_id, usuario.id, 1)       
                                captcha_code = captcha["characters"]
                                captchaModel.attemps=captchaModel.attemps-1
                                captchaModel.solution=captcha_code
                                s.merge(captchaModel)
                                s.commit()
                                print("USER", usuario.username, "FAILED ONE CAPTCHA ATTEMPT")
                                intentos = captchaModel.attemps
                                if intentos == 0:
                                    self.banCaptcha(bot, message, usuario, from_user)
                                    return
                                tlg_send_message(bot, message.chat_id, "Regenerating CAPTCHA, give it another try", type=None, parse_mode=ParseMode.HTML)
                                img_caption = "Please write the 4 numbers you see in the image to verify that you are a human."
                                tlg_send_image(bot, message.chat_id, open(captcha["image"],"rb"), None, img_caption)
                            elif captchaModel is not None and captchaModel.solution != message.text.upper().replace(" ", ""):
                                captchaModel.attemps=captchaModel.attemps-1
                                s.merge(captchaModel)
                                s.commit()
                                intentos = captchaModel.attemps
                                print("USER", usuario.username, "FAILED ONE CAPTCHA ATTEMPT")
                                if intentos == 0:
                                    self.banCaptcha(bot, message, usuario, from_user)
                                    return
                                tlg_send_message(bot, message.chat_id, "❌ Sorry incorrect, give it another go", type=None, parse_mode=ParseMode.HTML)                  
                        elif usuario.verified == 1:
                            tlg_send_message(bot, message.chat_id, "You have already completed the CAPTCHA, nothing more to see here", type=None, parse_mode=ParseMode.HTML)                     
                        elif usuario is None:
                            print("3 Message from user {} is from chat_id not being monitored: {}".format(
                                from_user,
                                message.chat_id)
                            )
                        s.close()
                    return

                if self.id_exists(user.id):
                    self.log_message(user.id, message.text,
                                     message.chat_id, message.message_id, None)
                else:
                    add_user_success = self.add_user(
                        user.id,
                        user.first_name,
                        user.last_name,
                        user.username,
                        1,
                        0)

                    if add_user_success:
                        self.log_message(
                            user.id, message.text, message.chat_id, message.message_id, None)
                        print("User added: {}".format(user.id))
                    else:
                        print("Something went wrong adding the user {}".format(user.id), file=sys.stderr)

                user_name = (
                    user.username or
                    "{} {}".format(user.first_name, user.last_name) or
                    "<none>").encode("utf-8")
                if 'vpn' in message.text.lower() and message.from_user.id not in self.get_admin_ids(bot, message.chat_id):
                    mention_html = message.from_user.mention_html()
                    bot.deleteMessage(message_id = message.message_id, chat_id = message.chat_id)
                    log_message = "❌ Message deleted. Sorry " + mention_html + " but talking about VPN services is not allowed. If you think it's an error, contact any admin to recover your message. You can check the list of admins using the /adminlist command."
                    delete_message_by_type(bot, "not-authorized", CHAT_IDS)
                    tlg_send_message(bot, CHAT_IDS, log_message, type="not-authorized", parse_mode=ParseMode.HTML)
                if message.text:
                    mention_html = message.from_user.mention_html()
                    self.add_count_messages(user.id, bot, message.chat_id, mention_html)
                    self.handleMessagesReplies(message)
                    print("{} {} ({}) : {}".format(
                        strftime("%Y-%m-%dT%H:%M:%S"),
                        user.id,
                        user_name,
                        message.text.encode("utf-8"))
                    )
                else:
                    print("{} {} ({}) : non-message".format(
                        strftime("%Y-%m-%dT%H:%M:%S"),
                        user.id,
                        user_name)
                    )

            else:
                print("Update and user not logged because no message was found")

            # Don"t check admin activity
            is_admin = False
            if message:
                is_admin = message.from_user.id in self.get_admin_ids(bot, message.chat_id)

            if is_admin and self.admin_exempt:
                print("👮‍♂️ Skipping checks. User is admin: {}".format(user.id))
            else:
                # Security checks
                self.attachment_check(bot, update)
                self.link_checks(bot, update)
                self.security_check_username(bot, update)
                # self.security_check_message(bot, update)
            if message.text == "+1" and message.reply_to_message.from_user is not None:
                checkAlreadyVoted = s.query(UserReputation).filter(UserReputation.message_id==message.reply_to_message.message_id, UserReputation.voter_id==message.from_user.id).all()
                if message.reply_to_message.from_user.id == message.from_user.id:
                    print("Cant vote your own message lol")
                elif checkAlreadyVoted is None or not checkAlreadyVoted:
                    userReputation = UserReputation(
                        owner_id=message.reply_to_message.from_user.id,
                        message_id=message.reply_to_message.message_id,
                        voter_id=message.from_user.id)
                    s.add(userReputation)
                    s.commit() 
                    userAddRep = s.query(User).filter(User.id==message.reply_to_message.from_user.id).first()
                    userAddRep.reputation = userAddRep.reputation + 1
                    s.merge(userAddRep)
                    s.commit()
                    votes = s.query(UserReputation).filter(UserReputation.message_id==message.reply_to_message.message_id).count()
                    delete_message_by_type(bot, "increase-reputation", CHAT_IDS)
                    tlg_send_message(bot, CHAT_IDS, "🙌🏻 " + message.from_user.mention_html() + " increased the reputation of " + message.reply_to_message.from_user.mention_html(), type="increase-reputation", parse_mode=ParseMode.HTML)
                    if votes == 5:
                        tlg_send_message(bot, message.chat_id, "⭐️ Congratulations! Your post reached 5 upvotes, keep rocking!", "", reply_to_message_id=message.reply_to_message.message_id, parse_mode=ParseMode.HTML)
                    username = None
                    if message.from_user.username is not None:
                        username = "@" + message.from_user.username
                    try:
                        tlg_send_message(bot, message.reply_to_message.from_user.id, "⭐️ You have been upvoted by " + str(message.from_user.first_name or '') + " " + str(message.from_user.last_name or '') + " " + str(username or '') + "\n\n✉️ Message link: https://t.me/DFX_Finance/" + str(message.reply_to_message.message_id), type=None, parse_mode=ParseMode.HTML)
                    except TelegramError:
                        print("User disabled voting notifications")
                    print("New vote from", message.from_user.first_name, message.from_user.last_name, "to", userAddRep.first_name, userAddRep.last_name)
                else:
                    print("User already voted to that message")
                bot.deleteMessage(message_id = message.message_id, chat_id = message.chat_id)
            s.close()
        except Exception as e:
            s.close()
            print("Error[521]: {}".format(e))
            print(traceback.format_exc())
            print("Error on line {}".format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        
    def handleMessagesReplies(self, message):
        ## Random stuff 1 out of 30 chances
        #chance = random.randint(0,30)
        #reply = random.randint(0,(len(funny_crazy_things)+1))
        #print("El chance es:", chance)
        #if chance == 15:
        #    message.reply_text(funny_crazy_things[reply])
        #    return
        array_words = re.sub('['+string.punctuation+']', '', message.text.lower()).split()
        badWord = False
        for word in array_words:
            if word in bad_words:
                badWord = True
                break        
        if badWord == True:
            n = random.randint(0,(len(replies_bad_words)-1))
            message.reply_text(replies_bad_words[n])
        elif 'hello' in array_words or 'hi' in array_words:
            n2 = random.randint(0,(len(welcome_messages)-1))
            message.reply_text(welcome_messages[n2])
        elif 'dfx' in array_words and 'dump' in array_words:
            message.reply_text("If DFX dumps, pump your wallet with more!")
        elif 'moon' in array_words or 'moons' in array_words or 'mooning' in array_words:
            message.reply_text("To the moon we go! 🚀🚀") 
        elif 'price prediction' in array_words:
            message.reply_text("My price prediction is that DFX will moon sooner or later and you will regret not buying more.")    
        elif 'dyor' in array_words:
            message.reply_text("DYOR stands for *D*FX *Y*our *O*nly *R*etirement (plan)", parse_mode="Markdown")    
            
    def link_checks(self, bot, update):
        print("link_checks")
        s = session()
        url = False
        if update.message is not None:
            try:
	            if len(extractor.find_urls(str(update.message.text))) > 0:
	                url = True
	            usuario = s.query(User).filter_by(id=update.message.from_user.id).first()
	            if usuario.popularity == 0 and url == True:
	                mention_html = update.message.from_user.mention_html()
	                log_message = "❌ Message deleted. " + mention_html + " you are not authorized to post audios, documents, links, games or voice messages. Level up to remove these restrictions."
	                delete_message_by_type(bot, "not-authorized", CHAT_IDS)
	                tlg_send_message(bot, CHAT_IDS, log_message, type="not-authorized", parse_mode=ParseMode.HTML)
	                update.message.delete()
	                messageHide = MessageHide(
	                    user_id=update.message.from_user.id,
	                    message=update.message.text)
	                s.add(messageHide)
	                s.commit()
            except: pass	          
        s.close()
        
    # DB queries
    def id_exists(self, id_value):
        print("id_exists")
        s = session()
        bool_set = False
        for id1 in s.query(User.id).filter_by(id=id_value):
            if id1:
                bool_set = True

        s.close()
        return bool_set

    def log_message(self, user_id, user_message, chat_id, message_id, last_edit):
        print("log_message")
        s = session()
        if user_message is None:
            user_message = "[NO MESSAGE]"

        try:
            if last_edit is None:              
                msg1 = Message(user_id=user_id, message=user_message, chat_id=chat_id, 
                    last_edit=last_edit, message_id=message_id)
                s.add(msg1)
                s.commit()
                
            else:
                msg1 = s.query(Message).filter(Message.message_id==message_id).first()
                user = s.query(User).filter(User.id==user_id).first()
                if msg1 is None:
                    print(user.first_name, "(", user.username, ")", "Edited message, but got an error !!!!!!!!!! MESSAGE_ID=", message_id)
                else:    
                    print(user.first_name, "(", user.username, ")", "Edited message, from:", msg1.message, "to:", user_message)
                    msg1.last_edit = user_message
                    s.merge(msg1)
                    s.commit()     
        except Exception as e:
            print("Error logging message: {}".format(e))
            print(traceback.format_exc())
            s.close()
        s.close()
       
       
    def add_count_messages(self, user_id, bot, chat_id, mention_html):
            s = session()
            usuarios = s.query(User).filter_by(id=user_id)  # gets the initial value
            for usuario in usuarios:                
                usuario.message_count = usuario.message_count + 1
                mensajes = usuario.message_count
                popularity = usuario.popularity            
                reputation = usuario.reputation
                if math.floor((mensajes+1)/50 + reputation/10) > popularity:
                    usuario.popularity = math.floor((mensajes+1)/50+reputation/10)
                    popularity_new = usuario.popularity
                    bot.send_message(chat_id, f"🌟 {mention_html} has reached level {popularity_new} !🌟", parse_mode=ParseMode.HTML)
                s.merge(usuario)
            s.commit()
            s.close()
                
    def add_user(self, user_id, first_name, last_name, username, verified, captcha_message):
        print("add_user")
        try:
            s = session()
            user = User(
                id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                message_count=0,
                popularity=0,
                reputation=0,
                join_datetime=func.now(),
                verified=verified,
                captcha_message=captcha_message
                )
            s.add(user)
            s.commit()
            s.close()
            return self.id_exists(user_id)
        except Exception as e:
            print("Error[347]: {}".format(e))
            print(traceback.format_exc())

            
    def handle_command(self, update: Update, context: CallbackContext):
        print("handle_command")
        bot = context.bot
        
        chat_id = None
        command = None
        s = session()
        message_id = update.effective_message.message_id
        message = update.message
        entities = message.entities
        user_interact_with = None
        for entity in entities:
            if entity.user is not None:
                user_interact_with = entity.user        
        if message.chat.type == "private":
            tlg_send_message(bot, update.effective_message.chat.id, "This command can only be used on the group", type=None, parse_mode=ParseMode.HTML)
            return
        is_admin = False
        if message:
            is_admin = message.from_user.id in self.get_admin_ids(bot, message.chat_id)
        command = command_from_message(update.effective_message)

        if update.effective_message.chat:
            chat_id = update.effective_message.chat.id
        if chat_id not in self.chat_ids:
            from_user = "UNKNOWN"
            print("2 Message from user {} is from chat_id not being monitored: {}".format(
                from_user,
                chat_id)
            )
            return
        print("command: {} seen in chat_id {}".format(command, chat_id))
        if BOT_ALIAS in command:
            command = command.replace("@" + BOT_ALIAS, "")
        if command != None and command not in ["/contract", "/website", "/twitter", "/medium", "/summary", "/education", "/dfx2", "/adminlist"]:
            bot.deleteMessage(message_id = update.message.message_id, chat_id = chat_id)
        if command == "/dragon":
            n = random.randint(1,59)
            image = "dfx_dragon_images/Image" + str(n) + ".jpg"
            delete_message_by_type(bot, "image", chat_id)
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image")
        if command == "/hopium":
            n = random.randint(1,7)
            image = "hopium_images/Image" + str(n) + ".jpg"
            delete_message_by_type(bot, "image", chat_id)
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image")
        if command == "/kevin":
            image = "random_images/kevin.jpg"
            delete_message_by_type(bot, "image", chat_id)
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image")
        if command == "/adrian":
            image = "random_images/adrian.jpg"
            delete_message_by_type(bot, "image", chat_id)
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image")
        if command == "/gm":
            image = "random_images/gm.jpg"
            delete_message_by_type(bot, "image", chat_id)
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image") 
        if command == "/coty":
            image = "random_images/coty.jpg"
            delete_message_by_type(bot, "image", chat_id)
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image")
        if command == "/jim" or command == "/kim" or command == "/kimjim" or command == "/jimkim" or command == "/good":
            image = "random_images/kim.jpg"           
            delete_message_by_type(bot, "image", chat_id)
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image")
        if command == "/price":
            delete_message_by_type(bot, "price", chat_id)
            self.price(bot, chat_id)
        if command == "/whalechart":
            delete_message_by_type(bot, "whalechart", chat_id)
            tlg_send_message(bot, chat_id, "500 DFX - Shrimp 🦐 \n500 - 2000 DFX - Crab 🦀 \n2K - 10K DFX - Tropical Fish 🐠 \n10K - 20K DFX - Octopus 🐙 \n20K - 30K DFX - Dolphin 🐬 \n30K - 50K DFX - Shark 🦈 \n50K - 75K DFX - Baby Whale 🐳 \n75K - 100K DFX - Whale 🐋 \n100K - 200K DFX - Dragon 🐉 \n200K++ DFX - Mythical Dragon 🐲", "whalechart", parse_mode=ParseMode.HTML)
        if command == "/unban":
            if is_admin and self.admin_exempt:
                self.unban_command(bot, update, chat_id, (command + " "))
        if command == "/levelup":
            if is_admin and self.admin_exempt:
                self.level_up(bot, update, chat_id, (command + " ")) 
        if command == "/ban":
            if is_admin and self.admin_exempt:
                silent = False
                self.ban_command(bot, update, chat_id, silent, (command + " "))
        if command == "/mylevel":
            user = s.query(User).filter(User.id==message.from_user.id).first()           
            tlg_send_message(bot, chat_id, "👑 Hey " + message.from_user.mention_html() + ", you are <b>level " + str(user.popularity) + "</b> 👑", "user-level", parse_mode=ParseMode.HTML)
        if command == "/top10level":
            delete_message_by_type(bot, "rank", chat_id)
            admins = bot.get_chat_administrators(CHAT_IDS, timeout=20)
            admins_to_exclude = []
            for admin in admins:
                admins_to_exclude.append(admin.user.id)
            print("Group admins", admins_to_exclude)
            top10users = s.query(User).filter(User.id.notin_(admins_to_exclude)).order_by(User.popularity.desc(), User.reputation.desc(), User.message_count.desc()).limit(10).all()
            textTop10 = "<b>🏆 TOP 10 USERS BY LEVEL 🏆</b>\n\n"
            arrayNumberEmojis = "4️⃣_5️⃣_6️⃣_7️⃣_8️⃣_9️⃣_🔟"
            i = 1
            for userRank in top10users:
                if i == 1:
                    textTop10 = textTop10 + "🥇<b>" + str(userRank.first_name or '') + " " + str(userRank.last_name or '') + "</b> → Level " + str(userRank.popularity or '') + "\n"
                elif i == 2:
                    textTop10 = textTop10 + "🥈<b>" + str(userRank.first_name or '') + " " + str(userRank.last_name or '') + "</b> → Level " + str(userRank.popularity or '') + "\n"
                elif i == 3:
                    textTop10 = textTop10 + "🥉<b>" + str(userRank.first_name or '') + " " + str(userRank.last_name or '') + "</b> → Level " + str(userRank.popularity or '') + "\n"
                else:
                    textTop10 = textTop10 + arrayNumberEmojis.split("_")[i-4] + " <b>" + str(userRank.first_name or '') + " " + str(userRank.last_name or '') + "</b> → Level " + str(userRank.popularity or '') + "\n"
                i = i + 1
            textTop10 = textTop10 + "\n<i>📝 Level up by being active on the group</i>"
            tlg_send_message(bot, chat_id, textTop10, "rank", parse_mode=ParseMode.HTML)
        if command == "/supply":
            request = requests.get('https://circ-supply.dfx.finance/api?' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)))
            if request.status_code == 200:
                delete_message_by_type(bot, "supply", chat_id)
                supplyStr = request.text
                supply = "{:,.2f}".format(round(float(supplyStr), 2))
                supplyTelegramText = "<b>📊 DFX current circulating supply:</b>\n" + str(supply) + " DFX\n\nThanks for asking! 😊"
                tlg_send_message(bot, chat_id, supplyTelegramText, "supply", parse_mode=ParseMode.HTML)
        if command == "/hardban":
            if is_admin and self.admin_exempt:
                silent = False
                self.hard_ban_command(bot, update, chat_id, silent, (command + " "))
        if command == "/bansilent":
            if is_admin and self.admin_exempt:
                silent = True
                self.ban_command(bot, update, chat_id, silent, (command + " "))
        if command == "/all":
            if is_admin and self.admin_exempt:
                con = engine.connect()
                result = con.execute("SELECT array_to_string(array_agg(CONCAT('<a href=''tg://user?id=', id)),'''>&#8288;</a>') AS result FROM telegram_users;")
                mencion_todos = str(result.fetchone()).replace("(", "").replace("\"", "").replace(",", "").replace(")", "") + "'>\&#8288;/a>🛎 Hello everyone!"
                print(mencion_todos)
                tlg_send_message(bot, chat_id, mencion_todos, "banned-from-command", parse_mode=ParseMode.HTML)           
        if command == "/hardbansilent":
            if is_admin and self.admin_exempt:
                silent = True
                self.hard_ban_command(bot, update, chat_id, silent, (command + " "))
        if command == "/maticrpc":
            image = "guides/maticrpc.jpg"
            delete_message_by_type(bot, "image-guide", chat_id)
            caption = "The picture below shows the Remote Procedure Call (RPC) info that you can add to your MetaMask wallet in order to operate on the Polygon (MATIC) blockchain.\n\nIf you would like to verify the information above, you can do so right here ->\nhttps://docs.polygon.technology/docs/develop/network-details/network/"
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image-guide", caption=caption)
        if command == "/vote":
            image = "guides/vote.jpg"
            delete_message_by_type(bot, "image-guide", chat_id)
            caption = "<b>Forum</b>\nhttps://forum.dfx.finance/\n\n<b>Voting</b>\nhttps://vote.dfx.finance/#/\n\n<b>Docs</b>\nhttps://docs.dfx.finance/\n\n<b>Proposal Template</b>\nhttps://docs.google.com/document/d/1ghkenFXHT5n0OtdsE0BWgmaJj2JS5Rg4/edit?usp=sharing&ouid=109120569613830820828&rtpof=true&sd=true"
            tlg_send_image(bot, chat_id, open(image, 'rb'), "image-guide", caption=caption, parse_mode="HTML")
        if command == "/enablewelcome":
            if is_admin and self.admin_exempt:
                welcome = s.query(MiscData).filter_by(key = "welcome_msg").first()
                welcome.data = "true"
                s.merge(welcome)
                s.commit()
        if command == "/disablewelcome":
            if is_admin and self.admin_exempt:
                welcome = s.query(MiscData).filter_by(key = "welcome_msg").first()
                welcome.data = "false"
                s.merge(welcome)
                s.commit()
        if command == "/enablecaptcha":
            if is_admin and self.admin_exempt:
                captcha = s.query(MiscData).filter_by(key = "captcha").first()
                captcha.data = "true"
                s.merge(captcha)
                s.commit()
        if command == "/disablecaptcha":
            if is_admin and self.admin_exempt:
                captcha = s.query(MiscData).filter_by(key = "captcha").first()
                captcha.data = "false"
                s.merge(captcha)
                s.commit()       
        if command == "/contract":
            delete_message_by_type(bot, "contract", chat_id)
            tlg_reply_message(message, "<b><u>DFX Contract Addresses:</u></b>\n<b>Polygon</b>\n<code>0xE7804D91dfCDE7F776c90043E03eAa6Df87E6395</code>\n<b>Ethereum</b>\n<code>0x888888435FDe8e7d4c54cAb67f206e4199454c60</code>", "contract")
        if command == "/website":
            delete_message_by_type(bot, "website", chat_id)
            tlg_reply_message(message, "http://dfx.finance/", "website")
        if command == "/adminlist":
            delete_message_by_type(bot, "admin-list", chat_id)
            tlg_reply_message(message, "<b><u>DFX Finance Admins list:\n</u></b>- @CotyKuhn \n- @naisechef \n- @robeyryan \n- @danicryptonews \n- @snappycappy\n- @Negitaro\n- @bigbossmanf\n- @AJ_DeFi \n- @Andrew_Pinch \n- @scottdoughty\n- @TheBigSur", "admin-list")
        if command == "/twitter":
            delete_message_by_type(bot, "twitter", chat_id)
            tlg_reply_message(message, "https://twitter.com/DFXFinance", "twitter")
        if command == "/medium":
            delete_message_by_type(bot, "medium", chat_id)
            tlg_reply_message(message, "https://medium.com/@dfxfinance/", "medium")
        if command == "/education":
            education_text = "<b>*** DFX Education Zone ***</b>\n\nHere are some posts to educate yourself on DFX, the DAO and some features of the platform\n\n<b>DFX Summary:</b> https://t.me/DFX_Finance/54550\n\n<b>Proposals &amp; DAO Voting Process:</b> https://t.me/DFX_Finance/56321\n\n<b>veDFX rewards boost explained:</b> https://t.me/DFX_Finance/54903\n<b>veDFX voting explained:</b> https://t.me/DFX_Finance/54692\n\n<b>How to maximise earnings:</b> https://t.me/DFX_Finance/47143\n\n<b>DFX v2.0 summary:</b> https://t.me/DFX_Finance/43205\n\n<b>DFX v2.0 - add a new pool &amp; incentivise it: </b>https://t.me/DFX_Finance/58755"
            delete_message_by_type(bot, "education", chat_id)
            tlg_reply_message(message, education_text, "education")
        if command == "/dfx2":
            dfx2_text = "<b>** Education Zone - DFX 2.0: How to list and incentivise a new pool **</b>\n\nThere are 3 main steps to do this:\n\n1) add a new liquidity pool\nhttps://t.me/DFX_Finance/58752\n\n2) add a gauge (ability to receive rewards) to the pool\nhttps://t.me/DFX_Finance/58753\n\n3) allocate rewards to the pool\nhttps://t.me/DFX_Finance/58754"
            delete_message_by_type(bot, "dfx2", chat_id)
            tlg_reply_message(message, dfx2_text, "dfx2")
        if command == "/summary":
            summary_text = "<b>*** DFX Summary ***\n</b>Forex (FX) Decentralized Exchange specializing in Non-USD Stablecoins that are backed 1:1 with their fiat equivalent. Current Non-USD Stablecoin offerings include:\nCADC 🇨🇦 , EUROC &amp; EURS🇪🇺, XSGD 🇸🇬, GYEN 🇯🇵, NZDS 🇳🇿, XIDR 🇮🇩, TRYB 🇹🇷 all paired with  USDC 🇺🇸\n\nallowing users of the platform to swap one stablecoin for another at the cost of 0.05% fee (a regular bank charges 2% upwards to swap currencies, so DFX is 40x cheaper than a bank)\n\n<b>How does this work?:\n</b>- liquidity providers provide liquidity to the stablcoin pools by staking a pair of stablecoin tokens on \nhttps://app.dfx.finance/pools\n- users of the platform exchange one stablecoin for another and as part of the transaction a 0.05% swap fee is taken\n- liquidity providers receive swap fees (added back to the pool on every swap), and incentives from DFX in the form of DFX tokens (claimable at your convenience) resulting in an avg APR between 8%-46% (depending on the pool you provide liquidity too).\n- DFX tokens can then be locked into veDFX to give a boost in the APR received from their liquidity pool investment up to 2.5x\n- DFX tokens can also be used to vote on proposals within the DAO giving the community the ability to steer the direction of the protocol.\n\n<b>Upcoming Features\n</b>- veDFX: lock up your DFX for voting power on Liquidity Pool rewards allocation and a APR boost up to 2.5x\n- DFX2.0: any token can propose to list on DFX (including commodities such as Gold, Oil etc.) if they hold enough veDFX and pass the DFX snapshot DAO vote\n- Bribes: those holding DFX can be bribed to vote on snapshot proposal via hiddenhand\n- Lending/Borrowing: extending the Loan/Borrow ability on Euler from currently just CADC to all stablecoins on the platform\n\n<b>Partnerships\n</b>- Circle: close partner and also provider of the USDC and EUROC stablecoins\n- Insure DAO: to insure the liquidity pools if hacked\n- Bluejay Finance: specialises in non-usd stablecoin on/off ramps to fiat\n- Chainlink: provide the oracle to ensure super efficient prices match to real world exchange rates\n\n<b>Where to get DFX?\n</b>CEXes: Huobi, MEXC, CoinDCX and BitKan\nDEXes: 1inch, Balancer, Sushiswap dexes, TELcoin app\n\n<b>More Info\n</b>docs.dfx.finance"
            delete_message_by_type(bot, "summary", chat_id)
            tlg_reply_message(message, summary_text, "summary")
        if command == "/delmsg":
            if is_admin and self.admin_exempt:
                try:
                    message_text = update.message.text.replace(command + ' ', '')
                    if update.message.reply_to_message is not None:
                        bot.delete_message(chat_id=chat_id, message_id=update.message.reply_to_message.message_id)
                    elif message_text.isdecimal():
                        bot.delete_message(chat_id=chat_id, message_id=message_text)
                except:
                    print("Message to delete not found")
        s.close()
        
    def ban_command(self, bot, update, chat_id, silent, command):
        # Es admin, continúo
        text = update.message.text.replace(command, '')
        s = session()
        user_id = self.get_user_id(text, update, s)
        print("Going to ban user_id", user_id)
        if user_id == '' or user_id is None:
            print("FAILED TO BAN USER: NOT FOUND")
        else:
            delete_message_by_type(bot, "banned-from-command", chat_id)
            userdb = s.query(User).filter(User.id==user_id).first()
            if userdb is not None:
                complete_name = ''
                if userdb.first_name is not None:
                    complete_name = complete_name + userdb.first_name
                if userdb.last_name is not None:
                    complete_name = complete_name + ' ' + userdb.last_name
                mention = "<a href='tg://user?id=" + str(user_id) + "'>" + complete_name + "</a>"
                print(mention)
                if silent == False:
                    tlg_send_message(bot, CHAT_IDS, "⛔️ User " + mention + " has been banned", "banned-from-command", parse_mode=ParseMode.HTML)
            reason = "Banned by admin " + update.message.from_user.username
            self.ban_user_from_id(bot, user_id, reason=reason)
        s.close()
                
    def hard_ban_command(self, bot, update, chat_id, silent, command):
        # Es admin, continúo
        text = update.message.text.replace(command, '')
        s = session()
        user_id = self.get_user_id(text, update, s)
        print("Going to ban user_id", user_id)
        if user_id == '' or user_id is None:
            print("FAILED TO BAN USER: NOT FOUND")
        else:
            delete_message_by_type(bot, "banned-from-command", chat_id)
            userdb = s.query(User).filter(User.id==user_id).first()
            if userdb is not None:
                complete_name = ''
                if userdb.first_name is not None:
                    complete_name = complete_name + userdb.first_name
                if userdb.last_name is not None:
                    complete_name = complete_name + ' ' + userdb.last_name
                mention = "<a href='tg://user?id=" + str(user_id) + "'>" + complete_name + "</a>"
                if silent == False:
                    tlg_send_message(bot, CHAT_IDS, "⛔️ User " + mention + " has been banned", "banned-from-command", parse_mode=ParseMode.HTML)
            reason = "Banned by admin " + update.message.from_user.username
            self.ban_user_from_id(bot, user_id, reason=reason)
            self.delete_messages_from_id(bot, user_id)
        s.close()
    
    def unban_command(self, bot, update, chat_id, command):
        # Es admin, continúo
        text = update.message.text.replace(command, '')
        s = session()
        user_id = self.get_user_id(text, update, s)
        print("Going to unban user_id", user_id)
        if user_id == '' or user_id is None:
            print("FAILED TO UNBAN USER: NOT FOUND")
        else:
            bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            s.query(UserBan).filter(UserBan.user_id==user_id).delete()
            user_unban = s.query(User).filter(User.id==user_id).first()     
            if user_unban is None:
                print("FAILED TO UNBAN USER: NOT FOUND")
            else:
                user_unban.verified = 1
                s.merge(user_unban)
                s.commit()
                permissions = ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_change_info=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                )
                bot.restrict_chat_member(chat_id, user_id, permissions)  
                print("USER UNBANNED!!!")
        s.close()
        
    def level_up(self, bot, update, chat_id, command):
        s = session()
        text = update.message.text.replace(command, '')
        user_id = self.get_user_id(text, update, s)
        print("Going to levelup user_id", user_id)
        if user_id == '':
            print("FAILED TO LEVELUP USER: NOT FOUND")
        else:
            user = s.query(User).filter(User.id==user_id).first()
            if user is None:
                print("FAILED TO LEVELUP USER: NOT FOUND")
            else:                    
                user.popularity = user.popularity+1
                s.merge(user)
                s.commit()     
                print("USER LEVELED UP!!!")
        s.close()          
        
    def get_user_id(self, text, update, s):
        # Get user id
        try:
            entities_list = [MessageEntity.TEXT_MENTION]
            if update.message.reply_to_message is not None:
                # Take id from reply
                return update.message.reply_to_message.from_user.id
            entities = update.message.parse_entities(entities_list)
            if len(entities) > 0:
                # Take id from text mention
                for entity in entities:
                    return entity.user.id
            if text[0] == "@":
                # Take id from @ mention
                username = text.replace("@", "")
                user_unban = s.query(User).filter(User.username==username).first()  
                if user_unban is not None:
                    return user_unban.id
                else:
                    user_unban = s.query(User).filter(func.concat(User.first_name, ' ', User.last_name).like(text)).first()  
                    if user_unban is not None:
                        return user_unban.id
                    else:
                        return ''       
            if text.isdecimal():
                # Take id from text
                return text
        except Exception as e:
            print(e)
            return ''
            
    def delete_messages_from_id(self, bot, user_id):
        s = session()
        mensajes = s.query(Message).filter(Message.user_id==user_id)
        for mensaje in mensajes:
            try:
                bot.deleteMessage(message_id = mensaje.message_id, chat_id = mensaje.chat_id)
            except: print("Error deleting mass message, but not a problem") 
            s.delete(mensaje)
        s.commit()
        s.close()    
        
    def error(self, bot, update, error):
        print("error")
        """ Log Errors caused by Updates. """
        print("Update caused error ",
            file=sys.stderr)
            
    def queryHandler(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        bot = context.bot
        reply_markup_price = InlineKeyboardMarkup([
                [InlineKeyboardButton(text='🔄 Refresh data', callback_data="refresh")]
        ])
        try:
            bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=self.priceText(),
            parse_mode='HTML',
            reply_markup=reply_markup_price
            )
        except:
            print("No changes from last refresh")
        print("Clicked")
            
    def price(self, bot, chat_id):      
        msg = tlg_send_message(bot, chat_id, "⏳ <i>Fetching data...</i>", "price", parse_mode=ParseMode.HTML)            
        reply_markup_price = InlineKeyboardMarkup([
                [InlineKeyboardButton(text='🔄 Refresh data', callback_data="refresh")]
        ])
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg['msg'].message_id,
            text=self.priceText(),
            parse_mode='HTML',
            reply_markup=reply_markup_price)             
        
    def priceText(self):
        # check self.cleanLast(bot, chat_id, message_id, "price")
        request = requests.post('https://api.jeroenmoonen.nl/dfx.json')
        headers = {
            'accept': 'application/json',
        }
        holders_request = requests.get('https://api.covalenthq.com/v1/1/tokens/0x888888435fde8e7d4c54cab67f206e4199454c60/token_holders/?quote-currency=USD&format=JSON&page-number=0&page-size=50000&key=ckey_c5a2a730f02844b49c29d2c4457')
        response = requests.get('https://api.coingecko.com/api/v3/coins/dfx-finance', headers=headers)
        text = ''
        if request.status_code == 200 and response.status_code == 200 and holders_request.status_code == 200:
            data = request.json()
            datacg = response.json()
            price=datacg['market_data']['current_price']['usd']
            satoshi=data['satoshi']
            marketcap_btc=datacg['market_data']['market_cap']['usd']
            circulating_supply=data['circulating_supply']
            volume=datacg['market_data']['total_volume']['usd']
            todayHoldersEth = len(json.loads(holders_request.text)['data']['items'])
            todayHoldersPoly = int(data['hodlers']['polygon']['today'].replace(',', ''))
            todayHolders = todayHoldersEth + todayHoldersPoly
            h_change=data['24h_change']           
            text = '📊 <b>DFX stats at ' + str(datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")) + '</b>\n<b>Price:</b>  ' + str(price) + '$\n<b>Sats:</b> ' + satoshi + '\n<b>MarketCap:</b> ' + format(int(marketcap_btc),",") + '$\n<b>Circulating Supply:</b> ' + str(circulating_supply) + '\n<b>Volume:</b> ' + format(int(volume),",") + '$\n<b>Wallets:</b> ' + format(int(todayHolders),",") + '\n<b>24h change:</b> ' + h_change
        else:
            raise Exception('Query failed and return code is ' +  + '.      ' +  + ''.format(request.status_code,
                            query))               
        return text
        
        
    def start(self):
        print("start")

        load_dotenv('.env')  # load main .env file
        environment = os.getenv("ENVIRONMENT")
        print("Environment: " + environment)

        sub_env = '.env.' + environment
        load_dotenv(sub_env)  # load main .env file
	
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        CHAT_IDS = os.getenv("CHAT_IDS")
        BOT_ALIAS = os.getenv("BOT_ALIAS")
        NOTIFY_CHAT = os.getenv("NOTIFY_CHAT")

        TELEGRAM_BOT_POSTGRES_URL = os.getenv("TELEGRAM_BOT_POSTGRES_URL")

        TWITTER_URL = os.getenv("TWITTER_URL")
        TWITTER_CHAT_ID = os.getenv("TWITTER_CHAT_ID")

        """ Start the bot. """
#        global bot
#        app = Client(
#            "bot",
#            bot_token=TELEGRAM_BOT_TOKEN,
#            api_id="14842537",
#            api_hash="e5502ebd10539f1588a9604989c5a613",
#        )
#        app.start()
#        listMembers = []
#        for x in app.get_chat_members("DFX_Finance"):
#            try:
#                print("User added")
#                self.add_user(
#                x.user.id,
#                x.user.first_name,
#                x.user.last_name,
#                x.user.username,
#                0,0,func.now(),1,0,0)
#            except: pass
#        app.stop()
        # Create the EventHandler and pass it your bot"s token.
        updater = Updater(TELEGRAM_BOT_TOKEN)

        # Get the dispatcher to register handlers
        dp = updater.dispatcher

        # on different commands - answer in Telegram

        # on commands
        dp.add_handler(
            CommandHandler(
                command=self.available_commands,
                callback=self.handle_command,
                filters=Filters.all,
            )
        )
        dp.add_handler(CallbackQueryHandler(self.queryHandler))
        dp.add_handler(MessageHandler(Filters.status_update.new_chat_members,self.onjoin))
        dp.add_handler(MessageHandler(Filters.status_update.left_chat_member,self.onleft))
        # on noncommand i.e message - echo the message on Telegram
        filters = Filters.all and ~Filters.status_update.new_chat_members
        dp.add_handler(MessageHandler(
            filters, callback=self.logger)
        )
        bot = updater.bot

        # log all errors
        dp.add_error_handler(
            lambda bot, update, error : self.error(bot, update, error)
        )
        # Handle members joining/leaving chats.
        dp.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
        dp.add_handler(ChatMemberHandler(self.greet_chat_members, ChatMemberHandler.CHAT_MEMBER))       
        print("LEN", len(replies_bad_words))
        th_0 = Thread(target=ban_not_verified, args=(bot,))
        th_0.name = "ban_not_verified"
        th_0.start()
        th_1 = Thread(target=user_increment, args=(bot,))
        th_1.name = "user_increment"
        th_1.start()
        th_2 = Thread(target=clean_messages, args=(bot,))
        th_2.name = "clean_messages"
        th_2.start()
        th_3 = Thread(target=twitter_reader, args=(bot,))
        th_3.name = "twitter_reader"
        th_3.start()
        th_4 = Thread(target=daily_description, args=(bot,))
        th_4.name = "daily_description"
        th_4.start()
        # Start the Bot
        updater.start_polling(allowed_updates=Update.ALL_TYPES)

        print("Bot started. Montitoring chats: {}".format(self.chat_ids))

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()
        

if __name__ == "__main__":
    c = TelegramMonitorBot()
    uvloop.install()
    c.start()
