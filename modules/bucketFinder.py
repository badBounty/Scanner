import requests
import urllib3
import re
import sys
import subprocess
import time
import os
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BucketFinder():

	scanned_targets = []
	data = []
	error_data = []
	msTeamsActivated = False
	outputActivated = False

	def activateOutput(self):
		self.outputActivated = True

	def showStartScreen(self):
		print('---------------------------------------------------------------------------------------')
		print('----------------------------++++++++++++-------++++++++++++++----------./*/.-----------')
		print('--------------------./*/.--++++++++++++++------++++++++++++++--------------------------')
		print('---------------------------+++----------------------------+++---./*/.------------------')
		print('---./*/.-------------------+++----------------------------+++--------------------------')
		print('---------------------------+++++++++++++-------++++++++++++++--------------------------')
		print('------------./*/.----------++++++++++++++------++++++++++++++-----------./*/.----------')
		print('--------------------------------------+++-----------------+++--------------------------')
		print('--------------------------------------+++-----------------+++--------------------------')
		print('---------------------------++++++++++++++------++++++++++++++------------------./*/.---')
		print('------------./*/.-----------+++++++++++++------++++++++++++++----./*/.-----------------')
		print('---------------------------------------------------------------------------------------')
		print('                                                                                       ')
		print('----------------------------------- Handerllon ©_© ------------------------------------')
		print('                                                                                       ')
		print('-------------------------- Starting vulnerable bucket finder --------------------------')
		print('Searching buckets on input...')

	def showEndScreen(self):

		print('---------------------------------------------------------------------------------------')
		print('Finished! Please check output for results!')


	def output(self):
		df = pd.DataFrame(self.data, columns = ['SourceURL','js_reference','Bucket Name','ls allowed', 'cprm allowed'])
		df.to_csv('output/'+self.inputName+'/bucketFinder.csv', index = False)
		df2 = pd.DataFrame(self.error_data, columns = ['SourceURL','js_reference','Reason'])
		df2.to_csv('output/'+self.inputName+'/bucketFinderError.csv', index = False)

	def setMsTeams(self,msTeams):
		self.msTeamsActivated = True
		self.msTeams = msTeams

	def filterInvalids(self,some_list):
		res = []
		#------ Filter invalid matches
		for item in some_list:
			if all(char not in item for char in ['\\','=','>','<','[',']','{','}',';','(',')']):
				res.append(item)
		return res

	def configureOutput(self, url, js_endpoint, bucket_list, ls_allowed, cprm_allowed):
		#------ Adding info for output
		for bucket in bucket_list:
			ls = False
			if bucket in ls_allowed:
				ls = True
			cprm = False
			if bucket in cprm_allowed:
				cprm = True

			#Microsoft teams output
			if self.msTeamsActivated:
				if ls == True and cprm == True:
					self.msTeams.title('Bucket found!')
					self.msTeams.text('Bucket ' + bucket + ' was found at host: '+ url + ' in: ' +
							js_endpoint+' with ls and cprm allowed')
					self.msTeams.send()
				elif ls == True:
					self.msTeams.title('Bucket found!')
					self.msTeams.text('Bucket ' + bucket + ' was found at host: '+ url + ' in: ' +
							js_endpoint+' with ls allowed')
					self.msTeams.send()
				elif cprm == True:
					self.msTeams.title('Bucket found!')
					self.msTeams.text('Bucket ' + bucket + ' was found at host: '+ url + ' in: ' +
							js_endpoint+' with cprm allowed')
					self.msTeams.send()

			#Adding to data for exporting
			self.data.append([url, js_endpoint, bucket, ls, cprm])

	def get_buckets(self, session, url, host):

		if url in self.scanned_targets:
			return []

		self.scanned_targets.append(url)
		try:
			response = session.get(url, verify = False)
		except:
			#print('Url: ' + url + ' could not be accessed')
			#self.error_data.append([host,url,'Invalid js file'])
			return []
		
		if response.status_code == 404:
			print('Url: ' + url + ' returned 404')
			self.error_data.append([host,url,'Returned 404'])
			return []

		#Buckets can come in different ways
		#Way 1: http<s>://s3.amazonaws.com/bucketName
		#Way 2: http<s>://bucketName.s3.amazonaws.com
		#Way 3: //bucketName.s3.amazonaws.com

		# view-source:https://cms.sky.com.br/en/card-page-cms

		#---------Way I----------
		bucketsFirstHTTPS = re.findall('"https://s3.amazonaws.com(.+?)"', response.text)
		bucketsFirstHTTPS = self.filterInvalids(bucketsFirstHTTPS)
		bucketsFirstHTTP = re.findall('"http://s3.amazonaws.com(.+?)"', response.text)
		bucketsFirstHTTP = self.filterInvalids(bucketsFirstHTTP)

		#---------Way II----------
		bucketsSecondHTTPS = re.findall('"https://(.+?).s3.amazonaws.com', response.text)
		bucketsSecondHTTPS = self.filterInvalids(bucketsSecondHTTPS)
		bucketsSecondHTTP = re.findall('"http://(.+?).s3.amazonaws.com', response.text)
		bucketsSecondHTTP = self.filterInvalids(bucketsSecondHTTP)

		#---------Way III---------
		bucketsThird = re.findall('\"//(.+?).s3.amazonaws.com', response.text)
		bucketsThird = self.filterInvalids(bucketsThird)

		bucket_list = bucketsFirstHTTP + bucketsSecondHTTP + bucketsFirstHTTPS + bucketsSecondHTTPS + bucketsThird
		bucket_list = list(dict.fromkeys(bucket_list))

		for i in range (len(bucket_list)):
			bucket_list[i] = bucket_list[i].replace('/','')

		return bucket_list

	#--------------------- Get buckets that allow ls ---------------------
	def get_ls_buckets(self,bucket_list):
		ls_allowed_buckets = []
		for bucket in bucket_list:
			try:
				output = subprocess.check_output('aws s3 ls s3://' + bucket, shell = True, stderr = subprocess.DEVNULL)
				ls_allowed_buckets.append(bucket)
			except subprocess.CalledProcessError:
				continue
				#print('Bucket ' + bucket + ' has ls blocked')

		return ls_allowed_buckets

	#--------------------- Get buckets that allow mv and rm ---------------------
	def get_cprm_buckets(self,bucket_list):
		cprm_allowed_buckets = []
		for bucket in bucket_list:
			try:
				output = subprocess.check_output('aws s3 cp test.txt s3://' + bucket, shell = True, stderr = subprocess.DEVNULL)
				subprocess.check_output('aws s3 rm s3://' + bucket + '/test.txt', shell = True)
				cprm_allowed_buckets.append(bucket)
			except subprocess.CalledProcessError as e:
				continue
				#print('Bucket ' + bucket + ' has cprm blocked')

		return cprm_allowed_buckets

	def get_js_files(self, session, url):

		# Regex used
		regex_str = r"""
  		(?:"|')                               # Start newline delimiter
  		(
    		((?:[a-zA-Z]{1,10}://|//)           # Match a scheme [a-Z]*1-10 or //
    		[^"'/]{1,}\.                        # Match a domainname (any character + dot)
    		[a-zA-Z]{2,}[^"']{0,})              # The domainextension and/or path
    		|
    		((?:/|\.\./|\./)                    # Start with /,../,./
    		[^"'><,;| *()(%%$^/\\\[\]]          # Next character can't be...
    		[^"'><,;|()]{1,})                   # Rest of the characters can't be
    		|
    		([a-zA-Z0-9_\-/]{1,}/               # Relative endpoint with /
    		[a-zA-Z0-9_\-/]{1,}                 # Resource name
    		\.(?:[a-zA-Z]{1,4}|action)          # Rest + extension (length 1-4 or action)
    		(?:[\?|#][^"|']{0,}|))              # ? or # mark with parameters
    		|
    		([a-zA-Z0-9_\-/]{1,}/               # REST API (no extension) with /
    		[a-zA-Z0-9_\-/]{3,}                 # Proper REST endpoints usually have 3+ chars
    		(?:[\?|#][^"|']{0,}|))              # ? or # mark with parameters
    		|
    		([a-zA-Z0-9_\-]{1,}                 # filename
    		\.(?:php|asp|aspx|jsp|json|
    		     action|html|js|txt|xml)        # . + extension
    		(?:[\?|#][^"|']{0,}|))              # ? or # mark with parameters
  		)
  		(?:"|')                               # End newline delimiter
		"""

		regex = re.compile(regex_str, re.VERBOSE)

		try:
			response = session.get(url, verify = False)
		except Exception:
			return []

		all_matches = [(m.group(1), m.start(0), m.end(0)) for m in re.finditer(regex, response.text)]
		js_endpoints = list()
		for match in all_matches:
			if '.js' in list(match)[0]:
				js_endpoints.append(list(match)[0])

		#print(js_endpoints)
		return js_endpoints

	def check_buckets(self, hostname, subname, bucket_list):
		if len(bucket_list)>0:
			print('The following bucket/s were found at ' + subname + ' :')
			print(bucket_list)

			#print('Checking bucket/s that allow ls...')
			ls_allowed = self.get_ls_buckets(bucket_list)
			#print('Checking bucket/s that allow cprm...')
			cprm_allowed = self.get_cprm_buckets(bucket_list)
			access_denied = list(set(bucket_list) - set(ls_allowed) - set(cprm_allowed)) 

			#print('Buckets that allowed ls are the following:')
			#print(ls_allowed)
			#print('Buckets that allowed cp and rm are the following:')
			#print(cprm_allowed)
			#print('No permissions buckets:')
			#print(access_denied)

			self.configureOutput(hostname, subname, bucket_list, ls_allowed, cprm_allowed)

	#Receives an urlList
	def run(self,urls, inputName):

		self.inputName = inputName
		session = requests.Session()
		headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

		session.headers.update(headers)
		
		for url in urls:
			if self.outputActivated:
				print('Scanning '+ url)

			buckets_in_html = self.get_buckets(session, url, 'html code')
			self.check_buckets(url, 'html code', buckets_in_html)

			js_in_url = self.get_js_files(session, url)

			#print(js_in_url)
			
			for js_endpoint in js_in_url:
				# Searching for buckets
				bucket_list = self.get_buckets(session, js_endpoint, url)
				self.check_buckets(url, js_endpoint, bucket_list)

		self.output()


		#print('-------------------------- Finished! --------------------------')
		#print('###__Found buckets sent to output.csv, errors sent to ErrorOutput.csv__###')