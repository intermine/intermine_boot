import subprocess
import os
import time

local_start_out = subprocess.Popen(["intermine_boot", "start", "local"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print("started local intermine")

while True:
	time.sleep(1)
	try:
		curl_out = subprocess.run(["curl", "http://localhost:9999/biotestmine/service/version"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout = 1000)
		print(curl_out.stdout)
		if(curl_out.stdout!=''):
		break
	except subprocess.TimeoutExpired:
		 print('process ran too long')
subprocess.run(["intermine_boot","stop","local"])
