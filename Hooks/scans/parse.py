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
 
import re
from Core.exceptions_ import PNickParseError
from Core.config import Config
from Core.maps import User
from Core.loadable import system
from Hooks.scans.parser import parse

scanre=re.compile("https?://[^/]+/(?:showscan|waves).pl\?scan_id=([0-9a-zA-Z]{15})")
scangrpre=re.compile("https?://[^/]+/(?:showscan|waves).pl\?scan_grp=([0-9a-zA-Z]{15})")

@system('PRIVMSG')
def catcher(message):
    try:
        user = User.load(name=message.get_pnick())
        uid = user.id if user else None
    except PNickParseError:
        uid = None

    share = True
    if Config.has_option("Channels", "share"):
        if message.get_chan().lower() == Config.get("Channels", "share").lower():
            share = False

    for m in scanre.finditer(message.get_msg()):
        parse(uid, "scan", m.group(1), share).start()

    for m in scangrpre.finditer(message.get_msg()):
        parse(uid, "group", m.group(1), share).start()
