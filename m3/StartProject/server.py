import re
import os
import json
import operator
import cherrypy
import subprocess
import traceback
from scripts import parse_json, generating_owl, onto_history
import time
from socket import *
from jinja2 import Environment, FileSystemLoader
import sys

sock = socket()
sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')


class Server(object):
    def __init__(self):
        self.data = self._load_data()
        self.regexes = {
            'from:': 'from:(("[^"]+")|([^\s]+))',
            'to:': 'to:(("[^"]+")|([^\s]+))',
            'rel:': 'rel:(("[^"]+")|([^\s]+))',
            'text:': 'text:(("[^"]+")|([^\s]+))',
            'value:': 'value:(("[^"]+")|([^\s]+))',
        }
        for x in self.regexes:
            self.regexes[x] = re.compile(self.regexes[x])

    def _load_data(self):
        old_json = os.path.join(resources_dir, "output.json")
        if os.path.exists(old_json):
            with open(old_json) as f:
                return json.loads(f.read())
        with open(os.path.join(resources_dir, "input.json")) as f:
            return json.loads(f.read())

    @cherrypy.expose
    def history(self, search=None):
        templates_env = Environment(loader=FileSystemLoader(templates_dir))
        template = templates_env.get_template('history.html')
        json_data = onto_history.addDataToJson()

        concepts = []
        concepts_diff = dict()

        for i in json_data.values():
            for j in range(len(i)):
                if i[j:j + 7] == 'replace':
                    j = j + 7
                    concept = ""
                    while i[j] != '}':
                        concept += i[j]
                        j += 1
                    concept += i[j]
                    concept += '\n'
                    concepts.append(concept)

                if i[j] == ',':
                    concept = ""
                    while i[j] != '}':
                        concept += i[j]
                        j += 1
                    concept += i[j]
                    concept += '\n'
                    concepts.append(concept)

                """if i[j] == '{':
                    print '\n\t'
                if i[j - 1] == '}' and i[j] == ',':
                    print '\n\n'
                if i[j] == ']':
                    print '\n'"""

        if search:
            search_regex = re.compile(search)
            for key in list(json_data.keys()):
                if search_regex.search(json_data[key]):
                    continue
                del json_data[key]

        return template.render({"input_dict": json_data, "search_value": search if search else ""})

    @cherrypy.expose
    def index(self, search=""):
        templates_env = Environment(loader=FileSystemLoader(templates_dir))
        template = templates_env.get_template('index.html')
        results = dict()
        output = dict()

        ok = False
        if search.startswith('"'):
            search = search[1:-1]

        for item in self.regexes:
            if item in search:
                ok = True
                result = self.regexes[item].search(search)
                if item not in results:
                    results[item] = result.group(1)
                    if results[item].startswith('"'):
                        results[item] = results[item][1:-1]
                    results[item] = re.compile(results[item])
            else:
                results[item] = re.compile(".*")

        if not ok:
            to_search = re.compile(search)

        for from_item in self.data:
            for relation_item in self.data[from_item]:
                for to in self.data[from_item][relation_item]:
                    [value, text] = [self.data[from_item][relation_item][to][0],
                                     self.data[from_item][relation_item][to][1:]]
                    if ok:
                        if results['from:'].match(from_item) and results['rel:'].match(relation_item) and \
                                results['to:'].match(to) and results['value:'].match(str(value)):
                            temp_ok = False
                            new_text = []
                            for item in text:
                                if results['text:'].match(item):
                                    temp_ok = True
                                    new_text.append(item)
                            if temp_ok:
                                if from_item not in output:
                                    output[from_item] = dict()
                                if relation_item not in output[from_item]:
                                    output[from_item][relation_item] = dict()
                                output[from_item][relation_item][to] = [value] + new_text
                    else:
                        new_text = []
                        temp_ok = False
                        for item in text:
                            if to_search.match(item):
                                temp_ok = True
                                new_text.append(item)

                        if to_search.match(from_item) or to_search.match(relation_item) or \
                                to_search.match(to) or to_search.match(str(value)) or temp_ok:

                            if from_item not in output:
                                output[from_item] = dict()
                            if relation_item not in output[from_item]:
                                output[from_item][relation_item] = dict()
                            if not temp_ok:
                                output[from_item][relation_item][to] = [value] + text
                            else:
                                output[from_item][relation_item][to] = [value] + new_text

        # main concepts
        main_concepts = dict()
        relations = set()
        for from_concept in self.data:
            if from_concept not in main_concepts:
                main_concepts[from_concept] = dict()
            for rel in self.data[from_concept]:
                relations.add(rel)
                main_concepts[from_concept][rel] = main_concepts[from_concept].get(rel, 0) + 1
        for from_concept in self.data:
            for rel in self.data[from_concept]:
                for to_concept in self.data[from_concept][rel]:
                    if to_concept not in main_concepts:
                        main_concepts[to_concept] = dict()
                    main_concepts[to_concept][rel] = main_concepts[to_concept].get(rel, 0) + \
                                                     main_concepts[from_concept].get(rel, 0) + 1
        concepts = set()
        for rel in relations:
            relation_score = {
                x: main_concepts[x][rel] for x in main_concepts if rel in main_concepts[x]
            }
            try:
                concepts.add(max(relation_score.items(), key=operator.itemgetter(1))[0])
            except Exception:
                traceback.print_exc()

        # return template.render({})
        custom_dict = dict()
        custom_dict["output"] = output
        custom_dict["search"] = search
        return template.render({"input_dict": custom_dict, "main_concepts": list(concepts)})

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def replace(self, old, new):
        old_json = json.loads(old)
        new_json = json.loads(new)
        if old_json['from'] not in self.data:
            return {"status": "error", "message": "field {} not found in ontology".format(old_json['from'])}

        if old_json['relation'] not in self.data[old_json['from']]:
            return {"status": "error",
                    "message": "relation {} not found in ontology {}".format(old_json['relation'], old_json['from'])}

        if old_json['to'] not in self.data[old_json['from']][old_json['relation']]:
            return {"status": "error",
                    "message": "to {} not found in ontology {} with relation {}".format(old_json['to'],
                                                                                        old_json['from'],
                                                                                        old_json['relation'])}

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
            # print(self.data)
            del (self.data[old_json['from']][old_json['relation']][old_json['to']])
            if len(self.data[old_json['from']][old_json['relation']]) == 0:
                del (self.data[old_json['from']][old_json['relation']])
            if len(self.data[old_json['from']]) == 0:
                del (self.data[old_json['from']])
            # print(self.data)
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
            # print(self.data)
        except Exception as e:
            return {"status": "error", 'message': str(e)}

        return {"status": "ok"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def delete(self, old):
        old_json = json.loads(old)
        if old_json['from'] not in self.data:
            return {"status": "error", "message": "field {} not found in ontology".format(old_json['from'])}

        if old_json['relation'] not in self.data[old_json['from']]:
            return {"status": "error",
                    "message": "relation {} not found in ontology {}".format(old_json['relation'], old_json['from'])}

        if old_json['to'] not in self.data[old_json['from']][old_json['relation']]:
            return {"status": "error",
                    "message": "to {} not found in ontology {} with relation {}".format(old_json['to'],
                                                                                        old_json['from'],
                                                                                        old_json['relation'])}

        try:
            old_data = self.data[old_json['from']][old_json['relation']][old_json['to']]
            # print(self.data)
            del (self.data[old_json['from']][old_json['relation']][old_json['to']])
            if len(self.data[old_json['from']][old_json['relation']]) == 0:
                del (self.data[old_json['from']][old_json['relation']])
            if len(self.data[old_json['from']]) == 0:
                del (self.data[old_json['from']])
        except Exception as e:
            return {"status": "error", 'message': str(e)}

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

    def isCyclicUtil(self, v, visited, recStack, relations, type_of_relations):
        visited[v] = True
        recStack[v] = True

        for node in range(len(relations)):
            if visited[node] == False and node != v and relations[v][2] == relations[node][0] and relations[v][
                1] in type_of_relations:
                if self.isCyclicUtil(node, visited, recStack, relations, type_of_relations) == True:
                    return True
            elif recStack[node] == True and node != v and relations[v][2] == relations[node][0] and relations[v][
                1] in type_of_relations:
                return True

        recStack[v] = False
        return False

    def isCyclic(self, relations, type_of_relations):
        visited = [False] * len(relations)
        recStack = [False] * len(relations)
        for node in range(len(relations)):
            if self.isCyclicUtil(node, visited, recStack, relations, type_of_relations) == True:
                return True
        return False

    def _check_for_cycles(self):
        type_of_relations = [
            "is_a"]  # for moment only this, if we want more we need just to add here the respective relationships
        relations = []

        for from_item in self.data:
            for relation_item in self.data[from_item]:
                for to in self.data[from_item][relation_item]:
                    relations.append((from_item, relation_item, to))

        return self.isCyclic(relations, type_of_relations)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def save(self):
        if (self._check_for_cycles == True):
            {'status': 'error', 'message': 'there are cycles in the current relationships!'}
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
        print(self.data)
        onto_history.DB().insert_into_table(self.data)
        print("Status generator: {}".format(output_generator))
        return {"status": "ok"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def reload(self):
        self.data = self._load_data()
        return {"status": "ok"}

    def rebuild(self):
        pass

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def delete_history(self, date):
        onto_history.DB().remove(date)
        return {"status": "ok"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def restore_history(self, date):
        restore_ontology = onto_history.DB().get_by_date(date)[0]
        self.data = json.loads(restore_ontology)


if __name__ == '__main__':
    cherrypy.quickstart(Server(), "/", "server.conf")
