
import sys  # To get the modules
sys.path.append('/usr/local/lib/python3.5/dist-packages/')

import os, pymongo, multiprocessing
from flask import Flask, request, Response
from functools import wraps
from bson.objectid import ObjectId
from json import dumps
from experiments import experiment, test_exp

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app = Flask(__name__)

app.config['UPLOAD_PATH'] = '/home/ubuntu/Training/'
app.config['UPLOAD_PATH_1'] = '/home/ubuntu/Test/'

database = pymongo.MongoClient()["nanonets"]
userCollection = database['users']
modelCollection = database['models']

def authenticate():

	return Response(
	'unauthorised access', 401,
	{'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.authorization

		if not auth or not query_user(auth.username, auth.password):
			return authenticate()
		return f(*args, **kwargs)
	return decorated

def query_user(u, p):
	doc = userCollection.find_one({'auth.username': u})

	if p:
		if doc:
			return p == doc['auth']['password']
		else:
			return False
	else:
		return doc['_id']

@app.route('/', methods=['GET'])
@requires_auth
def index():
	return "welcome to Nanonets"

@app.route('/models/list', methods=['GET'])
@requires_auth
def fetch_models():
	user_id = query_user(request.authorization.username, None)
	models = list(modelCollection.find({ "user_id": ObjectId(user_id)}, { "model_name": 1, 'images_uploaded': 1}))
	for model in models:
		model['model_id'] = str(model['_id'])
		del model['_id']

	return return_response(models)

@app.route('/models/create', methods=['POST'])
@requires_auth
def create_model():
	data = request.json
	if data:
		if 'model_name' in data:
			user_id = query_user(request.authorization.username, None)
			modelCollection.insert({
				'user_id': ObjectId(user_id),
				'model_name': data['model_name'],
				'results': [],
				'most_accurate': {},
				'images_uploaded': False
			})

			return return_response({'msg': 'Model created Successfully'})
		else:
			return improper_request('model_name not specified')
	else:
		return improper_request('please send proper JSON request')


@app.route('/models/training/upload/<id>', methods=['POST'])
@requires_auth
def upload(id):
	if request.method == 'POST':
		if id and modelCollection.find_one({'_id': ObjectId(id)}):

			if request.files:
				if 'images' in request.files:
					print(id)
					for f in request.files.getlist('images'):
						print(allowed_file(f.filename))
						if f and allowed_file(f.filename):
							f.save(os.path.join(app.config['UPLOAD_PATH'], f.filename))
						else:
							return 'Invalid file or files, not images'

					modelCollection.update_one({
						'_id': ObjectId(id)
					},{
						'$set': {
							'images_uploaded': True
						}}, upsert=False)

					return return_response({ 'msg': 'Upload completed.'})
				else:
					return improper_request('Please form-data key as images')
			else:
				return improper_request('Please attach images to request')
		else:
			return return_response('improper id in url')
	return improper_request('Please use post request')

@app.route('/models/optimise/start', methods=['POST'])
@requires_auth
def start_optimisation():
	data = request.json
	if data:
		if 'model_id' in data:
			if ObjectId.is_valid(data['model_id']):
				x = modelCollection.find_one({'_id': ObjectId(data['model_id'])})
				if x:
					if x['images_uploaded']:

						thread = multiprocessing.Process(target=experiment, args=(data['model_id'],))
						thread.start()
						return return_response({'msg': 'process started'})
					else:
						return improper_request('images still not uploaded')
				else:
					return improper_request('model id does not exist')
			else:
				return improper_request('improper model id')
		else:
			return improper_request('specify model id')
	else:
		return improper_request('please send proper JSON request')


@app.route('/models/optimise/status', methods=['POST'])
@requires_auth
def optimisation_status():
	data = request.json
	if data:
		if 'model_id' in data:
			if ObjectId.is_valid(data['model_id']):
				x = modelCollection.find_one({'_id': ObjectId(data['model_id'])})
				if x:
					if len(x['results']) < 27:
						msg = {"status": "Not Optimised"}
					else:
						msg = {"status": "Optimised"}
					return return_response(msg)
				else:
					return proper_request('model id does not exist')
			else:
				return proper_request('improper model id')
		else:
			return improper_request('specify model id')
	else:
		return improper_request('please send proper JSON request')


@app.route('/models/test/upload/<id>', methods=['POST'])
@requires_auth
def test(id):
	if request.method == 'POST':
		if id and ObjectId.is_valid(id) and modelCollection.find_one({'_id': ObjectId(id)}):
			values = modelCollection.find_one({'_id': ObjectId(id)}, {'most_accurate': 1})['most_accurate']
			print(values)
			if values:
				if request.files:
					if 'images' in request.files:

						if len(request.files.getlist('images')) == 1:
							f = request.files.getlist('images')[0]
							if f and allowed_file(f.filename):
								path = os.path.join(app.config['UPLOAD_PATH_1'], f.filename)
								f.save(path)

								dic = test_exp([
									values['i'], values['j'], values['k'], path
								])
								return return_response({ 'accuracy for image': dic['accuracy']})

							else:
								return improper_request('Invalid file or files, not images')
						else:
							return improper_request('Only 1 image can be uploaded')
					else:
						return improper_request('Please form-data key as images')
				else:
					return improper_request('Please attach images to request')
			else:
				return improper_request('model still not optimised')
		else:
			return return_response('improper id in url')
	return improper_request('Please use post request')


def allowed_file(filename):
	return '.' in filename and \
		   filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def return_response(response):
	return Response(dumps(response),
					mimetype='application/json',
					headers={
						'Access-Control-Allow-Origin': "*",
						'Access-Control-Allow-Methods': "POST, GET, OPTIONS, DELETE, PUT",
						'Access-Control-Max-Age': "1000",
						'Access-Control-Allow-Headers': "x-requested-with, x-auth-token, Content-Type, origin, authorization, accept, client-security-token"
					})

def improper_request(msg):
	return Response(msg, 400,
					mimetype='text/xml',
					headers={
						'Access-Control-Allow-Origin': "*",
						'Access-Control-Allow-Methods': "POST, GET, OPTIONS, DELETE, PUT",
						'Access-Control-Max-Age': "1000",
						'Access-Control-Allow-Headers': "x-requested-with, x-auth-token, Content-Type, origin, authorization, accept, client-security-token"
					})

if __name__ == '__main__':
	app.run(debug=True)
