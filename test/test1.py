import subprocess
import os
import time
import sys

Timeout = 540

def linux_test():
	local_start_out = subprocess.Popen(["intermine_boot", "start", "local"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	print("started local intermine")
	start = time.time()
	
	while True:
		time.sleep(1)
		end = time.time()
		curl_out = subprocess.run(["curl", "http://localhost:9999/biotestmine/service/version"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
		if(curl_out.stdout!=''):
			print(curl_out.stdout)
			break
		if((end-start)>Timeout):
			local_start_out.kill()
			subprocess.run(["intermine_boot","stop","local"])
			print("process ran for too long")
			sys.exit(1)
	
	subprocess.run(["intermine_boot","stop","local"])
	print("This test was successful")

def windows_test():
	print("This OS is not currently supported with travis")
	sys.exit(1)

	# local_start_out = subprocess.Popen(["intermine_boot", "start", "local"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	# print("started local intermine")
	# start = time.time()
	
	# while True:
	# 	time.sleep(1)
	# 	end = time.time()
	# 	curl_out = subprocess.run(["curl", "http://localhost:9999/biotestmine/service/version"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
	# 	if(curl_out.stdout!=''):
	# 		print(curl_out.stdout)
	# 		break
	# 	if((end-start)>Timeout):
	# 		local_start_out.kill()
	# 		subprocess.run(["intermine_boot","stop","local"])
 # 			print("process ran for too long")

	# 		sys.exit(1)
	
	# subprocess.run(["intermine_boot","stop","local"])
	# print("This test was successful")

def osx_test():
	print("This OS is not currently supported with travis")
	sys.exit(1)

	# local_start_out = subprocess.Popen(["intermine_boot", "start", "local"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	# print("started local intermine")
	# start = time.time()
	
	# while True:
	# 	time.sleep(1)
	# 	end = time.time()
	# 	curl_out = subprocess.run(["curl", "http://localhost:9999/biotestmine/service/version"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
	# 	if(curl_out.stdout!=''):
	# 		print(curl_out.stdout)
	# 		break
	# 	if((end-start)>Timeout):
	# 		local_start_out.kill()
	# 		subprocess.run(["intermine_boot","stop","local"])
	# 		print("process ran for too long")

	# 		sys.exit(1)
	
	# subprocess.run(["intermine_boot","stop","local"])
	# print("This test was successful")

os_name = sys.platform
print("You are using the following operating system:", os_name)
if(os_name=="linux2" or "linux"):
	linux_test()
elif (os_name=="win32"):
	windows_test()
elif (os_name=="darwin"):
	osx_test()
else:
	print("This is not a supported operating system in this test script")
