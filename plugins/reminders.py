from threading import Thread, Event
import datetime

from wrappers import *
from Message import Message
from dateutil import parser
import pymongo
import dill



units = {
        "year": 31536000,
        "years": 31536000,
        "fortnight": 1209600,
        "fortnights": 1209600,
        "week": 604800,
        "weeks": 604800,
        "day": 86400,
        "days": 86400,
        "hour": 3600,
        "hours": 3600,
        "min": 60,
        "mins": 60,
        "minute": 60,
        "minutes": 60,
        "second": 1,
        "seconds": 1,
        "sec": 1,
        "secs": 1,
        "moment": 90,
        "moments": 90,
        "milliseconds": 0.0001,
        "millisecond": 0.0001,
        "ms": 0.0001,
    }

quants = {
        "a": 1,
        "an": 1,
        "one": 1,
        "two": 2,
        "couple": 2,
        "three": 3,
        "few": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "dozen": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
        "hundred": 100,
        "thousand": 1000,
        "million": 1000000,
        "billion": 1000000000,
        "trillion": 1000000000000,
    }



@plugin(thread=True)
class Reminders(Thread):

    def __init__(self):
        super(Reminders, self).__init__()
        self.reminders = []
        self.event = Event()
        self.ticking = False

    @on_load
    def init(self):
        con = pymongo.MongoClient()
        db = con["reminders"]
        for reminder_ in db["reminders"].find():
            self.reminders.append(dill.loads(reminder_["reminder"]))
        self.reminders.sort()
        db.reminders.remove({})

    @on_unload
    def stop(self):
        self.ticking = False
        self.event.set()
        con = pymongo.MongoClient()
        db = con["reminders"]
        for reminder in self.reminders:
            db["reminders"].insert({"reminder": dill.dumps(reminder)})

    @command("date")
    def parse(self, message):
        "parse the date specified or return the current date"
        if message.text:
            date = parser.parse(message.text, fuzzy=True)
        else:
            date = datetime.datetime.now()
        # date = datetime_(date.year,date.month,date.day,date.hour,date.minute,date.second,date.microsecond,date.tzinfo)
        return message.reply(text=str(date), data=date)

    @command("reminds")
    def reminds(self, message):
        "list your current reminders"
        reminders = []
        for reminder_ in self.reminders:
            if message.nick == reminder_.set_for:
                reminders.append(reminder_)
        text = "you have %s reminders!%s"
        count = len(reminders)
        if count == 0:
            text2 = ""
        elif count < 3 or message.params[0] is not "#":
            text3 = " and ".join(
                [", ".join(["%s: %s: %s" % (str(x.set_time), x.set_by, x.message) for x in reminders[:1]])] or [] + [
                    "%s: %s: %s" % (str(x.set_time), x.set_by, x.message) for x in reminders[0:1]])
            text2 = " they are: {}".format(text3)
        else:
            text2 = " you have too many to post here, private message me for the list"

        text = text % (count, text2)
        return message.reply(text=text)

    @command
    def remind(self, message):
        """ remind <target> (in|at|on) (quantiy unit|datetime) to (message) -> sets a reminder, also accepts a piped in datetime or timedelta objects
        :param message:
        :return message:
        """
        if message._data is not None:
            if isinstance(message.data, datetime.datetime):
                self.reminders.append(reminder(message.nick, message.nick, datetime.datetime.today(),
                                               message.data, message._text or "", message.params,
                                               message.server))
                self.reminders.sort()
                self.event.set()
                return message.reply("reminder set for %s!" % str(message.data))
            elif isinstance(message.data, datetime.timedelta):
                self.reminders.append(reminder(message.nick, message.nick, datetime.datetime.today(),
                                               datetime.datetime.today() + message.data, message._text or "",
                                               message.params,
                                               message.server))
                self.reminders.sort()
                self.event.set()
                return message.reply("reminder set to go in %s!" % str(message.data))
            else:
                raise TypeError("expected a datetime or timedelta object")
        else:
            if message.text.split()[1:2] == ["in"]:
                try:
                    setfor, _, quant, unit, *msg = message.text.split()
                except:
                    raise Exception("invalid syntax")

                if quant in quants:
                    quant = quants[quant]
                else:
                    try:
                        quant = float(quant)
                    except:
                        Exception("unknown quantity: %s" % quant)

                if unit in units:
                    unit = units[unit]
                else:
                    raise Exception("unkown unit: %s" % unit)
                if msg[0:1] == ["to"]:
                    msg = msg[1:]
                msg = " ".join(msg)

                total = quant * unit

                date = datetime.datetime.now() + datetime.timedelta(seconds=total)


                if setfor == "me":
                    setfor = message.nick
                self.reminders.append(reminder(message.nick, setfor, datetime.datetime.today(),
                                               date, msg or "", message.params,
                                               message.server))
                self.reminders.sort()
                self.event.set()
                return message.reply("reminder set to go in %s!" % str(datetime.timedelta(seconds=total)))
            elif message.text.split()[1:2] == ["at"] or message.text.split()[1:2] == ["on"]:
                date, *msg = message.text[3:].split("to ")
                date = parser.parse(date, fuzzy=True)
                msg = "to ".join(msg)
                setfor = message.text.split()[0]
                if setfor == "me":
                    setfor = message.nick
                self.reminders.append(reminder(message.nick, setfor, datetime.datetime.today(),
                                               date, msg or "", message.params,
                                               message.server))
                self.reminders.sort()
                self.event.set()
                return message.reply("reminder set for %s!" % str(date))
            else:


                self.reminders.append(reminder(message.nick, message.nick, datetime.datetime.today(),
                                               datetime.datetime.today() + datetime.timedelta(0, 10), "",
                                               message.params,
                                               message.server))
                self.reminders.sort()
                self.event.set()
                return message.reply("10 second reminder set!")

    def run(self):
        self.ticking = True
        while self.ticking:
            if self.reminders and self.reminders[0].due_time <= datetime.datetime.today():
                try:
                    self.bot.send(self.reminders[0].to_message())
                except:
                    pass

                del self.reminders[0]

            else:
                if self.reminders:
                    self.event.wait((self.reminders[0].due_time - datetime.datetime.today()).total_seconds())
                else:
                    self.event.wait()
                self.event.clear()


class reminder:
    def __init__(self, set_by, set_for, set_time, due_time, message, channel, server):
        self.set_by = set_by
        self.set_for = set_for
        self.set_time = set_time
        self.due_time = due_time
        self.message = message
        self.channel = channel
        self.server = server

    def to_message(self):
        text = self.set_for + ": "
        if self.set_by == self.set_for:
            text += "reminder"
        else:
            text += self.set_by + " reminds you"
        if self.message:
            text += ": " + self.message
        else:
            text += "!"
        return Message(server=self.server, command="PRIVMSG", params=self.channel, text=text)

    def __lt__(self, other):
        try:
            return other.due_time > self.due_time
        except:
            pass
        return 0