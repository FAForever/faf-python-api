"""
Deals with basic data passing from db
"""

from api import *

import geoip2.database

geolite2 = geoip2.database.Reader(
    '/usr/lib/python3.4/site-packages/_geoip_geolite2/GeoLite2-City.mmdb')

def dsum(a,b):
    "Sum two dicts"
    d = a
    d.update(b)
    return a

# ======== User Resources =========

@app.route('/user/<int:id>')
@app.route('/user/<int:id>/<resource>')
def user_get(id, resource='info'):
    try:
        user = User.get(User.id == id)
    except DoesNotExist:
        return 'No such user id=%d' % id, 404

    if resource == 'info':

        rating = user.ladder1v1[0]

        res = dict(
            id=user.id,
            name=user.login,
            clan='',
            country='',

            league=dict(league=1, division='todo'),
            rating=dict(mean=rating.mean, deviation=rating.deviation)
        )

        if user.ip:
            ip_info = geolite2.city(user.ip)
            if ip_info and ip_info.country:
                res['country'] = ip_info.country.iso_code

        try:
            clan = ClanMember.get(ClanMember.player == user).clan

            res['clan'] = clan.tag
        except:
            pass

        try:
            avatar = user.avatars.select().where(UserAvatar.selected == True)[0].avatar

            res['avatar'] = dict(name='',tooltip=avatar.tooltip,url=avatar.url)
        except: # If avatar does not exist
            res['avatar'] = dict(name='',tooltip='',url='')

        return res

@app.route('/user/byname/<username>')
@app.route('/user/byname/<username>/<resource>')
def user_byname_get(username, resource='info'):
    try:
        user = User.get(User.login == username)
    except DoesNotExist:
        return 'No such user name=%s' % username, 404

    return user_get(user.id, resource)

# ======== Version Resources =========

@app.route('/version/repo/<int:id>')
def version_repo_get(id):
    ver = RepoVersion.get(RepoVersion.id == id)
    return ver.dict()

@app.route('/version/map/<int:id>')
def version_map_get(id):
    ver = MapVersion.get(MapVersion.id == id)
    return ver.dict()

@app.route('/version/mod/<int:id>')
def version_mod_get(id):
    ver = ModVersion.get(ModVersion.id == id)

    result = ver.dict()
    result['requires'] = [x.depend.dict() for x in ver.depends]
    return result

@app.route('/version/default/<mod_name>')
def version_default_get(mod_name):
    versions = DefaultVersion.select().where(DefaultVersion.mod == mod_name)

    result = []

    for ver in [x.dict() for x in versions]:
        ver['ver_engine'] = RepoVersion.get(RepoVersion.id == ver['ver_engine']).dict()
        ver['ver_main_mod'] = RepoVersion.get(RepoVersion.id == ver['ver_main_mod']).dict()

        result.append(ver)

    return result

# ============ Map Resources ==============

@app.route('/map/notes')
def map_list_notes():
    return [
        note.dict() for note in MapNote.select()
    ]

@app.route('/map/<int:id>', defaults=dict(resource='info'))
@app.route('/map/<int:id>/<resource>')
def map_get(id, resource):
    if resource == 'info':
        map = Map.get(Map.id == id)

        result = map.dict()

        result['norushoffset'] = [x.dict() for x in map.norushoffset]

        return result

    if resource == 'versions':
        return [
            x.ver.dict() for x in MapVersion.select().where(MapVersion.map == id)
        ]

    if resource == 'notes':
        return [
            note.dict() for note in MapNote.select().where(MapNote.map == id)
        ]

    if resource == 'markers':
        markers = MapMarker.select().where(MapMarker.map == id)

        ret = []
        for marker in markers:
            rep = marker.json()

            if 'prop' in rep:
                rep['prop'] = MapProp.get(MapProp.id == rep['prop'])

            if 'editorIcon' in rep:
                rep['editorIcon'] = MapEditorIcon.get(MapEditorIcon.id == rep['editorIcon'])

            ret.append(rep)

        return ret

# ============= Mod Resources ==============

@app.route('/mod/<int:id>',defaults=dict(resource='info'))
@app.route('/mod/<int:id>/<resource>')
def mod_get(id, resource):
    if resource == 'info':
        return Mod.get(Mod.id == id).dict()

    if resource == 'versions':
        return [ dsum(x.ver.dict(), dict(uid=x.uid))
                 for x in ModVersion.select().where(ModVersion.mod == id)]

