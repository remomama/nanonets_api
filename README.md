# nanonets_api

Run nanonets_api.py using python or python3 keeping experiments.py, train.py and test.py in same directory

Used mongo as Database with nanonets as DB name with users and models collections

add a user in users collection with schema:
{
  "first_name" : "Your First Name",
	"last_name" : "Your Last Name",
	"auth" : {
		"username" : "Your Username",
		"password" : "Your Password"
	}
}

Download modules - pymongo, flask are sufficient
