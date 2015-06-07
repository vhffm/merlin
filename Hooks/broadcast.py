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
 
# Module by Martin Stone

from Core.db import session
from Core.maps import Channel
from Core.config import Config
from Core.loadable import loadable, route, robohci

class broadcast(loadable):
    """Make a broadcast to all alliance channels. Append "HIDEME" if you do not want your username included."""
    usage = " <message> [HIDEME]"
    
    @route(r"(.+)", access = "admin")
    def execute(self, message, user, params):
        if params.group(1)[-6:].lower() == "hideme":
            notice = "%s" % (params.group(1)[:-6])
        else:
            notice = "(%s) %s" % (user.name, params.group(1))
        for chan in session.query(Channel).filter(Channel.userlevel > (Config.getint("Access",  "galmate") if "galmate" in Config.options("Access") else 0)).all():
            message.notice(notice, chan.name)
    
    @robohci
    def robocop(self, message, notice):
        if notice[:3] == "!#!":
            notice = " ".join(notice[3:].split("!#!"))
        for chan in session.query(Channel).filter(Channel.userlevel > (Config.getint("Access",  "galmate") if "galmate" in Config.options("Access") else 0)).all():
            message.notice(notice, chan.name)
