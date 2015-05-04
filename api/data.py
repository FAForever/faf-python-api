"""
Deals with basic data passing from db
"""

from api import *

from flask import request, Response

from os.path import join as pjoin, dirname
import _geoip_geolite2
import geoip2.database

# Theeee H4444x!
geolite2 = geoip2.database.Reader(
    pjoin(dirname(_geoip_geolite2.__file__), _geoip_geolite2.database_name))

def dsum(a,b):
    "Sum two dicts"
    d = a
    d.update(b)
    return a

def serve_db_file(file: DBFile):
    return Response(file.data, 200,
        {'Content-Length': len(file.data)},
        file.mime_type + '/' + file.mime_subtype)

class Resource:
    "Represents a URL reachable resource."

    # Subclasses should declare their own name.
    name = '_base'

    # Subclasses should declare their peewee model.
    model = None

    @staticmethod
    def get(id, detail='info'):
        """
        Override to return a dictionary/list/tuple
        that will be passed as the response.

        :param id: integer id
        :param detail: str specific detail, arbitrary, passed in http request,
                          defaults to 'info'
        :return:
        """
        pass

    @staticmethod
    def search(query):
        """
        Override to return a peewee where clause.

        Such as 'Match([ResModel.name], query) & ResModel.is_ok'
        :param query: search query
        :return: peewee where clause
        """
        return 'Resource is unsearchable.', 400

class UserRes(Resource):
    name = 'user'
    model = User

    @staticmethod
    def get(id, detail='info'):
        try:
            user = User.get(User.id == id)
        except DoesNotExist:
            return 'No such user id=%d' % id, 404

        if detail == 'info':

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
            except DoesNotExist:
                pass

            try:
                avatar = user.avatars.select().where(UserAvatar.selected == True)[0].avatar

                res['avatar'] = dict(name='',tooltip=avatar.tooltip,url=avatar.url)
            except: # If avatar does not exist
                res['avatar'] = dict(name='',tooltip='',url='')

            return res

    @staticmethod
    def search(query):
        return Match([User.login], query)

class MapRes(Resource):
    name = 'map'
    model = Map

    @staticmethod
    def get(id, detail='info'):
        if detail == 'info':
            map = Map.get(Map.id == id)

            result = map.dict()

            result['norushoffset'] = [x.dict() for x in map.norushoffset]

            return result

        if detail == 'versions':
            return [
                x.ver.dict() for x in MapVersion.select().where(MapVersion.map == id)
            ]

        if detail == 'notes':
            return [
                note.dict() for note in MapNote.select().where(MapNote.map == id)
            ]

        if detail == 'markers':
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

    @staticmethod
    def search(query):
        return Match([Map.name, Map.description, Map.author], query)

class ModRes(Resource):
    name = 'mod'
    model = Mod

    @staticmethod
    def get(id, detail='info'):
        if detail == 'info':
            return Mod.get(Mod.id == id).dict()

        if detail == 'versions':
            return [ dsum(x.ver.dict(), dict(uid=x.uid))
                     for x in ModVersion.select().where(ModVersion.mod == id)]

        if detail == 'icon':
            mod = Mod.get(Mod.id == id)

            if mod.icon:
                return serve_db_file(mod.icon)
            else:
                return "No icon for mod id=%d." % id, 404

    @staticmethod
    def search(query):
        return Match(
            [Mod.name, Mod.description, Mod.author, Mod.url, Mod.copyright],
            query
        )

# ======== Unified Resource Routes ========

resources = dict(
    user=UserRes,
    map=MapRes,
    mod=ModRes
)

@app.route('/<resource>/<int:id>')
@app.route('/<resource>/<int:id>/<detail>')
def resource_get(resource, id, detail='info'):
    if resource not in resources:
        return 'Unknown resource type=%s' % resource, 404

    return resources[resource].get(id, detail)

@app.route('/<resource>/search')
def resource_search(resource):
    if resource not in resources:
        return 'Unknown resource type=%s' % resource, 404

    resClass = resources[resource]
    rModel = resClass.model

    query = request.args.get('q', '')
    limit = request.args.get('l') or 20

    if len(query) < 2:
        return 'Cannot search with less than 2 characters.', 400

    query = ' '.join([x+'*' for x in query.split()])
    search_clause = resClass.search(query)

    if not search_clause or isinstance(search_clause, tuple):
        # Search failed / unsearchable.
        return search_clause

    id_select = rModel.select(rModel.id).where(search_clause).limit(limit)

    return [resClass.get(id) for id in id_select]

# ======== Extra Routes ========

@app.route('/user/byname/<username>')
@app.route('/user/byname/<username>/<detail>')
def user_byname_get(username, detail='info'):
    try:
        user = User.get(User.login == username)
    except DoesNotExist:
        return 'No such user name=%s' % username, 404

    return UserRes.get(user.id, detail)

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
