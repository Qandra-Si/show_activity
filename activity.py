import urllib2
import urllib
import json
import gzip
import sys
import os
from datetime import date
from datetime import datetime
from StringIO import StringIO
import time
from datetime import datetime
import yaml # pip install pyyaml
from sets import Set
import sys
import tzlocal  # pip install tzlocal
import array as arr

# Global settings
execfile("{cwd}/activity_settings.py".format(cwd=os.path.dirname(os.path.abspath(__file__))))
g_debug = True # show additional information (debug mode)
g_utc_offset = (datetime.fromtimestamp(1288483950000*1e-3) - datetime.utcfromtimestamp(1288483950000*1e-3)).total_seconds() # don't need tzlocal
g_local_timezone = tzlocal.get_localzone()

# Local settings
g_debug = True # show additional information (debug mode)
g_offline_mode = False # use only cached data


g_cached_solar_systems = []
g_cached_killmails = []
g_cached_pilots_stat = []
g_cached_systems_stat = []
g_cached_alliance_corporations = []
g_characters = []
g_sde_uniq_names_1 = []
g_sde_uniq_names_2 = []
g_sde_uniq_names_3 = []


def getTimestamp(datetime_str):
    dt = datetime.strptime(datetime_str,'%Y-%m-%dT%H:%M:%SZ')
    return int(time.mktime(dt.timetuple()))

def pushSolarSystem(id, name):
    g_cached_solar_systems.append({"id":int(id),"name":name.replace('\\','/')})

def getSolarSystemName(id):
    for s in g_cached_solar_systems:
        if int(id)==int(s["id"]):
            return s["name"]
    #return id
    print('Unknown solar system name {id}'.format(id=id))
    sys.stdout.flush()
    raise ValueError(id)

def getSolarSystemId(nm):
    for s in g_cached_solar_systems:
        if nm==s["name"]:
            return int(s["id"])
    #return id
    print('Unknown solar system id {name}'.format(name=nm))
    sys.stdout.flush()
    raise ValueError(nm)

def pushSolarSystemKillmail(id, datetime_str, attackers, victim, solar_system_id, location_id, npc):
    g_cached_killmails.append({
        "id":int(id),
        "time":getTimestamp(datetime_str),
        "attackers":attackers,
        "victim":victim,
        "system":int(solar_system_id),
        "location":int(location_id),
        "npc":npc
    })

# type=0 : https://esi.evetech.net/
# type=1 : https://zkillboard.com/
def getJson(type,renew_cache,suburl):
    fdir = '{tmp}/{type}/{suburl}'.format(type=type,tmp=g_tmp_directory,suburl=suburl)
    fname = '{dir}/data.json'.format(dir=fdir)
    if not renew_cache and os.path.isfile(fname):
        lfr = open(fname,"rt")
        s = lfr.read()
        json_data = (json.loads(s))
        #if g_debug:
        #    print(s)
        #    print(json.dumps(json_data, indent=4, sort_keys=True))
        lfr.close()
    elif g_offline_mode:
        json_data = (json.loads('[]'))
    else: # online mode
        if type==0:
            url = 'https://esi.evetech.net/latest/{esi}/?datasource={server}'.format(esi=suburl,server=g_eveserver)
            #headers={'Content-Type': 'application/json'}
            #req.addheaders = [('Content-Type', 'application/json')]
        else:
            url = 'https://zkillboard.com/api/{api}/'.format(api=suburl)
            #req.addheaders = [('Content-Type', 'application/json')]
            #headers=[{'Content-Type': 'application/json'},{'Accept-Encoding': 'gzip'},{'Maintainer': 'Alexander alexander.bsrgin@yandex.ru'}]
        if g_debug:
            print(url)
            sys.stdout.flush()
        req = urllib2.Request(url)
        if type==0:
            req.add_header('Content-Type', 'application/json')
        else:
            req.add_header('Accept-Encoding', 'gzip')
            req.add_header('User-Agent', g_user_agent)
        f = urllib2.urlopen(req)
        if f.info().get('Content-Encoding') == 'gzip':
            buffer = StringIO(f.read())
            deflatedContent = gzip.GzipFile(fileobj=buffer)
            s = deflatedContent.read()
        else:
            s = f.read().decode('utf-8')
        f.close()
        json_data = (json.loads(s))
        #if g_debug:
        #    print(s)
        #    print(json.dumps(json_data, indent=4, sort_keys=True))
        if not os.path.isdir(fdir):
            os.makedirs(fdir)
        lfr = open(fname,"wt+")
        lfr.write(s)
        lfr.close()
        time.sleep(3) # Do not hammer the server with API requests. Be polite.
        #if int(g_prev_get_json_type) == int(type):
        #    time.sleep(10) # Do not hammer the server with API requests. Be polite.
        #else:
        #    time.sleep(5) # Do not hammer the server with API requests. Be polite.
        #    g_prev_get_json_type = type
    return json_data

# type=2 : unpacked SDE-yyyymmdd-TRANQUILITY.zip
def getYaml(type,suburl):
    fname = '{tmp}/{type}/{suburl}'.format(type=type,tmp=g_tmp_directory,suburl=suburl)
    f = open(fname,"rt")
    s = f.read()
    yaml_data = yaml.load(s, Loader=yaml.FullLoader)
    #if g_debug:
    #    print(s)
    #    print(yaml.dump(yaml_data))
    f.close()
    return yaml_data

def loadCharacter(id):
    for c in g_characters:
        if int(id)!=int(c["id"]): continue
        return
    # curl -X GET "https://esi.evetech.net/latest/characters/631632288/?datasource=tranquility" -H "accept: application/json"
    who = getJson(0,False,'characters/{who}'.format(who=id))
    if not 'name' in who: return # offline mode? and there are no data? (skip)
    # curl -X GET "https://esi.evetech.net/latest/alliances/99009962/?datasource=tranquility" -H  "accept: application/json"
    alli = None
    if 'alliance_id' in who:
        alli = getJson(0,False,'alliances/{alliance_id}'.format(alliance_id=who["alliance_id"]))
        if not 'name' in alli: alli = None # offline mode? and there are no data? (skip)
    # curl -X GET "https://esi.evetech.net/latest/corporations/98550411/?datasource=tranquility" -H  "accept: application/json"
    corp = getJson(0,False,'corporations/{corporation_id}'.format(corporation_id=who["corporation_id"]))
    if not 'name' in corp: corp = None # offline mode? and there are no data? (skip)
    corporation_id = int(who["corporation_id"])
    corporation_name = corp["name"] if not corp is None else None
    corporation_ticker = corp["ticker"] if not corp is None else None
    alliance_id = int(who["alliance_id"]) if 'alliance_id' in who else None
    alliance_name = alli["name"] if not alli is None else None
    alliance_ticker = alli["ticker"] if not alli is None else None
    g_characters.append({
        "id":int(id),"name":who["name"],
        "corporation_id":int(corporation_id),"corporation_name":corporation_name,"corporation_ticker":corporation_ticker,
        "alliance_id":alliance_id,"alliance_name":alliance_name,"alliance_ticker":alliance_ticker
    })
    if 'alliance_id' in who:
        found = False
        for c in g_cached_alliance_corporations:
            if corporation_id == c["id"]:
                found = True
                break
        if not found:
            g_cached_alliance_corporations.append({"id":corporation_id,"alliance_id":alliance_id})

def getCharacter(id):
    for c in g_characters:
        if int(id)!=int(c["id"]): continue
        return c
    return {"id":id,"name":id}

def getLocationName(id):
    for n in g_sde_uniq_names_1:
        if int(n[0]) == id:
            return n[1]
        elif int(n[0]) > id: # sorted
            break
    for n in g_sde_uniq_names_2:
        if int(n[0]) == id:
            return n[1]
        elif int(n[0]) > id: # sorted
            break
    return id

def getItemName(id):
    for n in g_sde_uniq_names_3:
        if int(n[0]) == id:
            return n[1]
        elif int(n[0]) > id: # sorted
            break
    return id

first_time_characters = Set()
def pushPilotIntoCache(pilot_id):
    if not pilot_id in first_time_characters:
        first_time_characters.add(pilot_id)
        g_cached_pilots_stat.append({"id":int(pilot_id),"cnt":0,"where":[],"gangs":[],"ships":[]})

# type_id: 1 - attacker, 2 - victim, 3 - npc
def pushPilotAnalytics(pilot_id, system_id, location_id, type_id):
    pushPilotIntoCache(pilot_id)
    pilot = [item for item in g_cached_pilots_stat if item["id"] == int(pilot_id)]
    pilot[0]["cnt"] = pilot[0]["cnt"] + 1
    num_attacker = 1 if 1 == type_id else 0
    num_victim = 1 if 2 == type_id else 0
    num_npc = 1 if 3 == type_id else 0
    found_sys = False
    for s in pilot[0]["where"]:
        if s["system"] == int(system_id):
            found_loc = False
            for l in s["locations"]:
                if l["id"] == int(location_id):
                    l["attacker"] = l["attacker"] + num_attacker
                    l["victim"] = l["victim"] + num_victim
                    l["npc"] = l["npc"] + num_npc
                    found_loc = True
                    break
            if not found_loc:
                s["locations"].append({"id":int(location_id),"attacker":num_attacker,"victim":num_victim,"npc":num_npc})
            found_sys = True
            break
    if not found_sys:
        pilot[0]["where"].append({"system":int(system_id),"locations":[{"id":int(location_id),"attacker":num_attacker,"victim":num_victim,"npc":num_npc}]})

def pushPilotFleetAnalytics(pilot_id, ship_type, gang_size):
    pushPilotIntoCache(pilot_id)
    pilot = [item for item in g_cached_pilots_stat if item["id"] == int(pilot_id)]
    if not gang_size is None: # None for victim's
        pilot[0]["gangs"].append(gang_size)
    found_ship = False
    for s in pilot[0]["ships"]:
        if s["id"] == int(ship_type):
            s["cnt"] = s["cnt"] + 1
            found_ship = True
            break
    if not found_ship:
        pilot[0]["ships"].append({"id":int(ship_type),"cnt":1})

def pushFleetAnalytics(pilots, gang_size):
    for p in pilots:
        pushPilotFleetAnalytics(int(p["id"]), int(p["ship"]), gang_size)



# ------------------------------------------------------------------------------------------------
print('Loading names of locations (and other unique names)...')
sys.stdout.flush()
iuncnm = '{tmp}/unique_names_cache_1.json'.format(tmp=g_tmp_directory)
if os.path.isfile(iuncnm):
    jnr = open(iuncnm,"rt")
    s = jnr.read()
    g_sde_uniq_names_1 = (json.loads(s))
    jnr.close()

else:
    un_yaml = getYaml(2,'sde/bsd/invUniqueNames.yaml')
    g_sde_uniq_names_1 = []
    for n in un_yaml:
        g_sde_uniq_names_1.append([int(n["itemID"]),n["itemName"]])
    un_yaml = []
    
    g_sde_uniq_names_1.sort(key=lambda x: x[0])
    jnw = open(iuncnm, "wt+")
    jnw.write(json.dumps(g_sde_uniq_names_1, indent=1, sort_keys=False))
    jnw.close()
#if g_debug:
#    print(json.dumps(g_sde_uniq_names_1, indent=1, sort_keys=False))
print('Found {num} unique names in invUniqueNames.yaml'.format(num=len(g_sde_uniq_names_1)))
sys.stdout.flush()

iuncnm = '{tmp}/unique_names_cache_2.json'.format(tmp=g_tmp_directory)
if os.path.isfile(iuncnm):
    jnr = open(iuncnm,"rt")
    s = jnr.read()
    g_sde_uniq_names_2 = (json.loads(s))
    jnr.close()

else:
    un_yaml = getYaml(2,'sde/bsd/invNames.yaml')
    g_sde_uniq_names_2 = []
    for n in un_yaml:
        g_sde_uniq_names_2.append([int(n["itemID"]),n["itemName"]])
    un_yaml = []
    
    g_sde_uniq_names_2.sort(key=lambda x: x[0])
    jnw = open(iuncnm, "wt+")
    jnw.write(json.dumps(g_sde_uniq_names_2, indent=1, sort_keys=False))
    jnw.close()
#if g_debug:
#    print(json.dumps(g_sde_uniq_names_2, indent=1, sort_keys=False))
print('Found {num} unique names in invNames.yaml'.format(num=len(g_sde_uniq_names_2)))
sys.stdout.flush()

sys.stdout.flush()
iuncnm = '{tmp}/unique_names_cache_3.json'.format(tmp=g_tmp_directory)
if os.path.isfile(iuncnm):
    jnr = open(iuncnm,"rt")
    s = jnr.read()
    g_sde_uniq_names_3 = (json.loads(s))
    jnr.close()

else:
    un_yaml = getYaml(2,'sde/fsd/typeIDs.yaml')
    g_sde_uniq_names_3 = []
    for n in un_yaml:
        if 'name' in un_yaml[n] and 'en' in un_yaml[n]["name"]:
            g_sde_uniq_names_3.append([n,un_yaml[n]["name"]["en"]])
    un_yaml = []
    
    g_sde_uniq_names_3.sort(key=lambda x: x[0])
    jnw = open(iuncnm, "wt+")
    jnw.write(json.dumps(g_sde_uniq_names_3, indent=1, sort_keys=False))
    jnw.close()
#if g_debug:
#    print(json.dumps(g_sde_uniq_names_3, indent=1, sort_keys=False))
print('Found {num} unique names in typeIDs.yaml'.format(num=len(g_sde_uniq_names_3)))
sys.stdout.flush()
# ------------------------------------------------------------------------------------------------




# ------------------------------------------------------------------------------------------------
#example:shafrak = getYaml(2,'sde/fsd/universe/eve/Aridia\Leseasesh\Shafrak/solarsystem.staticdata')
#example:print(shafrak)
print('Loading solar systems from filesystem...')
sys.stdout.flush()
sscnm = '{tmp}/solar_systems_cache.json'.format(tmp=g_tmp_directory)
if os.path.isfile(sscnm):
    sscr = open(sscnm,"rt")
    s = sscr.read()
    g_cached_solar_systems = (json.loads(s))
    sscr.close()

else:
    print('  loading solar systems from Wormholes...')
    sys.stdout.flush()
    sde_universe_path = '{tmp}/2/sde/fsd/universe/wormhole'.format(tmp=g_tmp_directory)
    for path, dirs, files in os.walk(sde_universe_path):
        for f in files:
            #if g_debug:
            #    print('{}/{}'.format(path,f))
            suburl = path.replace('{tmp}/2/'.format(tmp=g_tmp_directory),'')
            solar_system = getYaml(2,'{}/{}'.format(suburl,f))
            if 'solarSystemID' in solar_system:
                id = int(solar_system["solarSystemID"])
                nm = getLocationName(id)
                #print('{} = {}'.format(nm,id))
                pushSolarSystem(id,nm)
    
    print('  loading solar systems from Universe...')
    sys.stdout.flush()
    sde_universe_path = '{tmp}/2/sde/fsd/universe/eve'.format(tmp=g_tmp_directory)
    for path, dirs, files in os.walk(sde_universe_path):
        for f in files:
            #if g_debug:
            #    print('{}/{}'.format(path,f))
            suburl = path.replace('{tmp}/2/'.format(tmp=g_tmp_directory),'')
            solar_system = getYaml(2,'{}/{}'.format(suburl,f))
            if 'solarSystemID' in solar_system:
                id = int(solar_system["solarSystemID"])
                nm = getLocationName(id)
                #print('{} = {}'.format(nm,id))
                pushSolarSystem(id,nm)
    
    sscw = open(sscnm, "wt+")
    sscw.write(json.dumps(g_cached_solar_systems, indent=1, sort_keys=False))
    sscw.close()
#if g_debug:
#    print(json.dumps(g_cached_solar_systems, indent=1, sort_keys=False))
print('Found {num} solar systems in eve university'.format(num=len(g_cached_solar_systems)))
sys.stdout.flush()
# ------------------------------------------------------------------------------------------------



# ------------------------------------------------------------------------------------------------
now_ts = int(time.time())
now_year = date.today().year
now_month = date.today().month
start_date_ts = getTimestamp(g_start_date)
start_date_year = int(g_start_date[:4])
start_date_month = int(g_start_date[5:7])
print('Fetching from {year}-{month} to {tyear}-{tmonth} ({now})'.format(year=start_date_year,month=start_date_month,tyear=now_year,tmonth=now_month,now=now_ts))
sys.stdout.flush()

# curl -X GET "https://zkillboard.com/api/solarSystemID/30004283/startTime/202004010000/page/1/" -H "accept: application/json"
print('Start activity processing of {num} solar systems:'.format(num=len(g_solar_systems)))
for system_name in g_solar_systems:
    system_id = int(getSolarSystemId(system_name))
    print('  {} = {}'.format(system_id,system_name))
    zkillmails_num = 0
    for y in range(start_date_year,now_year+1):
        if y==start_date_year:
            m0 = start_date_month
        else:
            m0 = 1
        if y==now_year:
            m1 = now_month
        else:
            m1 = 12
        for m in range(m0,m1+1):
            start = '{:04d}{:02d}01000000'.format(y,m)
            if m<12:
                end = '{:04d}{:02d}01000000'.format(y,m+1)
            else:
                end = '{:04d}0101000000'.format(y+1)
            page = 1
            if now_year == y and m == now_month:
                renew_cache = True # renew killmails by current month
            else:
                renew_cache = False
            while True:
                zkillmails = getJson(1,renew_cache,'solarSystemID/{system}/startTime/{start}/endTime/{end}/page/{page}'.format(system=system_id,start=start,end=end,page=page))
                zkillmails_num = zkillmails_num + len(zkillmails)
                #print(json.dumps(killmails, indent=4, sort_keys=False))
                for zkill in zkillmails:
                    # https://zkillboard.com/api/killID/80970275/
                    id = int(zkill["killmail_id"])
                    zkillmail = getJson(1,False,'killID/{id}'.format(id=id))
                    # curl -X GET "https://esi.evetech.net/latest/killmails/73216307/e015e69931dd8a22a10d0d439ca3ec45503498cc/?datasource=tranquility" -H "accept: application/json"
                    killmail = getJson(0,False,'killmails/{id}/{hash}'.format(id=id,hash=zkill["zkb"]["hash"]))
                    location_id = 0
                    if 'locationID' in zkill["zkb"]:
                        location_id = zkill["zkb"]["locationID"]
                    if not 'attackers' in killmail and not 'victim' in killmail:
                        break # offline mode? and there are no data? (skip)
                    npc = True if zkill["zkb"]["npc"] else False
                    # getting attackers and victim
                    attackers = []
                    victim = []
                    if 'attackers' in killmail:
                        for a in killmail["attackers"]:
                            if 'character_id' in a:
                                attackers.append(int(a["character_id"]))
                                loadCharacter(int(a["character_id"]))
                    if 'victim' in killmail:
                        v = killmail["victim"]
                        if 'character_id' in v:
                            victim.append(int(v["character_id"]))
                            loadCharacter(int(v["character_id"]))
                    pushSolarSystemKillmail(id, killmail["killmail_time"], attackers, victim, killmail["solar_system_id"], location_id, npc)
                    # getting pilot' ship types
                    attackers = []
                    victim = []
                    if 'attackers' in killmail:
                        for a in killmail["attackers"]:
                            if 'character_id' in a and 'ship_type_id' in a:
                                attackers.append({"id":int(a["character_id"]),"ship":int(a["ship_type_id"])})
                    if 'victim' in killmail:
                        v = killmail["victim"]
                        if 'character_id' in v and 'ship_type_id' in v:
                            victim.append({"id":int(v["character_id"]),"ship":int(v["ship_type_id"])})
                    if len(attackers) > 0:
                        pushFleetAnalytics(attackers, len(attackers))
                    if len(victim) > 0:
                        pushFleetAnalytics(victim, None)
                    # ---
                if len(zkillmails)<200:
                    break
                else:
                    page = page + 1
    print('  found {num} killmails in {snm}'.format(num=zkillmails_num,snm=system_name))
    sys.stdout.flush()
# ------------------------------------------------------------------------------------------------




# ------------------------------------------------------------------------------------------------
print('Analysis of killmails log...')
sys.stdout.flush()

def pushSolarSystemAnalytics(system_id, location_id, corporation_ids):
    found_sys = False
    for s in g_cached_systems_stat:
        if s["system"] == int(system_id):
            found_sys = True
            break
    if not found_sys:
        g_cached_systems_stat.append({"system":int(system_id),"cnt":0,"corporations":[],"alliances":[],"locations":[]})
    for s in g_cached_systems_stat:
        if s["system"] == int(system_id):
            for corporation_id in corporation_ids:
                alliance_id = None
                for c in g_cached_alliance_corporations:
                    if corporation_id == c["id"]:
                        alliance_id = c["alliance_id"]
                        break
                if alliance_id is None:
                    found_corp = False
                    for c in s["corporations"]:
                        if c["id"] == int(corporation_id):
                            c["cnt"] = c["cnt"] + 1
                            found_corp = True
                            break
                    if not found_corp:
                        s["corporations"].append({"id":int(corporation_id),"cnt":1})
                else:
                    found_alli = False
                    for c in s["alliances"]:
                        if c["id"] == int(alliance_id):
                            c["cnt"] = c["cnt"] + 1
                            found_alli = True
                            break
                    if not found_alli:
                        s["alliances"].append({"id":int(alliance_id),"cnt":1})
            found_loc = False
            for l in s["locations"]:
                if l["id"] == int(location_id):
                    l["cnt"] = l["cnt"] + 1
                    found_loc = True
                    break
            if not found_loc:
                s["locations"].append({"id":int(location_id),"cnt":1})
            s["cnt"] = s["cnt"] + 1
            break

# g_cached_killmails.sort(key=lambda x: x["time"])
for k in g_cached_killmails:
    # unix_timestamp = float(k["time"])
    # id = int(k["id"])
    system_id = int(k["system"])
    location_id = int(k["location"])
    npc = k["npc"]
    corporation_ids = []
    for pilot_id in k["attackers"]:
        pushPilotAnalytics(int(pilot_id), system_id, location_id, 1)
        pilot_details = getCharacter(int(pilot_id))
        if not pilot_details["corporation_id"] is None:
            corporation_ids.append(pilot_details["corporation_id"])
    for pilot_id in k["victim"]:
        pushPilotAnalytics(int(pilot_id), system_id, location_id, 2 if not npc else 3)
    if not npc:
        pushSolarSystemAnalytics(system_id, location_id, corporation_ids)

g_cached_systems_stat.sort(key=lambda x: x["cnt"], reverse=True)
for s in g_cached_systems_stat:
    s["corporations"].sort(key=lambda x: x["cnt"], reverse=True)
    s["alliances"].sort(key=lambda x: x["cnt"], reverse=True)
    s["locations"].sort(key=lambda x: x["cnt"], reverse=True)
g_cached_pilots_stat.sort(key=lambda x: x["cnt"], reverse=True)
for pilot in g_cached_pilots_stat:
    for where in pilot["where"]:
        where["locations"].sort(key=lambda x: x["attacker"]+x["victim"]+x["npc"], reverse=True)
    pilot["ships"].sort(key=lambda x: x["cnt"], reverse=True)
    # calc gang size and solo times
    gang_size = 0
    solo_percent = 0
    if len(pilot["gangs"]) > 0:
        for g in pilot["gangs"]:
            if g == 1:
                solo_percent = solo_percent + 1
            else:
                gang_size = gang_size + g
        if 0 == gang_size:
            pilot["solo"] = 100.0
        else:
            gang_size = int(float(gang_size) / float(len(pilot["gangs"])-solo_percent) + 0.5)
            pilot["gang_size"] = int(gang_size)
            pilot["solo"] = float(solo_percent) / float(len(pilot["gangs"])) * 100.0
    del pilot["gangs"]

if g_debug:
    gckmw = open('{tmp}/killmails.json'.format(tmp=g_tmp_directory), "wt+")
    gckmw.write(json.dumps(g_cached_killmails, indent=1, sort_keys=False))
    gckmw.close()
    
    gcssw = open('{tmp}/systems.json'.format(tmp=g_tmp_directory), "wt+")
    gcssw.write(json.dumps(g_cached_systems_stat, indent=1, sort_keys=False))
    gcssw.close()
    
    gcpsw = open('{tmp}/pilots.json'.format(tmp=g_tmp_directory), "wt+")
    gcpsw.write(json.dumps(g_cached_pilots_stat, indent=1, sort_keys=False))
    gcpsw.close()
# ------------------------------------------------------------------------------------------------




# ------------------------------------------------------------------------------------------------
print('Building report...')
sys.stdout.flush()

glf = open('{tmp}/report.html'.format(tmp=g_tmp_directory), "wt+")
glf.write("""<html><head><style>
body { margin: 0; padding: 0; background-color: #101010; overflow-y: hidden; }
h2 { margin-bottom: 3px }
h3 { margin-bottom: 0px }
body, html { min-height: 100vh; overflow-x: hidden; box-sizing: border-box; line-height: 1.5; color: #fff; font-family: Shentox,Rogan,sans-serif; }
table { border-collapse: collapse; border: none; }
th,td { border: 1px solid gray; text-align: left; vertical-align: top; }
td.attacks { text-align: right; color: green; }
td.victims { text-align: right; color: maroon; }
td.npc { text-align: right; color: #9933cc; }
div p, .div p { margin:0px; color:#888; }
p a, .p a, h3 a, .h3 a { color: #2a9fd6; text-decoration: none; }
small { color:gray; }
a.inert { color:#999; }
textarea { width: 600px; border: 1px solid #666; color: #bbb; background-color: #000; }
input.btn { cursor: pointer; color: #fff; background-color: #555; display: inline-block; margin-top: 3px; white-space: nowrap; vertical-align: middle; user-select: none; border: 1px solid transparent; padding: .2rem .6rem; font-size: 1rem; line-height: 1.5; border-radius: .25rem; transition: color .15s ease-in-out,background-color .15s ease-in-out,border-color .15s ease-in-out,box-shadow .15s ease-in-out; }
input.btn:hover { background-color: #777; border-color: #888; }
textarea, input.btn, input.btn:active, input.btn:focus { outline: none; }
</style>
<script type="text/javascript">
function showAll() {
 var divs = document.getElementsByTagName("div");
 for(var i = 0, cnt = divs.length; i < cnt; i++)
  if (divs[i].id)
   divs[i].style.display = 'block';
 document.getElementById('Paste anything').scrollIntoView();
}
function filterElements() {
 var filter = document.getElementById('Paste anything').value.split('\\n');
 var divs = document.getElementsByTagName("div");
 for(var i = 0, cnt1 = divs.length; i < cnt1; i++)
  if (divs[i].id){
   var found = 0;
   for (var j = 0, cnt2 = filter.length; j < cnt2; j++)
    if (filter[j] === divs[i].id){
     found = 1;
     break;
    }
    if (!found) divs[i].style.display = 'none';
 }
}
</script></head><body>
""")

# Most dangerous locations
glf.write('<div id="hide!me1"><h2>Most PvP-violent locations in region</h2>\n')
glf.write('<table><tr><th>Solar System</th><th>Location</th><th>Kills</th></tr>\n')
for s in g_cached_systems_stat:
    s_cnt = s["cnt"]
    if 0 == s_cnt: continue
    logo_html = ""
    most_danger_alli = None
    most_danger_corp = None
    if len(s["alliances"]) > 0:
        if len(s["corporations"]) > 0:
            if int(s["alliances"][0]["cnt"]) >= int(s["corporations"][0]["cnt"]):
                most_danger_alli = int(s["alliances"][0]["id"])
            else:
                most_danger_corp = int(s["corporations"][0]["id"])
        else:
            most_danger_alli = int(s["alliances"][0]["id"])
    elif len(s["corporations"]) > 0:
        most_danger_corp = int(s["corporations"][0]["id"])
    
    if not most_danger_alli is None:
        logo_html = '<div style="float:left"><a href="https://zkillboard.com/system/{system}/alliance/{aid}/"><img src="https://images.evetech.net/alliances/{aid}/logo?size=32"></a></div>'.format(system=s["system"],aid=int(most_danger_alli))
    elif not most_danger_corp is None:
        logo_html = '<div style="float:left"><a href="https://zkillboard.com/system/{system}/corporation/{cid}/"><img src="https://images.evetech.net/corporations/{cid}/logo?size=32"></a></div>'.format(system=s["system"],cid=int(most_danger_corp))
    quotients = arr.array('f', [])
    for loc in s["locations"]:
        l_cnt = loc["cnt"]
        quotient = float(l_cnt) / float(s_cnt) * 100.0
        if quotient < 13.0:
            if len(quotients) >= 2: break
        quotients.append(quotient)
        if 3 == len(quotients): break
    if 0 == len(quotients): continue
    glf.write('<tr><td rowspan={num} valign=top><div>{logo}<p><a href="https://zkillboard.com/system/{system}/">{system}</a></p></div></td>'.format(logo=logo_html,system=getSolarSystemName(s["system"]),num=len(quotients)))
    first = True
    l_idx = 0
    for loc in s["locations"]:
        if first:
            first = False
        else:
            glf.write('<tr>')
        q = quotients[l_idx]
        iq = int(q)
        _iq = int(100 - iq)
        l_idx = l_idx + 1
        glf.write('<td  style="background-image: linear-gradient(to right,#444444 {iq}%,black {iq}%,black {_iq}%)">{location}</td><td>{q:.1f}%</td></tr>\n'.format(location=getLocationName(loc["id"]),q=q,iq=iq,_iq=_iq))
        if l_idx == len(quotients): break
glf.write('</table></div>\n')

# Pilots stat
glf.write("""<div id="hide!me2"><h2>Pilots activity</h2></div>
<p style="margin:0;"><small>Right click on your chat transcript and select Copy All or press CTRL+A and then CTRL+C in the</br>
members panel and paste it here to get characters affiliations and PvP stats. Press ESC to reset.</small></p>
<textarea id="Paste anything" rows="10" title="Paste pilot names you managed to copy in Eve...

That means:
 CTRL+A to select all;
 CTRL+C to copy; and
 CTRL+V to paste." placeholder="Paste pilot names you managed to copy in Eve..."></textarea></br>
<input type="button" class="btn" value="Filter" onclick="filterElements()">
<input type="button" class="btn" value="Reset" onclick="showAll()">
""")
#debug:limit = 0
for pilot in g_cached_pilots_stat:
    #debug:limit = limit + 1
    #debug:if 10 == limit: break
    pilot_id = pilot["id"]
    pilot_details = getCharacter(pilot_id)
    lines = 0
    glf.write('<div id="{name}">'.format(name=pilot_details["name"]))
    # logo
    if pilot_details["alliance_id"] is None:
        glf.write('<div style="float:left"><img src="https://images.evetech.net/corporations/{cid}/logo?size=64"></div><div>\n'.format(cid=pilot_details["corporation_id"]))
    else:
        glf.write('<div style="float:left"><img src="https://images.evetech.net/alliances/{aid}/logo?size=64"></div><div>\n'.format(aid=pilot_details["alliance_id"]))
    # pilot
    glf.write('<h3><a href="https://zkillboard.com/character/{id}/">{name}</a></h3>\n'.format(id=pilot_id,name=pilot_details["name"]))
    # corporation
    if pilot_details["corporation_name"] is None:
        glf.write('<p>Corporation: <a href="https://zkillboard.com/corporation/{cid}/">Corp. {cid}</a>\n'.format(cid=pilot_details["corporation_id"]))
    else:
        glf.write('<p>Corporation: <a href="https://zkillboard.com/corporation/{cid}/">{cname}</a> [{cticker}]\n'.format(cid=pilot_details["corporation_id"],cname=pilot_details["corporation_name"],cticker=pilot_details["corporation_ticker"]))
    lines = lines + 1
    # alliance
    if not pilot_details["alliance_id"] is None:
        if pilot_details["alliance_name"] is None:
            glf.write('</br>Alliance: <a href="https://zkillboard.com/alliance/{aid}/">Alli. {aid}</a>'.format(aid=pilot_details["alliance_id"]))
        else:
            glf.write('</br>Alliance: <a href="https://zkillboard.com/alliance/{aid}/">{aname}</a> &lt;{aticker}&gt;'.format(aid=pilot_details["alliance_id"],aname=pilot_details["alliance_name"],aticker=pilot_details["alliance_ticker"]))
        lines = lines + 1
    # solo | gang size
    if 'solo' in pilot:
        glf.write('</br>Solo: <span style="color:yellow">{solo:.1f}%</span>'.format(solo=pilot["solo"]))
        if 'gang_size' in pilot:
            glf.write(' | Gang size: <b>{sz}</b>'.format(sz=int(pilot["gang_size"])))
        lines  = lines + 1
    # ships
    if len(pilot["ships"]) > 0:
        ships_cnt = 0
        fights_cnt = 0
        for s in pilot["ships"]:
            fights_cnt = fights_cnt + s["cnt"]
        glf.write('</br>Ships: <small>')
        for s in pilot["ships"]:
            if ships_cnt > 0: glf.write(' |')
            glf.write(' <span style="color:#bbb">{nm}</span> ({often:.1f}%)'.format(nm=getItemName(s["id"]),often=float(s["cnt"])/float(fights_cnt)*100.0))
            ships_cnt = ships_cnt + 1
            if 10 == ships_cnt: break
        glf.write('</small>')
    if lines < 2: glf.write('</br>')
    glf.write('</p>\n')
    
    glf.write('<table><tr><th>Solar System</th><th>Location</th><th>Attacks</th><th>Victims</th><th>NPC</th></tr>\n')
    a_all = 0
    v_all = 0
    n_all = 0
    for where in pilot["where"]:
        glf.write('<tr><td rowspan={num}>{system}</td>'.format(system=getSolarSystemName(where["system"]),num=len(where["locations"])))
        first = True
        for loc in where["locations"]:
            if first:
                first = False
            else:
                glf.write('<tr>')
            a = loc["attacker"]
            v = loc["victim"]
            n = loc["npc"]
            a_all = a_all + a
            v_all = v_all + v
            n_all = n_all + n
            glf.write('<td>{location}</td><td class=attacks>{attacker}</td><td class=victims>{victim}</td><td class=npc>{npc}</td></tr>\n'.format(location=getLocationName(loc["id"]),attacker=a if a>0 else "&nbsp;",victim=v if v>0 else "&nbsp;",npc=n if n>0 else "&nbsp;"))
    glf.write('<tr><td colspan=2>&nbsp;</td><td class=attacks>{a}</td><td class=victims>{v}</td><td class=npc>{n}</td></tr></table>\n'.format(a=a_all if a_all>0 else "&nbsp;",v=v_all if v_all>0 else "&nbsp;",n=n_all if n_all>0 else "&nbsp;"))
    
    glf.write(' </div>\n</div>\n')

# Don't remove line below !
glf.write('<p><small><small>Generated {dt}</small></br>\n'.format(dt=datetime.fromtimestamp(time.time(), g_local_timezone).strftime('%a, %d %b %Y %H:%M:%S %z')))
glf.write("""</br>
&copy; 2020 Kekuit Void &middot; <a class="inert" href="https://github.com/Qandra-Si/show_activity">GitHub</a> &middot; Data provided by <a class="inert" href="https://esi.evetech.net/">ESI</a> and <a class="inert" href="https://zkillboard.com/">zKillboard</a> &middot; Tips go to <a class="inert" href="https://zkillboard.com/character/2116129465/">Qandra Si</a></br>
</br>
<small>EVE Online and the EVE logo are the registered trademarks of CCP hf. All rights are reserved worldwide. All other trademarks are the property of their respective owners. EVE Online, the EVE logo, EVE and all associated logos and designs are the intellectual property of CCP hf. All artwork, screenshots, characters, vehicles, storylines, world facts or other recognizable features of the intellectual property relating to these trademarks are likewise the intellectual property of CCP hf.</small>
</small></p>""")
# Don't remove line above !
glf.write("""
<script type="text/javascript">
document.onkeydown = function(evt) {
    evt = evt || window.event;
    if (evt.keyCode == 27) showAll();
};
</script></body></html>
""")
glf.close()
# ------------------------------------------------------------------------------------------------
