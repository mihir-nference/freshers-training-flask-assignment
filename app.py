from collections import defaultdict
import requests
import json
from bson import ObjectId
from pymongo import MongoClient
from flask import Flask,jsonify,request
from creds import *

client = MongoClient(f"mongodb://{username}:{password}@mongo.servers.nferx.com:27017")
#client = MongoClient('localhost:27017')
db = client['Mihir_Narayan']
storedDatasets = db['datasets']
storedModels = db['models']
storedProjects = db['projects']
trainedModels = db['trained_models']

app=Flask(__name__)
projectServiceEndpoint = "http://sentenceapi2.servers.nferx.com:8015/tagrecorder/v3/projects/"

#return list of data from list of _id
def changeidtodata(lst,storedData):
	ans=[]
	for i in range(len(lst)):
		lst[i]=storedData.find_one({'_id':lst[i]})
		lst[i]['_id']=str(lst[i]['_id'])
		ans.append(lst[i])
	return ans

@app.route('/')
def index():
	return "Welcome to Flask app"

@app.route('/load_project',methods=['GET'])
def loadProject():
	project_id = ObjectId(request.args.get('project_id'))
	
	if storedProjects.find_one({'_id':project_id})!=None:
		return f"Project {project_id} already loaded!"

	fetchedData = requests.get(projectServiceEndpoint+str(project_id)).json()
	associated_datasets = fetchedData['result']['project']['associated_datasets']
	models = fetchedData['result']['project']['models']

	dataset_id = []
	for dataset in associated_datasets:
		dataset['_id']=ObjectId(dataset['_id'])
		storedDatasets.insert_one(dataset)
		dataset_id.append(dataset['_id'])

	model_id = []
	for model in models:
		temp = storedModels.insert_one(model)
		model['_id']=ObjectId(temp.inserted_id)
		model_id.append(model['_id'])
	
	res = {'_id':project_id,'associated_datasets':dataset_id,'models':model_id}
	storedProjects.insert_one(res)
	
	trained_models = defaultdict(list)
	for model in models:
		for dataset in model['datasets_used']:
			trained_models[ObjectId(dataset['dataset_id'])].append(model['_id'])
	trainedModels.insert_many([{'_id':d_id,'trained_models':trained_models[d_id]} for d_id in trained_models])
	
	return f"Your Project with project_id {project_id} is loaded to MongoDB"

@app.route('/fetch_info',methods=['GET'])
def fetchInfo():
	res="Enter either project_id,dataset_id or model_id"
	if request.args.get('project_id')!=None :
		project_id = ObjectId(request.args.get('project_id'))
		res = storedProjects.find_one({'_id':project_id})
		changeidtodata(res['associated_datasets'],storedDatasets)
		changeidtodata(res['models'],storedModels)
	elif request.args.get('dataset_id')!= None :
		dataset_id = ObjectId(request.args.get('dataset_id'))
		res = storedDatasets.find_one({'_id':dataset_id})
	elif request.args.get('model_id')!=None :
		model_id = ObjectId(request.args.get('model_id'))
		res = storedModels.find_one({'_id':model_id})
	else:
		return res

	res['_id']=str(res['_id'])
	return res

@app.route('/fetch_trained_models',methods=['GET'])
def fetchTrainedModels():
	dataset_id = ObjectId(request.args.get('dataset_id'))
	model_ids = trainedModels.find_one({'_id':dataset_id})['trained_models']
	res = {'dataset_id':str(dataset_id)}
	res['trained_models']=changeidtodata(model_ids,storedModels)
	return res

if __name__=="__main__" :
	app.run(debug=True)