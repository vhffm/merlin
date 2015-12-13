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

import re, sys, time, urllib2, shutil, os, errno

# ########################################################################### #
# ##############################     NOTICE     ############################# #
# ########################################################################### #
#                                                                             #
# This file is based on excalibur, and is used to provide a standalone set of #
#   tick dumps (without a bot).                                               #
#                                                                             #
# This script is *NOT* part of the normal operation of merlin.                #
#                                                                             #
# ########################################################################### #
# ##############################     CONFIG     ############################# #
# ########################################################################### #

base_url = "http://game.planetarion.com/botfiles/"
alt_base = "http://dumps.dfwtk.com/"
useragent = "Dumper (Python-urllib/%s); Admin/YOUR_IRC_NICK_HERE" % (urllib2.__version__)

# ########################################################################### #
# ########################################################################### #

# From http://www.diveintopython.net/http_web_services/etags.html
class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        result = urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)
        result.status = code
        return result 


def get_dumps(last_tick, etag, modified, alt=False):
    global base_url, alt_base, useragent

    if alt:
       purl = alt_base + str(last_tick+1) + "/planet_listing.txt"
       gurl = alt_base + str(last_tick+1) + "/galaxy_listing.txt"
       aurl = alt_base + str(last_tick+1) + "/alliance_listing.txt"
       furl = alt_base + str(last_tick+1) + "/user_feed.txt"
    else:
       purl = base_url + "planet_listing.txt"
       gurl = base_url + "galaxy_listing.txt"
       aurl = base_url + "alliance_listing.txt"
       furl = base_url + "/user_feed.txt"

    # Build the request for planet data
    req = urllib2.Request(purl)
    if etag:
        req.add_header('If-None-Match', etag)
    if modified:
        req.add_header('If-Modified-Since', modified)
    if useragent:
        req.add_header('User-Agent', useragent)

    opener = urllib2.build_opener(DefaultErrorHandler())

    planets = opener.open(req)
    try:
        if planets.status == 304:
            print "Dump files not modified. Waiting..."
            time.sleep(60)
            return (False, False, False, False)
        elif planets.status == 404 and last_tick < alt:
            # Dumps are missing from archive. Check for dumps for next tick
            print "Dump files missing. Looking for newer..."
            return get_dumps(last_tick+1, etag, modified, alt)
        else:
            print "Error: %s" % planets.status
            time.sleep(120)
            return (False, False, False, False)
    except AttributeError:
        pass

    # Open the dump files
    try:
        req = urllib2.Request(gurl)
        req.add_header('User-Agent', useragent)
        galaxies = opener.open(req)
        req = urllib2.Request(aurl)
        req.add_header('User-Agent', useragent)
        alliances = opener.open(req)
        req = urllib2.Request(furl)
        req.add_header('User-Agent', useragent)
        feed = opener.open(req)
    except Exception, e:
        print "Failed gathering dump files.\n%s" % (str(e),)
        time.sleep(300)
        return (False, False, False, False)
    else:
        return (planets, galaxies, alliances, feed)


def checktick(planets, galaxies, alliances):
    # Skip first three lines of the dump, tick info is on fourth line
    planets.readline();planets.readline();planets.readline();
    # Parse the fourth line and check we have a number
    tick=planets.readline()
    m=re.search(r"tick:\s+(\d+)",tick,re.I)
    if not m:
        print "Invalid tick: '%s'" % (tick,)
        time.sleep(120)
        return False
    planet_tick=int(m.group(1))
    print "Planet dump for tick %s" % (planet_tick,)

    # As above
    galaxies.readline();galaxies.readline();galaxies.readline();
    tick=galaxies.readline()
    m=re.search(r"tick:\s+(\d+)",tick,re.I)
    if not m:
        print "Invalid tick: '%s'" % (tick,)
        time.sleep(120)
        return False
    galaxy_tick=int(m.group(1))
    print "Galaxy dump for tick %s" % (galaxy_tick,)

    # As above
    alliances.readline();alliances.readline();alliances.readline();
    tick=alliances.readline()
    m=re.search(r"tick:\s+(\d+)",tick,re.I)
    if not m:
        print "Invalid tick: '%s'" % (tick,)
        time.sleep(120)
        return False
    alliance_tick=int(m.group(1))
    print "Alliance dump for tick %s" % (alliance_tick,)

    # Check the ticks of the dumps are all the same and that it's
    #  greater than the previous tick, i.e. a new tick
    if not (planet_tick == galaxy_tick  == alliance_tick):
        print "Varying ticks found, sleeping\nPlanet: %s, Galaxy: %s, Alliance: %s" % (planet_tick,galaxy_tick,alliance_tick)
        time.sleep(30)
        return False
    return planet_tick


def load_config():
    if os.path.isfile("dump_info"):
        info = open("dump_info", "r+")
        last_tick = int(info.readline()[:-1] or 0)
        etag = info.readline()[:-1]
        if etag == "None":
            etag = None
        modified = info.readline()[:-1]
        if modified == "None":
            modified = None
        info.seek(0)
    else:
        info = open("dump_info", "w")
        last_tick = 0
        etag = None
        modified = None
    return (info, last_tick, etag, modified)

def ticker(alt=False):

    t_start=time.time()
    t1=t_start

    (info, last_tick, etag, modified) = load_config()

    while True:
        try:
            # How long has passed since starting?
            # If 55 mins, we're not likely getting dumps this tick, so quit
            if (time.time() - t_start) >= (55 * 60):
                print "55 minutes without a successful dump, giving up!"
                info.close()
                sys.exit()
    
            (planets, galaxies, alliances, feed) = get_dumps(last_tick, etag, modified, alt)
            if not planets:
                continue

            # Get header information now, as the headers will be lost if we save dumps
            etag = planets.headers.get("ETag")
            modified = planets.headers.get("Last-Modified")
    
            try:
                os.makedirs("dumps/%s" % (last_tick+1,))
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            # Open dump files
            pf = open("dumps/%s/planet_listing.txt" % (last_tick+1,), "w+")
            gf = open("dumps/%s/galaxy_listing.txt" % (last_tick+1,), "w+")
            af = open("dumps/%s/alliance_listing.txt" % (last_tick+1,), "w+")
            ff = open("dumps/%s/user_feed.txt" % (last_tick+1,), "w+")
            # Copy dump contents
            shutil.copyfileobj(planets, pf)
            shutil.copyfileobj(galaxies, gf)
            shutil.copyfileobj(alliances, af)
            shutil.copyfileobj(feed, ff)
            # Return to the start of the file
            pf.seek(0)
            gf.seek(0)
            af.seek(0)
            ff.close()
            # Swap pointers
            planets = pf
            galaxies = gf
            alliances = af
    
            planet_tick = checktick(planets, galaxies, alliances)
            if not planet_tick:
                continue
    
            if not planet_tick > last_tick:
                print "Stale ticks found, sleeping"
                time.sleep(60)
                continue
    
            t2=time.time()-t1
            print "Loaded dumps from webserver in %.3f seconds" % (t2,)
            t1=time.time()
    
            if planet_tick > last_tick + 1:
                if not alt:
                    print "Missing ticks. Switching to alternative url...."
                    ticker(planet_tick-1)
                    (info, last_tick, etag, modified) = load_config()
                    continue
                if planet_tick > alt:
                    print "Something is very, very wrong..."
                    continue
            info.write(str(planet_tick)+"\n"+str(etag)+"\n"+str(modified)+"\n")
            if planet_tick < alt:
                info.flush()
                info.seek(0)
                print "Still some missing... (waiting 60 seconds)"
                time.sleep(60)
                ticker(alt)
            else:
                info.write(str(planet_tick)+"\n"+str(etag)+"\n"+str(modified)+"\n")
    
            break
        except Exception, e:
            print "Something random went wrong, sleeping for 15 seconds to hope it improves: %s" % (str(e),)
            time.sleep(15)
            continue

    info.close()

    t1=time.time()-t_start
    print "Total time taken: %.3f seconds" % (t1,)
    return planet_tick

print "Dumping from %s" % (base_url,)

planet_tick = ticker()
