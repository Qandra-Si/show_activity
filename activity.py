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

# Global settings
execfile("{cwd}/activity_settings.py".format(cwd=os.path.dirname(os.path.abspath(__file__))))
g_debug = True # show additional information (debug mode)
g_utc_offset = (datetime.fromtimestamp(1288483950000*1e-3) - datetime.utcfromtimestamp(1288483950000*1e-3)).total_seconds() # don't need tzlocal
g_local_timezone = tzlocal.get_localzone()

# Local settings
g_debug = True # show additional information (debug mode)
g_offline_mode = True # use only cached data


g_cached_solar_systems = []
g_cached_killmails = []
g_cached_characters = []
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

def pushSolarSystemKillmail(id, datetime_str, attackers, victim, solar_system_id, location_id):
    g_cached_killmails.append({"id":int(id),"time":getTimestamp(datetime_str),"attackers":attackers, "victim":victim, "system":int(solar_system_id),"location":int(location_id)})

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

def pushCharacter(id,name):
    g_characters.append({"id":int(id),"name":name})

def getCharacterName(id):
    for c in g_characters:
        if int(id)==int(c["id"]):
            return c["name"]
    # curl -X GET "https://esi.evetech.net/latest/characters/631632288/?datasource=tranquility" -H "accept: application/json"
    who = getJson(0,False,'characters/{who}'.format(who=id))
    if 'name' in who: # offline mode? and there are no data? (skip)
        pushCharacter(id,who["name"])
        return who["name"]
    else:
        return id

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
g_start_date = "2020-04-01T00:00:00Z"
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
                    attackers = []
                    victim = []
                    if 'attackers' in killmail:
                        for a in killmail["attackers"]:
                            if 'character_id' in a:
                                attackers.append(int(a["character_id"]))
                    if 'victim' in killmail:
                        v = killmail["victim"]
                        if 'character_id' in v:
                            victim.append(int(v["character_id"]))
                    pushSolarSystemKillmail(id, killmail["killmail_time"], attackers, victim, killmail["solar_system_id"], location_id)
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

first_time_characters = Set()
# type_id: 1 - attacker, 2 - victim
def pushPilotAnalitics(pilot_id, system_id, location_id, type_id):
    if not pilot_id in first_time_characters:
        first_time_characters.add(pilot_id)
        g_cached_characters.append({"id":int(pilot_id),"cnt":0,"where":[]})
    pilot = [item for item in g_cached_characters if item["id"] == int(pilot_id)]
    pilot[0]["cnt"] = pilot[0]["cnt"] + 1
    found_sys = False
    for s in pilot[0]["where"]:
        if s["system"] == int(system_id):
            found_loc = False
            for l in s["locations"]:
                if l["id"] == int(location_id):
                    if 1 == type_id:
                        l["attacker"] = l["attacker"] + 1
                    if 2 == type_id:
                        l["victim"] = l["victim"] + 1
                    found_loc = True
                    break
            if not found_loc:
                s["locations"].append({"id":int(location_id),"attacker":1 if type_id == 1 else 0,"victim":1 if type_id == 2 else 0})
            found_sys = True
            break
    if not found_sys:
        pilot[0]["where"].append({"system":int(system_id),"locations":[{"id":int(location_id),"attacker":1 if type_id == 1 else 0,"victim":1 if type_id == 2 else 0}]})

g_cached_killmails.sort(key=lambda x: x["time"])
for k in g_cached_killmails:
    unix_timestamp = float(k["time"])
    id = int(k["id"])
    system_id = int(k["system"])
    location_id = int(k["location"])
    for pilot_id in k["attackers"]:
        pushPilotAnalitics(pilot_id, system_id, location_id, 1)
    for pilot_id in k["victim"]:
        pushPilotAnalitics(pilot_id, system_id, location_id, 2)

g_cached_characters.sort(key=lambda x: x["cnt"], reverse=True)
for pilot in g_cached_characters:
    for where in pilot["where"]:
        where["locations"].sort(key=lambda x: x["attacker"]+x["victim"], reverse=True)

if g_debug:
    gckw = open('{tmp}/killmails.json'.format(tmp=g_tmp_directory), "wt+")
    gckw.write(json.dumps(g_cached_killmails, indent=1, sort_keys=False))
    gckw.close()
    
    gccw = open('{tmp}/pilots.json'.format(tmp=g_tmp_directory), "wt+")
    gccw.write(json.dumps(g_cached_characters, indent=1, sort_keys=False))
    gccw.close()
# ------------------------------------------------------------------------------------------------




# ------------------------------------------------------------------------------------------------
print('Building report...')
sys.stdout.flush()

glf = open('{tmp}/report.html'.format(tmp=g_tmp_directory), "wt+")
glf.write('<html><head><style>\n')
glf.write('body { margin: 0; padding: 0; background-color: #101010; overflow-y: hidden; }\n')
glf.write('body, html { min-height: 100vh; overflow-x: hidden; box-sizing: border-box; line-height: 1.5; color: #fff; font-family: Shentox,Rogan,sans-serif; }\n')
glf.write('table { border-collapse: collapse; border: none; }\n')
glf.write('th,td { border: 1px solid gray; text-align: left; vertical-align: top; }\n')
glf.write('td.attacks { text-align: right; color: green; }\n')
glf.write('td.victims { text-align: right; color: maroon; }\n')
glf.write('</style></head><body>\n')
for pilot in g_cached_characters:
    glf.write('<h3>{name}</h3>\n'.format(name=getCharacterName(pilot["id"])))
    glf.write('<table><tr><th>Solar System</th><th>Location</th><th>Attacks</th><th>Victims</th></tr>\n')
    a_all = 0
    v_all = 0
    for where in pilot["where"]:
        glf.write('<tr><td rowspan={num}>{system}</td>'.format(system=getSolarSystemName(where["system"]),num=len(where["locations"])))
        first = True
        for loc in where["locations"]:
            if first:
                first = False
            else:
                glf.write('<tr>')
            a = loc["attacker"]
            v = victim=loc["victim"]
            a_all = a_all + a
            v_all = v_all + v
            glf.write('<td>{location}</td><td class=attacks>{attacker}</td><td class=victims>{victim}</td></tr>\n'.format(location=getLocationName(loc["id"]),attacker=a if a>0 else "&nbsp;",victim=v if v>0 else "&nbsp;"))
    glf.write('<tr><td colspan=2>&nbsp;</td><td class=attacks>{a}</td><td class=victims>{v}</td></tr><table>\n'.format(a=a_all if a_all>0 else "&nbsp;",v=v_all if v_all>0 else "&nbsp;"))
glf.write('<p>Generated {dt} with help of https://github.com/Qandra-Si/show_activity</p>'.format(dt=datetime.fromtimestamp(time.time(), g_local_timezone).strftime('%Y-%m-%d %H:%M:%S %z (%a, %m %b %Y %H:%M:%S %z)')))
glf.write('</body></html>\n')
glf.close()
# ------------------------------------------------------------------------------------------------
