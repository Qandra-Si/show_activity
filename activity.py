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

first_time_characters = Set()
# type_id: 1 - attacker, 2 - victim, 3 - npc
def pushPilotAnalytics(pilot_id, system_id, location_id, type_id):
    if not pilot_id in first_time_characters:
        first_time_characters.add(pilot_id)
        g_cached_pilots_stat.append({"id":int(pilot_id),"cnt":0,"where":[]})
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

g_cached_killmails.sort(key=lambda x: x["time"])
for k in g_cached_killmails:
    unix_timestamp = float(k["time"])
    id = int(k["id"])
    system_id = int(k["system"])
    location_id = int(k["location"])
    npc = k["npc"]
    corporation_ids = []
    for pilot_id in k["attackers"]:
        pushPilotAnalytics(pilot_id, system_id, location_id, 1)
        pilot_details = getCharacter(pilot_id)
        if not pilot_details["corporation_id"] is None:
            corporation_ids.append(pilot_details["corporation_id"])
    for pilot_id in k["victim"]:
        pushPilotAnalytics(pilot_id, system_id, location_id, 2 if not npc else 3)
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
glf.write('<html><head><style>\n')
glf.write('body { margin: 0; padding: 0; background-color: #101010; overflow-y: hidden; }\n')
glf.write('h3 { margin-bottom: 0px }\n')
glf.write('body, html { min-height: 100vh; overflow-x: hidden; box-sizing: border-box; line-height: 1.5; color: #fff; font-family: Shentox,Rogan,sans-serif; }\n')
glf.write('table { border-collapse: collapse; border: none; }\n')
glf.write('th,td { border: 1px solid gray; text-align: left; vertical-align: top; }\n')
glf.write('td.attacks { text-align: right; color: green; }\n')
glf.write('td.victims { text-align: right; color: maroon; }\n')
glf.write('td.npc { text-align: right; color: #9933cc; }\n')
glf.write('div p, .div p { margin:0px; color:#888; }\n')
glf.write('p a, .p a, h3 a, .h3 a { color: #2a9fd6; text-decoration: none; }\n')
glf.write('</style></head><body>\n')

# Most dangerous locations
glf.write('<h2>Most PvP-violent locations in region</h2>\n')
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
glf.write('</table>\n')

# Pilots stat
glf.write('<h2>Pilots activity</h2>\n')
for pilot in g_cached_pilots_stat:
    pilot_id = pilot["id"]
    pilot_details = getCharacter(pilot_id)
    if pilot_details["alliance_id"] is None:
        glf.write('<div><div style="float:left"><img src="https://images.evetech.net/corporations/{cid}/logo?size=64"></div><div>\n'.format(cid=pilot_details["corporation_id"]))
    else:
        glf.write('<div><div style="float:left"><img src="https://images.evetech.net/alliances/{aid}/logo?size=64"></div><div>\n'.format(aid=pilot_details["alliance_id"]))
    glf.write('<h3><a href="https://zkillboard.com/character/{id}/">{name}</a></h3>\n'.format(id=pilot_id,name=pilot_details["name"]))
    if pilot_details["corporation_name"] is None:
        glf.write('<p>Corporation: <a href="https://zkillboard.com/corporation/{cid}/">Corp. {cid}</a></br>\n'.format(cid=pilot_details["corporation_id"]))
    else:
        glf.write('<p>Corporation: <a href="https://zkillboard.com/corporation/{cid}/">{cname}</a> [{cticker}]</br>\n'.format(cid=pilot_details["corporation_id"],cname=pilot_details["corporation_name"],cticker=pilot_details["corporation_ticker"]))
    if pilot_details["alliance_id"] is None:
        glf.write('</br>')
    elif pilot_details["alliance_name"] is None:
        glf.write('Alliance: <a href="https://zkillboard.com/alliance/{aid}/">Alli. {aid}</a>'.format(aid=pilot_details["alliance_id"]))
    else:
        glf.write('Alliance: <a href="https://zkillboard.com/alliance/{aid}/">{aname}</a> &lt;{aticker}&gt;'.format(aid=pilot_details["alliance_id"],aname=pilot_details["alliance_name"],aticker=pilot_details["alliance_ticker"]))
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
glf.write('<p><small style="color:gray">Generated {dt} with help of <a href="https://github.com/Qandra-Si/show_activity" style="color:gray">https://github.com/Qandra-Si/show_activity</a></small></p>'.format(dt=datetime.fromtimestamp(time.time(), g_local_timezone).strftime('%Y-%m-%d %H:%M:%S %z (%a, %m %b %Y %H:%M:%S %z)')))
# Don't remove line above !
glf.write('</body></html>\n')
glf.close()
# ------------------------------------------------------------------------------------------------
