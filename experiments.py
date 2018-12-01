import sys  # To get the modules

sys.path.append('/usr/local/lib/python3.5/dist-packages/')

import pymongo, flask

I = [0.001, 0.01, 0.1]
J = [1, 2, 4]
K = [1000, 2000, 4000]

from subprocess import Popen, PIPE
import ast
from bson.objectid import ObjectId


def experiment(model_id):
    client = pymongo.MongoClient()
    db = client["nanonets"]
    mods = db['models']

    for i in I:
        for j in J:
            for k in K:
                result = start_exp([i, j, k])
                mods.update_one({"_id": ObjectId(model_id)},
                                {'$push': {'results': result}})  # insert object id with model_id

    doc = mods.find_one({"_id": ObjectId(model_id)})
    sorted_list = sorted(doc['results'], key=lambda k: k['accuracy'])
    highest = sorted_list.pop()
    mods.update_one({"_id": ObjectId(model_id)}, {'$set': {'most_accurate': highest}})


def start_exp(arg):
    process = Popen(["python", "train.py", "--i", str(arg[0]), "--j",
                     str(arg[1]), "--k", str(arg[2]), "--images", "/home/ubuntu/Training/"], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    dic = ast.literal_eval(stdout.decode("utf-8"))
    return dic

def test_exp(arg):
    process = Popen(["python", "test.py", "--i", str(arg[0]), "--j",
                     str(arg[1]), "--k", str(arg[2]), "--image", arg[3]], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    dic = ast.literal_eval(stdout.decode("utf-8"))
    return dic