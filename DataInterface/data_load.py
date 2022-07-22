from collections import defaultdict
import queue
import copy


INDIVIDUAL_RELATION = {'parent': 'child', 'child': 'parent', 'spouse': 'spouse'}
UPDATED = 1
INVARIANT = 0
ATTR_THRESHOLD = {"corporation": 0.5, "partnership": 0, "individual": 1}


class Relationship(object):
    """Relationship of two entities"""

    def __init__(self, owner_name, owner_id, sub_name, sub_id, relation_type, value_percentage, is_included=None):
        self.owner_name = owner_name
        self.owner_id = owner_id
        self.sub_name = sub_name
        self.sub_id = sub_id
        self.relation_type = relation_type
        self.value_percentage = value_percentage
        self.attributions = defaultdict(float)

        self.attributions[owner_id] = value_percentage
        if is_included is None:
            self.is_included = False
        else:
            self.is_included = is_included

    def __add__(self, other):
        if self.relation_type != other.relation_type:
            raise TypeError("Can't add relationships with different relation_type: {}, {}",
                            self.relation_type, other.relation_type)
        else:
            self.value_percentage += other.value_percentage
            self.attributions[other.owner_id] += other.value_percentage
            return self

    def __str__(self):
        if len(self.attributions) == 1:
            attributions = ""
        else:
            attributions = ["{:.2f} from {}".format(percentage, owner_id)
                            for owner_id, percentage in self.attributions.items() if percentage]
            attributions = "({})".format(", ".join(attributions))
        return "{}-{:.2f}%{}->{}".format(self.owner_name, self.value_percentage*100, attributions, self.sub_name)


class Path(object):
    """A series of consecutive relationship"""

    def __init__(self, relationships=None):
        self.value = 0
        self.relationships = list()
        self.partnerships = list()
        if relationships is not None:
            for relationship in relationships:
                self.add_relationship(relationship)

    def add_relationship(self, relationship_arg, is_owner_partnership=False):
        relationship = copy.deepcopy(relationship_arg)
        if not self.relationships:
            self.relationships.append(relationship)
            self.value = relationship.value_percentage
        else:
            if relationship.owner_id != self.relationships[-1].sub_id:
                raise AssertionError("Disconnected path {}".format(str(self)))
            elif relationship.sub_id == self.relationships[-1].owner_id:
                raise AssertionError("Dual attributed path {}".format(str(self)))
            else:
                self.relationships.append(relationship)
                self.value *= relationship.value_percentage
                if is_owner_partnership:
                    self.partnerships.append(relationship.owner_id)

    def get_owner_id(self):
        if self.relationships is None:
            return None
        else:
            return self.relationships[0].owner_id

    def get_sub_id(self):
        if self.relationships is None:
            return None
        else:
            return self.relationships[-1].sub_id

    def __str__(self):
        """String representation also used as id, needs a more robust id"""
        path_str = []
        for relationship in self.relationships:
            path_str.append(str(relationship))
        return "\t{:.2f}%: {:s}".format(self.value * 100, ", ".join(path_str))


class Entity(object):
    """Primary entity"""

    def __init__(self, entity_id, legal_name, tax_form, tax_residence=None):
        self.entity_id = entity_id
        self.legal_name = legal_name
        self.tax_form = tax_form
        if tax_residence is not None:
            self.tax_residence = tax_residence
        self.subs = dict()
        self.owners = dict()          # directly owned by
        self.family = dict()   # all spouse, child and parent of this entity
        self.attribution = set()        # all the entities that attribute to this entity
        self.ownership318 = defaultdict(lambda: {"paths": [], "value": 0})
        self.is_calculated = False
        self.control_partnerships = list()

    def add_owned_by(self, relationship):
        self.owners[relationship.owner_id] = relationship

    def add_attribution(self, entities, sub_id):
        """recursively add attribution entities"""
        if sub_id == self.entity_id or sub_id in self.attribution:
            return
        self.attribution.add(sub_id)
        for sub_sub_id in entities[sub_id].attribution:
            self.add_attribution(entities, sub_sub_id)

    def add_relationship(self, relationship):
        """Add a relationship to the entity"""
        relationship = copy.deepcopy(relationship)
        if relationship.relation_type not in INDIVIDUAL_RELATION.keys():
            if relationship.sub_id not in self.subs.keys():
                zero_relationship = Relationship(self.legal_name, self.entity_id, relationship.sub_name, relationship.sub_id, relationship.relation_type, 0)
                self.subs[relationship.sub_id] = zero_relationship
            self.subs[relationship.sub_id] += relationship
        else:
            self.family[relationship.sub_id] = relationship

    def combine_entity(self, sub):
        """Combine all entity_relationships of sub"""
        for _, relationship in sub.subs.items():
            if relationship.sub_id != self.entity_id:
                self.add_relationship(relationship)

    def __str__(self):
        """string representation of the object"""
        return "{:s}".format(self.legal_name)


def print_ownership318(owner, sub):
    """Print the owner's ownership318 path and value in sub"""
    paths = owner.ownership318[sub.entity_id]["paths"]
    value = owner.ownership318[sub.entity_id]["value"]
    print(" Sec. 318 Result ".center(40, "*"))
    print("{0:s}'s Sec.318 ownership in {1:s} is {2:.2f}%".format(owner.legal_name, sub.legal_name, value*100))
    print("Calculated paths:")
    for counter, path in enumerate(paths):
        print("\t[{}]".format(counter+1) + str(path))


def get_attribution(entities, owner_id):
    """Add attribution to owner. Entities is modified"""
    owner = entities[owner_id]
    if owner.attribution:
        return
    if owner.tax_form == "Individual":
        for sub_id, relationship in owner.individual_relationships.items():
            entities[owner_id].attribution.add(sub_id)
            if relationship.relation_type == "parent":
                for sub_sub_id, sub_relationship in entities[sub_id].individual_relationships.items():
                    if sub_relationship.relation_type == "parent":
                        entities[owner_id].attribution.add(sub_sub_id)
    else:
        for owner_owner_id in owner.owners.keys():
            get_ownership(entities, owner_owner_id)
            if entities[owner_owner_id].ownership318[owner_id]["value"] >= ATTR_THRESHOLD[owner.tax_form]:
                entities[owner_id].attribution.add(owner_owner_id)
                entities[owner_id].attribution.update(entities[owner_owner_id].attribution)


def get_ownerships(entities):
    """"Calculate ownership318 for the entire graph"""
    for entity_id, entity in entities.items():
        if entity.is_calculated:
            continue
        get_ownership(entities, entity_id)


def get_ownership(entities_arg, owner_id):
    """calculated owner's ownership318 in all sub based on information in the entities graph.
        Args:
            entities_arg: list, the entire graph of entities. Only owner's ownership318 is modified in this function
            owner_id: str, entity_id of the owner
        Returns:
            None
    """
    entities = copy.deepcopy(entities_arg)
    if owner_id not in entities.keys():
        return
    owner = entities[owner_id]
    if owner.is_calculated:
        return

    get_attribution(entities, owner_id)
    for sub_id in owner.attribution:
        owner.combine_entity(entities[sub_id])
        entities[sub_id].subs = dict()
    for sub_id in owner.attribution:
        owner.subs.pop(sub_id, False)
    for own_own_id in owner.owners.keys():
        entities[own_own_id].subs.pop(owner_id, False)
    owner.owners = dict()
    owner.individual_relationships = dict()

    update_ownership(entities, owner_id)
    entities_arg[owner_id].ownership318 = entities[owner_id].ownership318
    entities_arg[owner_id].attribution = entities[owner_id].attribution
    entities_arg[owner_id].is_calculated = True
    return


def update_ownership(entities, global_owner_id):
    """Updates the owner's ownership in every other entity.
    Args:
        entities: list, the entire graph of entities.
        global_owner_id: double, entity_id of the owner
    Returns:
        None
    """
    global_owner = entities[global_owner_id]
    q = queue.Queue()

    q.put(global_owner)
    while q.qsize():
        owner = q.get_nowait()
        owner_id = owner.entity_id
        for sub_id, relationship in owner.subs.items():
            sub = entities[sub_id]
            if owner == global_owner:
                new_path = Path([relationship])
                global_owner.ownership318[sub_id]["paths"].append(new_path)
                global_owner.ownership318[sub_id]["value"] += new_path.value
            else:
                for path in global_owner.ownership318[owner_id]["paths"]:
                    new_path = copy.deepcopy(path)
                    new_path.add_relationship(relationship, entities[relationship.owner_id].tax_form == "partnership")
                    if not owner.control_partnerships:
                        if str(new_path) not in [str(p) for p in global_owner.ownership318[sub_id]["paths"]]:
                            global_owner.ownership318[sub_id]["paths"].append(new_path)
                            global_owner.ownership318[sub_id]["value"] += new_path.value
                    else:
                        if str(new_path) not in [str(p) for p in global_owner.ownership318[sub_id]["paths"]]\
                                and list(set(path.partnerships) & set(owner.control_partnerships)):
                            global_owner.ownership318[sub_id]["paths"].append(new_path)
                            global_owner.ownership318[sub_id]["value"] += new_path.value

            if global_owner.ownership318[sub_id]["value"] >= ATTR_THRESHOLD[sub.tax_form]:
                sub.control_partnerships = []
                q.put(sub)
            else:
                partnerships = {p for path in global_owner.ownership318[sub_id]["paths"] for p in path.partnerships}
                control_partnerships = list()
                for partnership in partnerships:
                    p_own_sub = sum([path.value for path in global_owner.ownership318[sub_id]["paths"]
                                     if partnership in path.partnerships]) / global_owner.ownership318[partnership]["value"]
                    if p_own_sub >= ATTR_THRESHOLD[sub.tax_form]:
                        control_partnerships.append(partnership)
                if control_partnerships:
                    sub.control_partnerships = control_partnerships
                    q.put(sub)
