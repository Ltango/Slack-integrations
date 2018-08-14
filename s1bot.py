#!/usr/bin/python

from multiprocessing.dummy import Pool as ThreadPool
import thread
import os
import time
import datetime
import re
import requests
from util import Utilities
import json
import getpass
import sys
import random
from slackclient import SlackClient
from multiprocessing import Process,Pipe
import socket
from threading import Timer


# instantiate Slack client
#this is the OAuth bot token for s1app
slack_client =	SlackClient('')
baseurl = 'https://Company.sentinelone.net'

#TODO: MAKE CHECKS ONCE PER DAY TO SEE IF TOKENS HAVE EXPIRED TO ALL USERS IN TOKENS.JSON FILE

s1session = requests.Session()

#TODO: SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "do"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
withinExpiredDays = 3

def parse_bot_commands(slack_events):
	"""
		Parses a list of events coming from the Slack RTM API to find bot commands.
		If a bot command is found, this function returns a tuple of command and channel.
		If its not found, then this function returns None, None.
	"""
	for event in slack_events:
		if event["type"] == "message" and not "subtype" in event:
			user_id, message = parse_direct_mention(event["text"])
			if user_id == starterbot_id:
				return message, event["channel"], event["user"]
	return None, None, None

def parse_direct_mention(message_text):
	"""
		Finds a direct mention (a mention that is at the beginning) in message text
		and returns the user ID which was mentioned. If there is no direct mention, returns None
	"""
	matches = re.search(MENTION_REGEX, message_text)
	# the first group contains the username, the second group contains the remaining message
	return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel, slackID):
	"""
		Executes bot command if the command is known
	"""


	# Default response is help text for the user
	listOfCommands = "=== Console Commands ===\n"
	listOfCommands += "Console		Print the URL to your console.\n"
	listOfCommands += "Set Token	Set Token For Sentinel One API\n"
	listOfCommands += "\n"
	listOfCommands += "=== Investigation ===\n"
	listOfCommands += "Find user [agent user]		Identify Details of Specified User on Local Systems.\n"
	listOfCommands += "Find Admin [admin_user]		Identify Details of Specified Console User.\n"
	listOfCommands += "ip [ip address]				Identify Details of Specified System By IP Address.\n"
	listOfCommands += "who has an api token			Lists registered slack users\n"
	listOfCommands += "\n"
	listOfCommands += "=== Agent Actions ===\n"
	listOfCommands += "disconnect [ip address OR machine name]		Isolate the Specified System from Network Resources.\n"
	listOfCommands += "reconnect [ip address OR machine name]		Reconnect the Specified system to the Network.\n"
	listOfCommands += "shutdown [ip address OR machine name]		Shutdown the Specified System.\n"
	listOfCommands += "restart [ip address OR machine name]			Restart the Specified System.\n"
	listOfCommands += "uninstall [ip address OR machine name]			Uninstall S1 from the Specified System.\n"
	listOfCommands += "passphrase [ip address OR machine name]			Obtain passphrase for the Specified System.\n"
	listOfCommands += "\n"
	listOfCommands += "=== Testing ===\n"
	listOfCommands += "I love you!\n"
	listOfCommands += "\n"
	default_response = "Not sure what you mean.\nType 'help' for a list of commands"

	# Finds and executes the given command, filling in response
	response = None



	# This is where you start to implement more commands!
	command = command.lower()
	#stupid commands - gets overwritten if real commands are given
	if command.endswith("?"):
		if bool(random.getrandbits(1)):
			response = 'Yes!'
		else:
			response = 'No...'
	if command.endswith("!"):
		response = 'Don\'t yell at me!'




	if command.startswith("help"):
		response = listOfCommands
	if command.startswith("console"):
		response = slacksentinelPrintBaseURL(command)
	# if command.startswith("set token"):
		# response = None
		# default_response = None
		# slackAPITokenPrompt("Let's reset your token.")
		# because Luke's is better than Mike's
	if command.startswith("set token"):
		response = None
		default_response = None
		slackRegenerateAPITokenButton(slackID)
	if command.startswith("find user"):
		response = slackGetAgentDetailsFromName(command)
	if command.startswith("i love you"):
		response = slackTellMeYouLoveMe(command)
	if command.startswith("find admin"):
		response = slacksentinelGetUserDetails(command)
	if command.startswith("ip"):
		response = slackGetAgentDetailsFromIP(command)
	if command.startswith("disconnect"):
		response = slackDisconnectFromNetwork(command)
	if command.startswith("reconnect"):
		response = slackReconnectToNetwork(command)
	if command.startswith("shutdown"):
		response = slackShutdownAgent(command)
	if command.startswith("restart"):
		response = slackRestartAgent(command)
	if command.startswith("uninstall"):
		response = slackUninstallAgent(command)
	if command.startswith("passphrase"):
		response = slackGetPassphrase(command)
	#if command.startswith("repeat"):
	#	response = slackS1SendMessage(channel, command)
	if command.startswith("who has an api token"):
		response = slackListNamesOfTokens(slackID)
	if command.startswith('processes'):
		response = slackGetProcesses(command)
	if command.startswith('custom'):
		response = slackCustomAPIRequest(command)
	#if command.startswith('me'):
		#response = socket.gethostbyname(socket.gethostname())
	if command.startswith('break'):
		raise Exception('Manually thrown Exception')
	if command.startswith('menu'):
		response = None
		default_response = None
		slackTestMenu(channel)
	if command.startswith('slackme'):
		response = SlackGetUserDetails(slackID)
	if command.startswith('check all tokens'):
		checkEverybodiesTokens(slackID, channel, True)
		response = None
		default_response = None



	# Sends the response back to the channel
	slack_client.api_call(
		"chat.postMessage",
		channel=channel,
		text=response or default_response
	)


def SlackGetUserDetails(slackID):
	#return slack_client.api_call("users.info", user = slackID)
	return json.dumps(slack_client.api_call("users.info", user = slackID),sort_keys=True, indent=4)

def slackGetRealNameFromID(slackID):
	return slack_client.api_call("users.info", user = slackID)['user']['real_name']

def slackListNamesOfTokens(slackID):
	nestedList = returnJSONCredentials(slackID)
	currentApprovedUsersList = list()
	expiredList = list()
	goodNames = ''
	badNames = ''
	try:
		expiredList = nestedList.pop()
	except:
		print 'no expired tokens'
	try:
		currentApprovedUsersList = nestedList.pop()
	except:
		print 'no valid users???'
	for user in currentApprovedUsersList:
		data = slack_client.api_call("users.info", user = user)
		#goodNames.append(data['user']['real_name'])
		goodNames += ' - ' + data['user']['real_name'] + '\n'
	for user in expiredList:
		data = slack_client.api_call("users.info", user = user)
		#print data['user']['real_name']
		#badNames.append(data['user']['real_name'])
		badNames += ' - ' + data['user']['real_name'] + '\n'
	if not expiredList:
		badNames = 'No expired Users'
	return 'Current Users: \n' + goodNames + '\n\nExpired Users: \n' + badNames

def slackSendConfirmButton(type, id = 'true'):
	slack_client.api_call(
			"chat.postMessage",
			channel = channel,
			as_user = 'true',
			attachments = [
			{
			"text": "Are you sure???",
			"fallback": "Unable to comply with your request",
			"callback_id": "confirm" + type + "ButtonID",
			"color": "#3AA3E3",
			"actions": [
				{
					"name": "yesbutton",
					"text": "Yes",
					"type": "button",
					"value": id,
					"style": "primary",
				},
				{
					"name": "nobutton",
					"text": "No",
					"type": "button",
					"value": "false",
					"style": "danger"
				}

			]
			}
		]
		)

def slackAPITokenPrompt(prompt):
	slack_client.api_call(
		"chat.postMessage",
		channel = channel,
		as_user = 'true',
		attachments = [
		{
		"text": prompt,
		"fallback": "Unable to comply with your request",
		"callback_id": "buttonDialogNewS1APIToken",
		"color": "#3AA3E3",
		"actions": [
			{
				"name": "dialogueLaunchButton",
				"text": "Enter API Token",
				"type": "button",
				"value": "newAPITokenLaunchDialog",
				"style": "primary",
			},
			{
				"name": "dialogueLaunchButtonCancel",
				"text": "Cancel",
				"type": "button",
				"value": "false",
				"style": "danger"
			}
		]
		}
	]
	)

def slackLaunchS1APITokenDialog(triggerID):
	open_dialog = slack_client.api_call(
		"dialog.open",
		trigger_id = triggerID,
		dialog = 
		{
		"title": "Enter S1 API Token:",
		"callback_id": "s1apidialog",
		"submit_label": "Submit",
		"elements": [
				{
				"type": "text",
				"label": "Enter your API Token",
				"name": "apitoken"
				}
		]
		}
	)

def updateSlackMessage(channel, ts, msg):
	slack_client.api_call(
		"chat.update",
		channel = channel,
		ts = message_ts,
		text = msg,
		attachments = []
	)

def slackS1SendMessage(channel, msg):
	slack_client.api_call(
		"chat.postMessage",
		channel = channel,
		as_user = 'true',
		text = msg
	)

def slackShutdownAgent(command):
	temp = command.replace("shutdown ", "")
	if isIPAddress(temp):
		id = sentienlGetAgentIDFromIP(temp)
	else:
		id = sentienlGetAgentIDFromName(temp)
	if id is not None:
		slackSendConfirmButton("Shutdown", id)
	else:
		return 'No such agent'

def slackRestartAgent(command):
	temp = command.replace("restart ", "")
	if isIPAddress(temp):
		id = sentienlGetAgentIDFromIP(temp)
	else:
		id = sentienlGetAgentIDFromName(temp)
	if id is not None:
		slackSendConfirmButton("Restart", id)
	else:
		return 'No such agent'

def slackUninstallAgent(command):
	temp = command.replace("uninstall ", "")
	if isIPAddress(temp):
		id = sentienlGetAgentIDFromIP(temp)
	else:
		id = sentienlGetAgentIDFromName(temp)
	if id is not None:
		slackSendConfirmButton("Uninstall", id)
	else:
		return 'No such agent'

def slackDisconnectFromNetwork(command):
	temp = command.replace("disconnect ", "")
	if isIPAddress(temp):
		id = sentienlGetAgentIDFromIP(temp)
	else:
		id = sentienlGetAgentIDFromName(temp)
	if id is not None:
		slackSendConfirmButton("Disconnect", id)
	else:
		return 'No such agent'

def slackReconnectToNetwork(command):
	temp = command.replace("reconnect ", "")
	if isIPAddress(temp):
		id = sentienlGetAgentIDFromIP(temp)
	else:
		id = sentienlGetAgentIDFromName(temp)
	if id is not None:
		slackSendConfirmButton("Reconnect", id)
	else:
		return 'No such agent'

def slackGetProcesses(command):
	strBuild = 'Processes:\n'
	temp = command.replace("processes ", "")
	if isIPAddress(temp):
		id = sentienlGetAgentIDFromIP(temp)
	else:
		id = sentienlGetAgentIDFromName(temp)
	if id is not None:
		processList = sentinelGetAgentProcesses(id)
		processList = set(processList)
		processList = sorted(processList, key=str.lower)
		for process in processList:
			strBuild += ' - ' + process + '\n'
		return strBuild
	else:
		return 'No such agent'

def slackGetPassphrase(command):
	temp = command.replace("passphrase ", "")
	if isIPAddress(temp):
		id = sentienlGetAgentIDFromIP(temp)
	else:
		id = sentienlGetAgentIDFromName(temp)
	if id is not None:
		passphrase = '`' + sentinelGetAgentProcesses(id).pop() + '`'
		return passphrase
	else:
		return 'No such agent'

def slackGetAgentDetailsFromIP(command):
	ip = command.replace("ip ", "")
	temp = sentinelGetAgentInformationBasedOnIP(ip)
	if temp is not None:
		return temp
	else:
		return "could not find agent for ip: " + ip

def slacksentinelGetUserDetails(command):
	tempCommand = command.replace("find admin ", "")
	temp = sentinelGetUserIDFromUsername(tempCommand)
	if temp is None:
		return("I was unable to find user:" + tempCommand)
	return sentinelGetUserDetails(temp)

def slacksentinelPrintBaseURL(command):
	if baseurl is None:
		return("You don't have a console set!")
	return baseurl

def slackGetAgentDetailsFromName(command):
	tempCommand = command.replace("find user ", "")

	nestedList = sentinelGetMachineDetails(tempCommand)

	pcNameList = nestedList[0]
	ipList = nestedList[1]
	pcTypeListList = nestedList[2]
	osList = nestedList[3]
	lastActiveDateList = nestedList[4]

	if not pcNameList:
		return "No agents found of user: " + tempCommand

	responseBuilder = "List of user's agents (last logged into)\n"
	loopCount = 0
	agentNamesAlreadyUsedList = list()
	for i in pcNameList:
		#skip duplicate agent names
		if any(j in pcNameList for j in agentNamesAlreadyUsedList):
			continue
		responseBuilder += 'Agent Name: ' + pcNameList[loopCount] + '\n'
		responseBuilder += 'Agent IP: ' + ipList[loopCount] + '\n'
		responseBuilder += 'Agent Type: ' + pcTypeListList[loopCount] + '\n'
		responseBuilder += 'Agent OS: ' + osList[loopCount] + '\n'
		responseBuilder += 'Last active: ' + lastActiveDateList[loopCount] + '\n'
		responseBuilder += '\n'
		agentNamesAlreadyUsedList.append(i)

	return responseBuilder

def slackTellMeYouLoveMe(command):
	return "I umm.... thanks?"

def slackCustomAPIRequest(command):
	temp = command.replace("custom ", "")
	#return sentinelCustomAPIRequest(temp)
	return json.dumps(sentinelCustomAPIRequest(temp),sort_keys=True, indent=4)

def slackTestMenu(channel):
	slack_client.api_call(
		"chat.postMessage",
		channel = channel,
		as_user = 'true',
		text = "Would you like to play a game?",
		response_type = "in_channel",
		attachments = [
			{
				"text": "Choose a game to play",
				"fallback": "If you could read this message, you'd be choosing something fun to do right now.",
				"color": "#3AA3E3",
				"attachment_type": "default",
				"callback_id": "test_menuu",
				"actions": [
					{
						"name": "games_list",
						"text": "Pick a game...",
						"type": "select",
						"options": [
							{
								"text": "Hearts",
								"value": "hearts"
							},
							{
								"text": "Bridge",
								"value": "bridge"
							},
							{
								"text": "Checkers",
								"value": "checkers"
							},
							{
								"text": "Chess",
								"value": "chess"
							},
							{
								"text": "Poker",
								"value": "poker"
							},
							{
								"text": "Falken's Maze",
								"value": "maze"
							},
							{
								"text": "Global Thermonuclear War",
								"value": "war"
							}
						]
					}
				]
			}
		]
	)

def slackRegenerateAPITokenButton(channel):
	slack_client.api_call(
			"chat.postMessage",
			channel = channel,
			as_user = 'true',
			attachments = [
			{
			"text": "Would you like to regenerate your API Token?",
			"fallback": "Unable to comply with your request",
			"callback_id": "confirmAPIRegenerateButtonID",
			"color": "#3AA3E3",
			"actions": [
				{
					"name": "yesbutton",
					"text": "Yes",
					"type": "button",
					"value": "confirm",
					"style": "primary",
				},
				{
					"name": "nobutton",
					"text": "No",
					"type": "button",
					"value": "false",
					"style": "danger"
				}

			]
			}
		]
		)


############################THESE METHODS WILL REQUIRE EXTRA HANDLING FOR CONFIRM BUTTONS#########################

# HAHA YEPP THAT WORKS PERFECTLY ON THE FIRST TRY i feel dumb not saving everything...
# warning - this turns off the agent's machine based on id
def sentinelShutdownAgent(slackUserID, id):
	s1APICredentials = searchJSONCredentials(slackUserID)
	if s1APICredentials is None:
		slackAPITokenPrompt("You do not have an API token registered with me")
	else:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1APICredentials})
		if s1APICredentialCheck():
			printWarning('SHUTTING DOWN AGENT')
			if id is None:
				printWarning('Host does not exist')
				return False
			r = s1session.post(baseurl + '/web/api/v1.6/agents/shutdown?id__in=' +id)
			if printAndCheckStatusCode(r):
				return True
			else:
				printError("failed to shutdown agent")
				if r.json() is not none:
					print 'raw json data:' + r.json()
				return False
		else:
			slackAPITokenPrompt("Your S1 API Token has expired")
	return False

# warning - this restarts the agent's machine based on id
def sentinelRestartAgent(slackUserID, id):
	s1APICredentials = searchJSONCredentials(slackUserID)
	if s1APICredentials is None:
		slackAPITokenPrompt("You do not have an API token registered with me")
	else:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1APICredentials})
		if s1APICredentialCheck():
			printWarning('RESTARTING AGENT: ' + id)
			if id is None:
				printWarning('Host does not exist')
				return False
			r = s1session.post(baseurl + '/web/api/v1.6/agents/'+id+'/restart-machine')
			if printAndCheckStatusCode(r):
				return True
			else:
				printError("failed to restart agents hardware ")
				if r.json() is not none:
					print 'raw json data:' + r.json()
				return False
		else:
			slackAPITokenPrompt("Your S1 API Token has expired")
	return False

# warning - this uninstalls the agent's machine based on id
def sentinelUninstallAgent(slackUserID, id):
	s1APICredentials = searchJSONCredentials(slackUserID)
	if s1APICredentials is None:
		slackAPITokenPrompt("You do not have an API token registered with me")
	else:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1APICredentials})
		if s1APICredentialCheck():
			printWarning('UNINSTALLING AGENT: ' + id)
			if id is None:
				printWarning('Host does not exist')
				return False
			r = s1session.post(baseurl + '/web/api/v1.6/agents/'+id+'/uninstall')
			if printAndCheckStatusCode(r):
				return True
			else:
				printError("failed to uninstall S1 from agent")
				if r.json() is not none:
					print 'raw json data:' + r.json()
				return False
		else:
			slackAPITokenPrompt("Your S1 API Token has expired")
	return False

# don't do this to yourself or you will not have interwebs - and will need your coworker 
# to reconnect you to the network 
def sentinelDisconnectAgentFromNetwork(slackUserID, id):
	s1APICredentials = searchJSONCredentials(slackUserID)
	if s1APICredentials is None:
		slackAPITokenPrompt("You do not have an API token registered with me")
	else:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1APICredentials})
		if s1APICredentialCheck():
			printLog('Disconnecting Agent to network')
			if id is None:
				printWarning('Host does not exist')
				return False
			r = s1session.post(baseurl + '/web/api/v1.6/agents/'+id+'/disconnect')
			if printAndCheckStatusCode(r):
				return True
			else:
				printError("failed to deconnect agent from network")
				if r.json() is not none:
					print 'raw json data:' + r.json()
				return False
		else:
			slackAPITokenPrompt("Your S1 API Token has expired")
	return False

#For when you accidently disconnect an agents machine from the network
def sentinelReconnectAgentToNetwork(slackUserID, id):
	s1APICredentials = searchJSONCredentials(slackUserID)
	if s1APICredentials is None:
		slackAPITokenPrompt("You do not have an API token registered with me")
	else:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1APICredentials})
		if s1APICredentialCheck():
			printLog('Reconnecting Agent to network')
			if id is None:
				printWarning('Host does not exist')
				return False
			r = s1session.post(baseurl + '/web/api/v1.6/agents/'+id+'/connect')
			if printAndCheckStatusCode(r):
				return True
			else:
				printError("failed to reconnect agent to network")
				if r.json() is not none:
					print 'raw json data:' + r.json()
				return False
		else:
			slackAPITokenPrompt("Your S1 API Token has expired")
	return False

#builder helper
"""
	s1APICredentials = searchJSONCredentials(slackUserID)
	if s1APICredentials is None:
		slackAPITokenPrompt("You do not have an API token registered with me")
	else:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1APICredentials})
		if s1APICredentialCheck():




		else:
			slackAPITokenPrompt("Your S1 API Token has expired")
	return False
"""

##########################END OF THESE METHODS WILL REQUIRE EXTRA HANDLING FOR CONFIRM BUTTONS#######################

def checkEverybodiesTokens(slackID, channel, manual = False):
	nestedList = returnJSONCredentials(slackID)
	currentApprovedUsersList = list()
	expiredList = list()
	slackEmails = list()
	sentinelEmails = list()
	matchingList = list()

	try:
		expiredList = nestedList.pop()
	except:
		print 'no expired tokens'
	try:
		currentApprovedUsersList = nestedList.pop()
	except:
		print 'no valid users???'
	for user in currentApprovedUsersList:
		data = slack_client.api_call("users.info", user = user)
		#goodNames.append(data['user']['real_name'])
							#[SlackID, email]
		slackEmails.append([user,data['user']['profile']['email']])
	#print slackEmails
	#for user in expiredList:
		#Send a message saying you're token has expired???
		#Delete the user from JSON file?

	printLog('retrieving user ID and email')
	r = s1session.get(baseurl + '/web/api/v1.6/users')
	if printAndCheckStatusCode(r):
		data = r.json()
		for item in data:
			theID = item["id"]
			theEmail = item["email"]
								#[ sentID, Email]
			sentinelEmails.append([theID, theEmail])
	else:
		printError("failed to retrieve user ID and email")
		if r.json() is not none:
			print 'raw json data:' + str(r.json())

	for slackList in slackEmails:
		for sentList in sentinelEmails:
			if slackList[1] == sentList[1]:
				matchingList.append([slackList[0],sentList[0],slackList[1]])
									#[SlackID  ,  SentID   ,  Email]
	print matchingList
	for match in matchingList:
		expireDays = sentinelCheckExpired(match[1])
		if expireDays < withinExpiredDays:
			slackS1SendMessage(match[0],'Your SentinelOne API token is going to expire in ' + str(expireDays) + ' days')
			slackRegenerateAPITokenButton(match[0])
		if manual and match[0] == slackID:
			#slackS1SendMessage(channel,'Your SentinelOne API token is going to expire in ' + str(expireDays) + ' days')
			#slackRegenerateAPITokenButton(slackID)
			pass

def sentinelRegenerateAPIToken(slackID):
	currentToken = searchJSONCredentials(slackID)
	s1session.headers.update({'Authorization' : 'APIToken ' + currentToken})
	r = s1session.post(baseurl + '/web/api/v1.6/users/generate-api-token')
	if printAndCheckStatusCode(r):
		APItoken = get_all(r.json(), 'token').pop()
		s1session.headers.update({'Authorization' : 'APIToken ' + APItoken})
		return APItoken
	else:
		printError("failed to regenerate API token")
		if r.json() is not None:
			print 'raw json data:' + str(r.json())
		return False

def sentinelCheckExpired(sentID):
	printLog('Checking if token expires within ' + str(withinExpiredDays) + ' days')
	r = s1session.get(baseurl + '/web/api/v1.6/users/' + sentID + '/api-token-details')
	if printAndCheckStatusCode(r):
		expireString = get_all(r.json(), 'expires_at').pop()
		#convert expireString
		expireString = str(expireString[:10])
		#print expireString
		expireDateTime = datetime.datetime.strptime(expireString, '%Y-%m-%d')
		#get Current Date
		today = datetime.datetime.today()#.strftime('%Y-%m-%d')
		#compare Dates
		delta = expireDateTime - today
		print 'expires in ' + str(delta.days) + ' days'
		return delta.days
	else:
		printError("failed to check if token will expire within " + str(withinExpiredDays))
		if r.json() is not none:
			print 'raw json data:' + str(r.json())
		return -1

def sentinelGetAgentProcesses(id):
	printLog('returning agent processes from ' + id)
	if id is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/agents/' + id + '/processes')
	if printAndCheckStatusCode(r):
		try:
			processes = get_all(r.json(), 'process_name')
			return processes
		except:
			return None
	else:
		printError("failed to retrieve processes from " + id)
		if r.json() is not None:
			print 'raw json data:' + str(r.json())
		return None

def sentinelGetAgentProcesses(id):
	printLog('returning agent passphrase from ' + id)
	if id is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/agents/' + id + '/passphrase')
	if printAndCheckStatusCode(r):
		try:
			passphrase = get_all(r.json(), 'passphrase')
			return passphrase
		except:
			return None
	else:
		printError("failed to retrieve passphrase from " + id)
		if r.json() is not None:
			print 'raw json data:' + str(r.json())
		return None

def sentinelCustomAPIRequest(customRequest):
	printLog('attempting custom API request')
	r = s1session.get(baseurl + customRequest)
	if printAndCheckStatusCode(r):
		if r.json() is not None:
			return r.json()
		else:
			return 'Success!'
	elif r.status_code == 405:
		r = s1session.post(baseurl + customRequest)
		if printAndCheckStatusCode(r):
			if r.json() is not None:
				return r.json()
			else:
				return 'Success!'
	else:
		printWarning('Failed custom request')
		return 'Failed'

def sentienlGetActiveDirectory():
	printLog('returning agent id from ip...')
	if ip is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/settings/active-directory')
	if printAndCheckStatusCode(r):
		try:
			agentID = get_all(r.json(), 'id').pop()
			return agentID
		except:
			return None
	else:
		printError("failed to retrieve agent id from ip")
		if r.json() is not None:
			print 'raw json data:' + str(r.json())
		return None

def sentienlGetAgentIDFromIP(ip):
	printLog('returning agent id from ip...')
	if ip is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/agents/iterator?query=' + ip + '&limit=1')
	if printAndCheckStatusCode(r):
		try:
			agentID = get_all(r.json(), 'id').pop()
			return agentID
		except:
			return None
	else:
		printError("failed to retrieve agent id from ip")
		if r.json() is not None:
			print 'raw json data:' + str(r.json())
		return None

def sentienlGetAgentIDFromName(agentName):
	printLog('returning agent id from name...')
	if agentName is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/agents/iterator?query=' + agentName + '&limit=1')
	if printAndCheckStatusCode(r):
		try:
			agentID = get_all(r.json(), 'id').pop()
			return agentID
		except:
			return None
	else:
		printError("failed to retrieve agent id from ip")
		if r.json() is not none:
			print 'raw json data:' + str(r.json())
		return None

# returns agent information based on ip
def sentinelGetAgentInformationBasedOnIP(ip):
	printLog('returning Agent Information...')
	if ip is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/agents/iterator?query=' + ip + '&limit=1')
	if printAndCheckStatusCode(r):
		try:
			machineName = get_all(r.json(), 'computer_name').pop()
			agentID = get_all(r.json(), 'id').pop()
			UUID = get_all(r.json(), 'uuid').pop()
			isDecomissioned = get_all(r.json(), 'is_decommissioned').pop()
			networkStatus = get_all(r.json(), 'network_status').pop()
			strbuilder = '\nmachineName: '+ str(machineName) + '\nip: ' + ip + '\nagentID: '+ str(agentID) + '\nUUID: '+ str(UUID)+ '\nis decommissioned: '+ str(isDecomissioned)+ '\nnetwork status: '+ str(networkStatus)+ '\n'
			return strbuilder
		except:
			return None
	else:
		printError("failed to find agent information ")
		return None

def sentinelGetMachineDetails(lastloginName):
	printLog('Showing User Details')
	if lastloginName is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/agents?query=' + lastloginName)
	if printAndCheckStatusCode(r):


		pcNameList = get_all(r.json(), 'computer_name')
		ipList = get_all(r.json(), 'external_ip')
		pcTypeListList = get_all(r.json(), 'machine_type')
		osList = get_all(r.json(), 'os_name')
		lastActiveDateList = get_all(r.json(), 'last_active_date')


		return [pcNameList,ipList,pcTypeListList,osList,lastActiveDateList]
	else:
		printError("failed to show user details")
		if r.json() is not None:
			print 'raw json data:' + str(r.json())

# returns all of the details in a pretty json response of the user's details
def sentinelGetUserDetails(userid):
	printLog('Showing User Details')
	if userid is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/users/'+userid)
	if printAndCheckStatusCode(r):
		print json.dumps(r.json(), indent=4)
		return json.dumps(r.json(), indent=4)
	else:
		printError("failed to show user details")
		if r.json() is not none:
			print 'raw json data:' + str(r.json())

# Super inefficient but the only way - have to get a json response of every single user
# on the account, parse through it to locate the username, and then print only the userID
# the get_all method will not work for this purpose because it would return other ids
# since 'group' has its own id NAMED id FOR SOME REASON
# would be more efficient if we only called this once and stored the data during the session
# but were not limited on API calls so that's fine
def sentinelGetUserIDFromUsername(usrname):
	printLog('retrieving user ID')
	if usrname is None:
		printWarning('Host does not exist')
		return False
	r = s1session.get(baseurl + '/web/api/v1.6/users')
	if printAndCheckStatusCode(r):
		data = r.json()
		for item in data:
			if usrname in item["username"]:
				theID = item["id"] 
				print theID
				return theID
		return None
	else:
		printError("failed to retrieve user ID")
		if r.json() is not none:
			print 'raw json data:' + str(r.json())

# this is my beautiful recursive search function that returns an array of all instances of a key
# within a json response - Sentinel One has many different types of json inside lists and arrays
# all nested within each other so recursion is the only way to go - and it does have to go through
# the entire json response
# THIS WILL RETURN A LIST EVEN IF IT IS ONLY 1 ITEM FOUND SO YOU MUST POP() TO GET CLEAN INPUT
def get_all(myjson, key):
	recursiveResult = []
	if type(myjson) == str:
		myjson = json.loads(myjson)
	if type(myjson) is dict:
		for jsonkey in myjson:
			if type(myjson[jsonkey]) in (list, dict):
				recursiveResult += get_all(myjson[jsonkey], key)
			elif jsonkey == key:
				recursiveResult.append(str(myjson[jsonkey]))
	elif type(myjson) is list:
		for item in myjson:
			if type(item) in (list, dict):
				recursiveResult += get_all(item, key) 
	return recursiveResult

def isIPAddress(check):
	a = check.split('.')
	if len(a) != 4:
		printLog('Not an IP address - incorrect number of sections')
		return False
	for x in a:
		if not x.isdigit():
			printLog('Not an IP address, non digits exist')
			return False
		i = int(x)
		if i < 0 or i > 255:
			printLog('Not an IP address - invalid range of numbers')
			return False
	printLog('Is valid IP address')
	return True

# based on status code from response; really just makes things green, red, or blue
def printAndCheckStatusCode(r):
	if r.status_code == 200 or r.status_code == 204 or r.status_code == 201:
		printSuccess(str(r))
		return True
	elif r.status_code == 405:
		printError(str(r) + " - may need to change 'post' method to 'get' or vise versa")
	else:
		printError(str(r))
	return False

# put these here from utilities file so we don't need 
# to instatiate every single time we need to print
# basically just makes your log pretty and easier to read
def printSuccess(msg):
	print(Utilities.OKGREEN + "[OK]" + msg + Utilities.ENDC)
def printError(msg):
	print(Utilities.FAIL + "[ERROR]" + msg + Utilities.ENDC + str(sys.exc_info()[0]))
def printException(msg):
	print(Utilities.FAIL + "[EXCEPTION]" + msg + Utilities.ENDC + str(sys.exc_info()[0]))
def printLog(msg):
	print(Utilities.OKBLUE + "[LOG]" + msg + Utilities.ENDC)
def printWarning(msg):
	print(Utilities.WARNING + "[ATTENTION]" + msg + Utilities.ENDC)

def updateJSONCredentials(slackID, s1token):
	try:
		with open('tokens.json', mode='r') as feedsjson:
			feeds = json.load(feedsjson)
	except:
		printWarning("Unable to find proper JSON data in tokens.json")
		feeds = list()

	count = -1
	for item in feeds:
		count += 1
		if slackID in item['slackUserID']:
			feeds[count]['s1apiToken'] = s1token
			with open('tokens.json', mode='w') as feedsjson:
				json.dump(feeds, feedsjson)
			return

	with open('tokens.json', mode='w') as f:
		json.dump([], f)

	with open('tokens.json', mode='w') as feedsjson:
		entry = {'slackUserID': slackID, 's1apiToken': s1token}
		feeds.append(entry)
		json.dump(feeds, feedsjson)

def searchJSONCredentials(slackID):
	try:
		with open('tokens.json') as f:
			data = json.load(f)
		for item in data:
			if slackID in item['slackUserID']:
				connectedToken = item['s1apiToken']
				return connectedToken
		return None
	except:
		return None

def returnJSONCredentials(slackID):
	slackUserID = list()
	slackExpiredTokenID = list()
	try:
		with open('tokens.json') as f:
			data = json.load(f)
		for item in data:
			connectedToken = item['s1apiToken']
			s1session.headers.update({'Authorization' : 'APIToken ' + connectedToken})
			if s1APICredentialCheck():
				slackUserID.append(item['slackUserID'])
				#print slackUserID
			else:
				slackExpiredTokenID.append(item['slackUserID'])
				#print slackExpiredTokenID
		currentToken = searchJSONCredentials(slackID)
		s1session.headers.update({'Authorization' : 'APIToken ' + currentToken})
		return [slackUserID,slackExpiredTokenID]
	except Exception as e: 
		print e
		return None

#TODO
def deleteJSONCredentials(slackID):
	pass

def sentinelTest(slackUserID):
	s1APICredentials = searchJSONCredentials(slackUserID)
	if s1APICredentials is None:
		slackAPITokenPrompt("You do not have an API token registered with me")
	else:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1APICredentials})
		if s1APICredentialCheck():
			r = s1session.get(baseurl + '/web/api/v1.6/users')
			if printAndCheckStatusCode(r):
				return True
			print r.json()
			return False
		else:
			slackAPITokenPrompt("Your S1 API Token has expired")

def s1APICredentialCheck():
	r = s1session.get(baseurl + '/web/api/v1.6/users')
	if printAndCheckStatusCode(r):
		return True
	return False


		# Sends the response back to the channel
	slack_client.api_call(
		"chat.postMessage",
		channel=channel,
		text=response or default_response
	)

def update_invalid_token(slackUserID, token):
	s1apiToken = token
	if s1apiToken is not None:
		s1session.headers.update({'Authorization' : 'APIToken ' + s1apiToken})
		if s1APICredentialCheck():
			updateJSONCredentials(slackUserID,s1apiToken)
			return True
		else:
			printError('Invalid token')
			return False
	else:
		printError('Empty field')
		return False

def handle_bot_command(command, channel, slackUserID):
	try:
		s1CorrectAPICredentials = None
		s1CorrectAPICredentials = searchJSONCredentials(slackUserID)
		if s1CorrectAPICredentials is None:
			slackAPITokenPrompt("You do not have an API token registered with me")
		else:
			s1session.headers.update({'Authorization' : 'APIToken ' + s1CorrectAPICredentials})
			if s1APICredentialCheck():
				handle_command(command, channel, slackUserID)
			else:
				slackAPITokenPrompt("Your S1 API Token has expired")
	except Exception as e:
		slackS1SendMessage(channel, 'You broke me because of: \n' + str(e))
		time.sleep(5)

#TODO: MAKE THREADS TIME OUT

if __name__ == "__main__":
	while True:
		if slack_client.rtm_connect(with_team_state=False, auto_reconnect = True):
			print("S1Bot connected and running!")
			# Read bot's user ID by calling Web API method `auth.test`
			starterbot_id = slack_client.api_call("auth.test")["user_id"]
			while True:
				command, channel, slackUserID = parse_bot_commands(slack_client.rtm_read())
				if command:
					thread.start_new_thread(handle_bot_command, (command, channel, slackUserID))
				time.sleep(RTM_READ_DELAY)
		else:
			print("Connection failed. Exception traceback printed above.")




