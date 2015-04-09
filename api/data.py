"""
Deals with basic data passing from db
"""

from api import *

def dsum(a,b):
    "Sum two dicts"
    d = a
    d.update(b)
    return a

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
    ver = DefaultVersion.get(DefaultVersion.mod == mod_name).dict()

    ver['ver_engine'] = RepoVersion.get(RepoVersion.id == ver['ver_engine']).dict()
    ver['ver_main_mod'] = RepoVersion.get(RepoVersion.id == ver['ver_main_mod']).dict()

    return ver

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

