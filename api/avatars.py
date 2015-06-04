from api import *

from db.faf_orm import Avatar

@app.route("/avatar")
def list_avatars():
    return [avatar.dict() for avatar in Avatar.select()]
