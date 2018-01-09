import os
import json
import cherrypy
import subprocess
from scripts import parse_json, generating_owl
import time
from socket import *
from jinja2 import Environment, FileSystemLoader

sock=socket()
sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')

class Server(object):
    def __init__(self):
        self.data = self._load_data()

    def _load_data(self):
        old_json = os.path.join(resources_dir, "output.json")
        if os.path.exists(old_json):
            with open(old_json) as f:
                return json.loads(f.read())
        with open(os.path.join(resources_dir, "input.json")) as f:
            return json.loads(f.read())

    @cherrypy.expose
    def index(self):
        templates_env = Environment(loader=FileSystemLoader(templates_dir))
        template = templates_env.get_template('index.html')
        # return template.render({})
        return template.render({"input_dict": self.data})

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def replace(self, old, new):
        old_json = json.loads(old)
        new_json = json.loads(new)
        if old_json['from'] not in self.data:
            return {"status": "error", "message": "field {} not found in ontology".format(old_json['from'])}

        if old_json['relation'] not in self.data[old_json['from']]:
            return {"status": "error", "message": "relation {} not found in ontology {}".format(old_json['relation'], old_json['from'])}

        if old_json['to'] not in self.data[old_json['from']][old_json['relation']]:
            return {"status": "error", "message": "to {} not found in ontology {} with relation {}".format(old_json['to'], old_json['from'], old_json['relation'])}


        if new_json['from'] in self.data:
            if new_json['relation'] in self.data[new_json['from']]:
                if new_json['to'] in self.data[new_json['from']][new_json['relation']]:
                    return {'status': 'error', 'message': 'already exists'}

        if new_json['relation'].strip().lower() == 'is_a':
            if new_json['to'] in self.data:
                if new_json['relation'] in self.data[new_json['to']]:
                    if new_json['from'] in self.data[new_json['to']][new_json['relation']]:
                        return {'status': 'error', 'message': 'is_a relation already exists in oposite direction'}

        try:
            old_data = self.data[old_json['from']][old_json['relation']][old_json['to']]
            print(self.data)
            del(self.data[old_json['from']][old_json['relation']][old_json['to']])
            if len(self.data[old_json['from']][old_json['relation']]) == 0:
                del(self.data[old_json['from']][old_json['relation']])
            if len(self.data[old_json['from']]) == 0:
                del (self.data[old_json['from']])
            print(self.data)
            if new_json['from'] not in self.data:
                self.data[new_json['from']] = dict()
            if new_json['relation'] not in self.data[new_json['from']]:
                self.data[new_json['from']][new_json['relation']] = dict()
            self.data[new_json['from']][new_json['relation']][new_json['to']] = old_data

            # new_data = dict()
            # new_data[new_json['to']]=old_data
            # new_new_data = dict()
            # new_new_data[new_json['relation']] = new_data
            # new_data = dict()
            # new_data[new_json['from']] = new_new_data
            # self.data[new_json['from']] = new_new_data
            print(self.data)
        except Exception as e:
            return {"status": "bad"}

        return {"status": "ok"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def delete(self, old):
        old_json = json.loads(old)
        if old_json['from'] not in self.data:
            return {"status": "error", "message": "field {} not found in ontology".format(old_json['from'])}

        if old_json['relation'] not in self.data[old_json['from']]:
            return {"status": "error", "message": "relation {} not found in ontology {}".format(old_json['relation'], old_json['from'])}

        if old_json['to'] not in self.data[old_json['from']][old_json['relation']]:
            return {"status": "error", "message": "to {} not found in ontology {} with relation {}".format(old_json['to'], old_json['from'], old_json['relation'])}

        try:
            old_data = self.data[old_json['from']][old_json['relation']][old_json['to']]
            print(self.data)
            del(self.data[old_json['from']][old_json['relation']][old_json['to']])
            if len(self.data[old_json['from']][old_json['relation']]) == 0:
                del(self.data[old_json['from']][old_json['relation']])
            if len(self.data[old_json['from']]) == 0:
                del(self.data[old_json['from']])
        except Exception as e:
            return {"status": "ok"}


    @cherrypy.expose
    @cherrypy.tools.json_out()
    def create(self, new):
        new_json = json.loads(new)

        if new_json['from'] in self.data:
            if new_json['relation'] in self.data[new_json['from']]:
                if new_json['to'] in self.data[new_json['from']][new_json['relation']]:
                    return {'status': 'error', 'message': 'already exists'}

        if new_json['relation'].strip().lower() == 'is_a':
            if new_json['to'] in self.data:
                if new_json['relation'] in self.data[new_json['to']]:
                    if new_json['from'] in self.data[new_json['to']][new_json['relation']]:
                        return {'status': 'error', 'message': 'is_a relation already exists in oposite direction'}

        if new_json['from'] not in self.data:
            self.data[new_json['from']] = dict()
        if new_json['relation'] not in self.data[new_json['from']]:
            self.data[new_json['from']][new_json['relation']] = dict()
        self.data[new_json['from']][new_json['relation']][new_json['to']] = [new_json["value"], new_json["text"]]
        return {"status": "ok"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def save(self):
        with open(os.path.join(resources_dir, "output.json"), "w") as f:
            json.dump(self.data, f)

        # parse_script_path = os.path.join(scripts_dir, "parse_json.py")
        # proc = subprocess.Popen(["python", parse_script_path], stdout=subprocess.PIPE, shell=True)
        # (out, err) = proc.communicate()
        # print("Out: {} | Err: {}".format(out, err))
        # os.system(parse_script_path)
        output_parser = parse_json.run()
        print("Status save: {}".format(output_parser))

        # generate_script_path = os.path.join(scripts_dir, "generating_owl.py")
        # os.system(generate_script_path)
        output_generator = generating_owl.run()
        print("Status generator: {}".format(output_generator))
        return {"status": "ok"}
        pass

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def reload(self):
        self.data = self._load_data()
        return {"status": "ok"}

    def rebuild(self):
        pass

if __name__ == '__main__':
    cherrypy.quickstart(Server(), "/", "server.conf")