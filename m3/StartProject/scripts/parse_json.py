import os
import json

resources_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")

handler = open(os.path.join(resources_dir, "output.json"))
obj = json.load(handler)
handler.close()

limit = 5
score = dict()
concepts = dict()
# dict cu relatiile intre concepte gen pentru conceptul "mere" o sa am relatia "is_a" fruct
def get_the_highest_score(concept):
    if concept not in concepts:
        return 1
    elif "is_a" not in concepts:
        if concept in score:
            return score[concept]
        else:
            return 1
    if concept in score:
        return max(score[concept], get_the_highest_score(concepts[concept]["is_a"]))
    else:
        return get_the_highest_score(concepts[concept]["is_a"])


for concept in obj:
    print("Concept: {}".format(concept))
    concepts[concept] = dict()
    concept_score = 0
    for relation in obj[concept]:
        concepts[concept][relation] = list()
        print("- relation: {}".format(relation))
        for new_concept in obj[concept][relation]:
            concepts[concept][relation].append(new_concept)
            concept_score += get_the_highest_score(new_concept) * int(obj[concept][relation][new_concept][0])
            print("-- with concept: {}".format(new_concept))
    score[concept] = concept_score

desired_concepts = dict()
for item in concepts:
	if score[item] >= limit:
		desired_concepts[item] = concepts[item]

print(concepts)
print(score)
print(desired_concepts)

nh = open(os.path.join(resources_dir, "ontorat_input_file.txt"), "wb")

for item in desired_concepts:
	for relation in desired_concepts[item]:
		for tt in desired_concepts[item][relation]:
			nh.write("{}\t{}\t{}\n".format(item.strip(), relation.strip(), tt.strip()))

nh.close()