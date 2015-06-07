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
#
# Module by Martin Stone
 
import re
from Core.config import Config
from Core.db import session
from Core.maps import Planet, Alliance, User, Intel
from Core.loadable import loadable, route, require_user

class forcepref(loadable):
    """Set a user's planet, password for the webby, URL preference and phone number and settings; order doesn't matter"""
    usage = " <user> [planet=x.y.z] [password=pass] [url=ip] [phone=999] [pubphone=T|F] [smsmode=clickatell|google|both|twilio|whatsapp|email] [email=user@example.com]"
    access = 1 # Admin
    planet_coordre = re.compile(loadable.planet_coord)
    
    @route(r"(\S+)", access="forcepref")
    @require_user
    def show_prefs(self, message, user, params):

        name=params.group(1)
        u = User.load(name=name, exact=False)
        if u is None:
            message.reply("No members matching %s found"%(name,))
            return
        else:
            user=u

        reply = ""
        if user.planet is not None:
            reply += " planet=%s:%s:%s" % (user.planet.x,user.planet.y,user.planet.z,)
        if user.url:
            reply += " url: %s" % (Config.get("alturls", user.url),)
        if user.email:
            reply += " email=%s" % (user.email,)
        if user.phone:
            reply += " phone=%s pubphone=%s" % (user.phone, str(user.pubphone)[0],)
            if user.smsmode is not None:
                reply += " smsmode=%s" % (user.smsmode,)
        if len(reply) > 0:
            message.reply("Preferences for %s:" % (user.name,) + reply)
        else:
            message.reply("%s hasn't set any preferences" % (user.name,))
    
    @route(r"(\S+)\s(.+)", access="admin")
    @require_user
    def set_prefs(self, message, user, params):

        name=params.group(1)
        u = User.load(name=name, exact=False)
        if u is None:
            message.reply("No members matching %s found"%(name,))
            return
        else:
            user=u
        
        params = self.split_opts(params.group(2))
        reply = ""
        for opt, val in params.items():
            if opt == "planet":
                m = self.planet_coordre.match(val)
                if m:
                    planet = Planet.load(*m.group(1,3,5))
                    if planet is None:
                        message.alert("No planet with coords %s:%s:%s" % m.group(1,3,5))
                        continue
                    user.planet = planet
                    reply += " planet=%s:%s:%s"%(planet.x,planet.y,planet.z)
                    if user.has_access("is_member"):
                        alliance = Alliance.load(Config.get("Alliance","name"))
                        if planet.intel is None:
                            planet.intel = Intel(nick=user.name, alliance=alliance)
                        else:
                            planet.intel.nick = user.name
                            planet.intel.alliance = alliance
                elif val in self.nulls:
                    user.planet = None
                    reply += " planet=None"
            if opt == "password":
                if message.in_chan():
                    message.reply("Don't set passwords in public you shit")
                    continue
                user.passwd = val
                reply += " password=%s"%(val)
            if opt == "url":
                if val == "game" or val in self.nulls:
                    user.url = None
                    val = Config.get("URL", "game")
                elif val not in Config.options("alturls"):
                    ret = "Valid URLs are: game: %s, " %(Config.get("URL", "game"),)
                    ret+= ", ".join(["%s: %s" %(k,v,) for k, v in Config.items("alturls")])
                    message.reply(ret)
                    continue
                else:
                    user.url = val
                    val = Config.get("alturls", val)
                reply += " url: %s"%(val)
            if opt == "email":
                if val in self.nulls:
                    user.email = None
                    reply += " email=None"
                else:
                    try:
                        user.email = val
                    except AssertionError:
                        reply += " email=%s"%(user.email)
                    else:
                        reply += " email=%s"%(val)
            if opt == "phone":
                if val in self.nulls:
                    user.phone = ""
                    reply += " phone=None"
                else:
                    user.phone = val
                    reply += " phone=%s"%(val)
            if opt == "pubphone":
                if val.lower() in self.true:
                    user.pubphone = True
                    reply += " pubphone=%s"%(True)
                elif val.lower() in self.false:
                    user.pubphone = False
                    reply += " pubphone=%s"%(False)
            if opt == "smsmode":
                if (val[:1] in ['C', 'G']) and (Config.get("Misc", "sms") != "combined"):
                    message.alert("Your alliance doesn't support SMS mode switching")
                    continue
                if val[:1].upper() in User._sms_modes:
                    user.smsmode = val
                    reply += " smsmode=%s" % (user.smsmode,)
                elif val[:1].lower() == "b" or val in self.nulls:
                    user._smsmode = None
                    reply += " smsmode=None"
        
        session.commit()
        if len(reply) > 0:
            message.reply("Updated preferences for %s:" % (user.name) + reply)
