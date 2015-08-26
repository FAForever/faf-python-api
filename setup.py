from distutils.core import setup, Command

import api
import inspect


class ApiDoc(Command):
    description = 'Generate API documentation'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def inspect(self, member, seen):
        members = inspect.getmembers(member)
        for name, value in members:
            print("Inspecting {}".format(name))
            if (inspect.ismodule(value)
                    and name not in seen
                    and not inspect.isbuiltin(value)):
                print('Walking {}'.format(name))
                seen.add(name)
                self.inspect(value, seen)
            elif inspect.isfunction(value):
                print("Found function: {}".format(value))
                print(value.__qualname__)

    def run(self):
        api.app.config.from_object('config')
        api.api_init()
        map = api.app.url_map
        with open('route-info.apibp', 'w') as f:
            singular_template = """
# {method} {route}
{doc}

"""
            multiple_template_head = """
# {route}
"""

            multiple_template_item = """
## {method}
{doc}
"""
            for rule in map.iter_rules():
                fn = api.app.view_functions[rule.endpoint]
                args = dict(
                    methods=rule.methods,
                    route=str(rule),
                    doc=fn.__doc__
                )
                if len(args['methods']) == 1:
                    args['method'] = args['methods'][0]
                    f.write(singular_template.format(**args))
                else:
                    f.write(multiple_template_head.format(route=args['route']))
                    for method in args['methods']:
                        f.write(multiple_template_item.format(method=method,
                                                              doc=args['doc']))
        print("To generate the api doc use an apiblueprint generator")
        print("E.g. 'aglio'")
        print("\tnpm install -g aglio")
        print("\taglio -i documentation.apibp -o output.html")

setup(
    cmdclass={
      'apidoc': ApiDoc
    },
    name='Forged Alliance Forever API',
    version=api.__version__,
    packages=['api'],
    url='http://www.faforever.com',
    license=api.__license__,
    author=api.__author__,
    author_email=api.__contact__,
    description='API project'
)
