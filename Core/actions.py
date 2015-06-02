# This file is part of Merlin.
# Merlin is the Copyright (C)2008,2009,2010 of Robin K. Hansen, Elliot Rosemarine, Andreas Jacobsen.

# Individual portions may be copyright by individual contributors, and
# are included in this collective work with permission of the copyright
# owners.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
 
# This determines what the bot can send to the server, and is basically the IRC-API for plugin writers

from Core.connection import Connection
from Core.chanusertracker import CUT
from Core.messages import Message, PUBLIC_REPLY, PRIVATE_REPLY, NOTICE_REPLY
from Core.config import Config
from Core.maps import User

class Action(Message):
    # This object holds the parse, and will enable users to send messages to the server on a higher level
    
    def write(self, text, color=False, priority=0):
        # Write something to the server, the message will be split up by newlines and at 450chars max

        # Set Priority
        p = 5 + priority
        if Config.getint("Connection", "antiflood") > 0:
            l = len(text)
            if l < 100:
                p -= 1
            elif l > 150:
                p += min(l,400) // 100 + l // 450

        n = False
        try:
            n = self.get_pnick()
        except:
            p += 2
        if n:
            if n in Config.options("Admins"):
                p -= 2
            try:
                u = User.load(n)
                if u:
                    if u.group_id == 1:
                        p -= 1
                    elif u.group_id == 2:
                        p += 1
                else:
                    p +=2
            except:
                p += 2

        # Split message and send
        colon = text.find(":")
        if colon != -1:
            while text[colon-1] != " " and colon != -1:
                colon = text.find(":",colon+1)
            if colon != -1:
                params = text[:colon+1]
                text = text[colon+1:]
        if colon == -1:
            params = text
            text = None
        if text:            
            if color:
                params += "\x03"+Config.get("Connection", "color")
            for line in text.split("\n"):
                while line:
                    i = len(line)
                    while i > (450 - len(params)):
                        i = max(line.rfind(" ", 0, i), line.rfind(",", 0, i))
                        if i == -1:
                            while len(params + line) > 450:
                                Connection.write((params + line)[:450], p)
                                line = line[450 - len(params):]
                            i = len(line)
                            continue
                    Connection.write(params + line[:i+1], p)
                    line = line[i+1:]
        else:
            Connection.write(params, p)
    
    def privmsg(self, text, target=None, priority=0):
        # Privmsg someone. Target defaults to the person who triggered this line
        # Should we send colours?
        if (Config.has_option("Connection", "color") and not Config.has_option("NoColor", target) and not (target[0] in ['#','&'] and Config.has_option("NoColorChan", target[1:]))):
            text = "\x03"+Config.get("Connection", "color")+text+"\x0F"
            color = True
        else:
            color = False
        # If we're opped in a channel in common with the user, we can reply with
        #  CPRIVMSG instead of PRIVMSG which doesn't count towards the flood limit.
        if (not target or target[0] not in "#&") and hasattr(self, "_channel") and CUT.opped(self.get_chan()) and CUT.nick_in_chan(target or self.get_nick(), self.get_chan()):
            self.write("CPRIVMSG %s %s :%s" % (target or self.get_nick(), self.get_chan(), text), color, priority)
        else:
            self.write("PRIVMSG %s :%s" % (target or self.get_nick(), text), color, priority)
    
    def notice(self, text, target=None, priority=0):
        # If we're opped in a channel in common with the user, we can reply with
        #  CNOTICE instead of NOTICE which doesn't count towards the flood limit.
        if hasattr(self, "_channel") and CUT.opped(self.get_chan()) and CUT.nick_in_chan(target or self.get_nick(), self.get_chan()):
            self.write("CNOTICE %s %s :%s" % (target or self.get_nick(), self.get_chan(), text), priority=priority)
        else:
            self.write("NOTICE %s :%s" % (target or self.get_nick(), text), priority=priority)
    
    def reply(self, text, priority=0):
        if self.get_command() != "PRIVMSG":
            return
        # Caps Lock is cruise control for awesome
        if self.get_msg().isupper():
            text = text.upper()
        # Always reply to a PM with a PM, otherwise only ! replies with privmsg
        # Always reply to an @command with a PM
        reply = self.reply_type()
        if reply == PUBLIC_REPLY:
            self.privmsg(text, self.get_chan(), priority=priority)
        if reply == PRIVATE_REPLY:
            self.privmsg(text, self.get_nick(), priority=priority)
        if reply == NOTICE_REPLY:
            self.notice(text, priority=priority)
    
    def alert(self, text, priority=0):
        if self.get_command() != "PRIVMSG":
            return
        # Notice the user, unless it was a PM
        if self.in_chan():
            self.notice(text, priority=priority-1)
        else:
            self.privmsg(text, self.get_nick(), priority=priority-1)
    
    def topic(self, text, channel=None):
        # Set the topic in a channel
        channel = channel or self.get_chan()
        self.write("TOPIC %s :%s" % (channel, text))
    
    def nick(self, new_nick):
        # Change the bots nick to new_nick
        self.write("NICK %s" % new_nick)
    
    def join(self, target, key=None):
        # Join a channel
        self.write("JOIN %s" % target if not key else "JOIN %s :%s" % (target, key))
    
    def part(self, target, comment=None):
        # Part a channel
        self.write(("PART %s :%s" % (target, comment)) if comment else ("PART %s" % target))
    
    def invite(self, target, channel=None):
        # Invite target to channel
        channel = channel or self.get_chan()
        self.write(("INVITE %s %s" % (target, channel)), priority=-1)
    
    def quit(self, message=None):
        # Quit the bot from the network
        self.write(("QUIT :%s" % message) if message else "QUIT", priority=+1)
    
    def kick(self, target, channel=None, message=None):
        # Make the bot kick someone
        channel = channel or self.get_chan()
        if message:
            self.write("KICK %s %s :%s" % (channel, target, message))
        else:
            self.write("KICK %s %s" % (channel, target))
    
