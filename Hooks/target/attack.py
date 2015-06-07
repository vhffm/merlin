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
from sqlalchemy.sql import asc
from Core.paconf import PA
from Core.db import session
from Core.maps import Updates, Galaxy, Planet, Attack, Request
from Core.loadable import loadable, route
from Core.config import Config
from Core.robocop import push

class attack(loadable):
    """Create an attack page on the webby with automatic parsed scans"""
    usage = " [<eta|landingtick> [<#waves>w] <coordlist> [comment]] | [list] | [show <id>]"
    access = 3 # Member
    subcommands = ["att_early", "att_set"]
    subaccess = [4, 3]
    
    @route(r"(?:list)?")
    def list(self, message, user, params):
        Q = session.query(Attack)
        if not user.has_access("att_early"): # Hide attacks until they are active, unless the user has access
            Q = Q.filter(Attack.landtick <= Updates.current_tick() + Config.getint("Misc", "attactive"))
        Q = Q.filter(Attack.landtick + Attack.waves >= Updates.current_tick()) # Hide attacks one tick after the last wave has landed
        Q = Q.order_by(asc(Attack.id))
        
        replies = []
        for attack in Q:
            replies.append("(%d LT: %d %s)" %(attack.id,attack.landtick,attack.comment,))
        
        reply = "Open attacks: " + " ".join(replies)
        message.reply(reply)
    
    @route(r"(?:show\s+)?(\d+)")
    def show(self, message, user, params):
        id = params.group(1)
        attack = Attack.load(id)
        
        if attack is None:
            message.alert("No attack exists with id %s" %(id))
            return
        if not user.has_access("att_early") and attack.landtick > Updates.current_tick() + Config.getint("Misc", "attactive"):
            message.alert("Attack %s is not open yet" %(id))
            return
        
        message.reply(str(attack))
    
    @route(r"(?:new\s+)?(\d+)\s+(?:(\d+)\s*w(?:ave)?s?\s+)?([. :\-\d,]+)(?:\s*(.+))?", access="att_set")
    def new(self, message, user, params):
        tick = Updates.current_tick()
        comment = params.group(4) or ""
        when = int(params.group(1))
        waves = params.group(2) or Config.get("Misc", "attwaves")
        if when < PA.getint("numbers", "protection"):
            when += tick
        elif when <= tick:
            message.alert("Can not create attacks in the past. You wanted tick %s, but current tick is %s." % (when, tick,))
            return
        if when > 32767:
            when = 32767
        
        attack = Attack(landtick=when,comment=comment,waves=int(waves))
        session.add(attack)
        
        for coord in re.findall(loadable.coord, params.group(3)):
            if not coord[4]:
                galaxy = Galaxy.load(coord[0],coord[2])
                if galaxy:
                    attack.addGalaxy(galaxy)
            
            else:
                planet = Planet.load(coord[0],coord[2],coord[4])
                if planet:
                    attack.addPlanet(planet)
        
        session.commit()
        message.reply(str(attack))

        # Request scans
        if Config.has_option("Misc", "attscans"):
            scantypes = Config.get("Misc", "attscans")
        else:
            scantypes = ""

        for stype in scantypes:
           for p in attack.planets:
               scan = p.scan(stype)
               if scan and (int(tick) == scan.tick):
                   return
               else:
                   req = Request(target=p, scantype=stype, dists=0)
                   user.requests.append(req)
                   session.commit()
                   push("request", request_id=req.id, mode="request")
        if scantypes:
            message.reply("Scans requested: %s" % (scantypes))
