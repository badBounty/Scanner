import os
import requests
import re
import pandas as pd

class TokenFinder():

	scanned_targets = []
	data = []
	error_data = []
	outputActivated = False

	def activateOutput(self):
		self.outputActivated = True

	def showStartScreen(self):

		print('---------------------------------------------------------------------------------------')
		print('---------------------------++++++++++++++------++++++++++++++----------./*/.-----------')
		print('--------------------./*/.--++++++++++++++------++++++++++++++--------------------------')
		print('--------------------------------++++-----------+++--------------./*/.------------------')
		print('---./*/.------------------------++++-----------+++-------------------------------------')
		print('--------------------------------++++-----------+++++++++++-----------------------------')
		print('------------./*/.---------------++++-----------+++++++++++--------------./*/.----------')
		print('--------------------------------++++-----------+++-------------------------------------')
		print('--------------------------------++++-----------+++-------------------------------------')
		print('--------------------------------++++-----------+++-----------------------------./*/.---')
		print('------------./*/.---------------++++-----------+++---------------./*/.-----------------')
		print('---------------------------------------------------------------------------------------')
		print('                                                                                       ')
		print('----------------------------------- Handerllon ©_© ------------------------------------')
		print('                                                                                       ')
		print('-------------------------------- Starting token finder --------------------------------')
		print('Searching sensitive info on input...')

	def showEndScreen(self):

		print('---------------------------------------------------------------------------------------')
		print('Finished! Please check output/tokenFinder.csv for results and output/tokenFinderError.csv for errors found')

	def output(self):
		df = pd.DataFrame(self.data, columns = ['SourceURL','Type','Found'])
		df.to_csv('output/tokenFinder.csv', index = False)
		df2 = pd.DataFrame(self.error_data, columns = ['SourceURL','Reason'])
		df2.to_csv('output/tokenFinderError.csv', index = False)


	def filterInvalids(self,some_list):
		res = []
		#------ Filter invalid matches
		for item in some_list:
			if all(char not in item for char in ['\\','=','>','<','[',']','{','}',';','(',')']):
				res.append(item)
		return res

	def get_js_files(self, url):

		try:
			get_response = requests.get(url, verify = False)
		except Exception:
			return []
			
		get_text = get_response.text

		js_found = re.findall('([^\s",\'%]+)\.js', get_text)
		js_found = self.filterInvalids(js_found)
		for i in range (len(js_found)):
			#We add the .js that was removed at the regex
			js_found[i] = js_found[i] + '.js'

		host = get_response.url.split('/')
		host_protocol = host[0]
		host_name = host[2]
		only_hostname = host_protocol + '//' + host_name

		for i in range (len(js_found)):
			if js_found[i][:2] == '//':
				js_found[i] = 'https:' + js_found[i]
			elif js_found[i][:1] == '/':
				js_found[i] = only_hostname + js_found[i]
			elif js_found[i][:1] != 'h':
				js_found[i] = 'https://' + js_found[i]

		#print(str(len(js_found)) + ' js files were found!')
		return(js_found)

	#Searches certain keywords on site
	def process(self, session, url):

		try:
			response = session.get(url, verify = False)
		except:
			print('Url: ' + url + ' could not be accessed')
			self.error_data.append([url,'Invalid js file'])
			return []

		if response.status_code == 404:
			print('Url: ' + url + ' returned 404')
			self.error_data.append([url,'Returned 404'])
			return []

		tokens = re.findall('token="(.+?)"', response.text)
		tokens_2 = re.findall('Token="(.+?)"', response.text)
		keys = re.findall('key="(.+?)"', response.text)
		usernames = re.findall('Username="(.+?)"', response.text)
		passwords = re.findall('Password="(.+?)"', response.text)
		access_key_ids = re.findall('access_key_id="(.+?)"', response.text)
		secret_access_key_ids = re.findall('secret_access_key_id="(.+?)"', response.text)

		if len(tokens) > 0:
			for token in tokens:
				self.data.append([url, 'Token', token])
		if len(tokens_2) > 0:
			for token in tokens_2:
				self.data.append([url, 'Token',token])
		if len(keys) > 0:
			for key in keys:
				self.data.append([url, 'Key', key])
		if len(usernames) > 0:
			for username in usernames:
				self.data.append([url, 'Username', username])
		if len(passwords) > 0:
			for password in passwords:
				self.data.append([url, 'Password', password])
		if len(access_key_ids) > 0:
			for key in access_key_ids:
				self.data.append([url, 'access_key_id', key])
		if len(secret_access_key_ids) > 0:
			for key in secret_access_key_ids:
				self.data.append([url, 'secret_access_key', key])

	def run (self, urls):

		session = requests.Session()
		headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

		session.headers.update(headers)

		for url in urls:
			if self.outputActivated:
				print('Scanning '+ url)

			self.process(session, url)
			js_in_url = self.get_js_files(url)

			#print('Scanning js files...')

			for js_endpoint in js_in_url:
				self.process(session, js_endpoint)

		self.output()


