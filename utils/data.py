import json

class JointWeight(dict):
    @ property
    def joint_list(self):
        return self.keys()

class VertexWeight(dict):
    @ property
    def index_list(self):
        return self.keys()
    @ property
    def joint_list(self):
        joint_list = set()
        for key in self.keys():
            joint_weight_dict = self.__getitem__(key)
            joint_list.update(joint_weight_dict.keys())
        return list(joint_list)
    def write_file(self, file_name):
        serialize_data = json.dumps(self, indent=4)
        with open(file_name, 'w') as json_file:
            json_file.write(serialize_data)
    def read_file(self, file_name):
        with open(file_name, "r") as json_file:
            json_data = json.load(json_file)
        curr_data = {int(x):JointWeight(json_data[x]) for x in json_data.keys()}
        self.update(curr_data)
        return self
