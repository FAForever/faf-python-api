
import sys

if sys.version_info.major != 3:
    raise RuntimeError(
        "FAForever API requires python 3.\n"
        "Refer to passenger documentation on how to accomplish that.\n"
        "Good luck.")

from flask import Flask
app = Flask("FAForever Python Web API")



if __name__ == "__main__":
    app.run()
else:
    application = app