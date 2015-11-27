# Module by ChronoX

from Core.loadable import loadable, route
from Core.maps import Updates
from Core.paconf import PA
 
class bonus(loadable):
    """Calculates upgrade bonus for a given tick, or for the current tick."""
    usage = " [tick]"
 
    @route(r"(\d+)?")
    def bonus(self, message, user, params):
 
        # Check if tick is provided
        tick = int(params.group(1) or 0)

        if tick > PA.getint("numbers","last_tick"):
            message.reply("Use your bonus during the round, not after.")
            return
 
        # If there is no tick provided in the command then check what the current tick is.
        if not tick:
            # Retrieve current tick
            tick = Updates.current_tick()
            if not tick:
                # Game not ticking yet.
                message.reply("Game is not ticking yet!")
                return
 
        resources = 10000 + tick * 4800
        roids = int(6 + tick * 0.15)
        research = 4000 + tick * 24
        construction = 2000 + tick * 18
 
        message.reply("Upgrade Bonus calculation for tick {} | Resources: {:,} EACH | Roids: {:,} EACH | Research Points: {:,} | Construction Units: {:,}".format(tick, resources, roids, research, construction))
