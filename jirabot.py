#!/usr/bin/python
# -*- coding: utf-8 -*-
from multiprocessing.dummy import Pool as ThreadPool
import thread
import os
import base64
from bs4 import BeautifulSoup
import time
import datetime
import re
import requests
import email
from util import Utilities
import json
import getpass
import sys
import random
from slackclient import SlackClient
from multiprocessing import Process,Pipe
import socket
from threading import Timer
from jira import JIRA

# instantiate Slack client
#this is the OAuth bot token for s1app
slack_client =	SlackClient('')
baseurl = 'https://Company.sentinelone.net'


#TODO: SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "do"
MENTION_REGEX = r"^<@(|[WU].+?)>(.*)"
COLOR_REGEX = r"{color.*?}"
HTML_REGEX = r"<html.*?<\/html>"
Base64_REGEX_Attachment = r"(?<=base64)(.*?)(?=--attachment--)"
Base64_REGEX_From = r"(?<=base64)(.*?)(?=From)"
#Base64_END_REGEX = r"(?<=base64).*"
From_REGEX = r"(?<=mynewlinecharactersFrom:).*?(?=(mynewlinecharactersTo:|mynewlinecharactersSubject:|mynewlinecharactersDate:))"
To_REGEX = r"(?<=mynewlinecharactersTo:).*?(?=mynewlinecharactersDate:|mynewlinecharactersSubject:|mynewlinecharactersX-|mynewlinecharactersContent-|mynewlinecharactersReceived:|mynewlinecharactersMessage-)"

jql = 'labels = "~Potential_Malware_Phishing~" AND status != "RESOLVED"'
NumberOfMaxResults = 200
automationCommentAuthor = ''

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

#Main interface, here we parse for commands mentioned to the bot to launch different actions based on input
def handle_command(command, channel, slackID):
	"""
		Executes bot command if the command is known
	"""


	# Default response is help text for the user
	listOfCommands = "=== Testing ===\n"
	listOfCommands += "[I love you]\n"
	listOfCommands += "\n"
	listOfCommands += "=== Function ===\n"
	listOfCommands += "[init]			the main funciton of jira phish bot\n"
	listOfCommands += "	-Blocked Canned Response button will respond with a comment stating the URLs have already been blocked\n"
	listOfCommands += "	-Threat Canned Response button will respond with a comment stating the user is being threatened into paying a ransome without any substance\n"
	listOfCommands += "	-Spam Canned Response button will respond with a comment stating the URLs are not dangerous just spam\n"
	listOfCommands += "	-Custom Canned Response button will respond with a custom comment that you input yourself\n"
	listOfCommands += "		-drop down menu - will block link in mimecast\n"
	listOfCommands += "\n"
	listOfCommands += "[update]			force update of all tickets (grabs new tickets from jira)\n"
	listOfCommands += "[get] <ticket key>				returns a ticket key if it exists in server json file\n"
	listOfCommands += "[put] <ticket key>				manually inserts a ticket key into the server json file\n"
	listOfCommands += "[delete] <ticket key>			deletes a ticket key if it exists in server json file\n"
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
	if command.startswith("i love you"):
		response = slackTellMeYouLoveMe(command)
	if command.startswith('break'):
		raise Exception('Manually thrown Exception')
	if command.startswith('init'):
		response = None
		default_response = None
		jiraPhishInitiateButton(False)
	if command.startswith('put'):
		temp = command.replace("put ", "")
		response = put_JSON_key(temp)
		default_response = "Failed to put key somehow"
	if command.startswith('delete'):
		temp = command.replace("delete ", "")
		response = delete_JSON_key(temp)
		default_response = "No key found"
	if command.startswith('update'):
		jiraPhishInitiateButton(True)
		default_response = None
	if command.startswith('get'):
		temp = command.replace("get ", "")
		response = get_JSON_Key(temp)
		default_response = "No key found"

	# Sends the response back to the channel
	slack_client.api_call(
		"chat.postMessage",
		channel=channel,
		text=response or default_response
	)

#testing method
def slackTellMeYouLoveMe(command):
	return "I umm.... thanks?"


#updates a message in slack, ts is the slack set timestamp of the message
def jiraUpdateSlackMessage(channel, ts, msg):
	slack_client.api_call(
		"chat.update",
		channel = channel,
		ts = message_ts,
		text = msg,
		attachments = []
	)

#send a slack message to the specified channel
def jiraSlackSendMessage(channel, msg):
	slack_client.api_call(
		"chat.postMessage",
		channel = channel,
		as_user = 'true',
		text = msg
	)

#button to start the dialog for login credentials that leads to the main module of this program
def jiraPhishInitiateButton(update):
	if update == False:
		update = 'false'
	else:
		update = 'true'
	slack_client.api_call(
		"chat.postMessage",
		channel = channel,
		as_user = 'true',
		attachments = [
		{
		"text": 'You will need to login with your Jira credentials here',
		"fallback": "Unable to comply with your request",
		"callback_id": "initiateJira",
		"color": "#3AA3E3",
		"actions": [
			{
				"name": "dialogueLaunchButton",
				"text": "Launch Jira",
				"type": "button",
				"value": "confirm|" + update,
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

#prompted from button - leads to the launching of the main module of this program
def jiraLoginDialog(triggerID, update):
	if update == 'true':
		callbackID = 'jiraLoginDialogUpdate'
	else:
		callbackID = "jiraLoginDialog"
	open_dialog = slack_client.api_call(
		"dialog.open",
		trigger_id = triggerID,
		dialog = 
		{
		"title": "Enter Jira Credentials:",
		"callback_id": callbackID,
		"submit_label": "Submit",
		"elements": [
				{
				"type": "text",
				"label": "Enter your Username",
				"name": "username"
				},
				{
				"type": "text",
				"label": "Enter your password",
				"name": "password"
				}
		]
		}
	)

#We attempt to login with the credentials given in the prompted slack dialog, if it fails we respond with false, false
# in the server if we recieve false, false we give a message saying they may need to redo their capatcha
def jiraAttemptLogin(uname, pwd):
	try:
		jira = JIRA(basic_auth=(uname, pwd), options = {'server': 'https://jira.Company.com'})
		return jira,pwd
	except:
		return False, False

#Module gets called from the server, kicks off the message and deletes the key from jiraKeys.json in the server so that multiple issues
# will not be sent to different concurrent users.
def jiraPhishingMain(slackChannel, jira, LoggedInUser, passw):
	key = get_next_JSON_Key()
	if key is not None:
		delete_JSON_key(key)
		#commentedTicket = jira.issue(ticket.key, expand='renderedFields')
		jiraSendIssue(key, jira, slackChannel, LoggedInUser, passw)
		return True
	else:
		jiraSlackSendMessage(slackChannel, "Looks like I'm all out of work for you!")
		return False

#We send back up to 200 tickets , using x3 to make sure we will bring back extra tickets as not all will be processed by the automation comment module yet
def JiraGetTickets(jira, maxTickets):
	if (maxTickets * 3) > NumberOfMaxResults:
		return jira.search_issues(jql, maxResults = NumberOfMaxResults)
	else:
		return jira.search_issues(jql, maxResults = (maxTickets * 3))


#The surprising meat of the operation - sneakily sending login credentials in the value parameters of whatever button is pressed, 
# heavy work of parsing emails and attachments, formatting everything in an easily readable slack message, 
# button prompts for resolutions, urls to the ticket, dropdown menu of all URLs found in automation comment,
# all formatted to slacks json requirements for a loaded up message full of interactive elements and attachments
def jiraSendIssue(key, jira, channel, LoggedInUser, jiraPass):
	from_address = ""
	to_address = ""
	from_to_string = ""
	emailSendMesage = ""
	emailBody = ""
	extraJSONattachment = ""
	issue = jira.issue(key, expand='renderedFields')
	attachments = issue.fields.attachment
	attachmentTypeString = ""
	for attach in attachments:
		attachmentTypeString += attach.filename.encode('utf-8').strip() + "\n"
		if attach.filename.endswith('.eml'):
			emailBody = ""
			data = attach.get()
			msg = email.message_from_string(data)
			tempmsg = str(msg).replace('\r\n','mynewlinecharacters')
			tempmsg = tempmsg.replace('\n','mynewlinecharacters')
			try:
				from_address = re.search(From_REGEX, str(tempmsg)).group()
			except Exception as e:
				print e
			try:
				to_address = re.search(To_REGEX, str(tempmsg)).group()
			except Exception as e:
				print e
			try:
				from_to_string = "*To:* " + str(to_address) + "\n*From:* " + str(from_address) + "\n"
				from_to_string = from_to_string.replace('mynewlinecharacters', '\n') 
			except Exception as e:
				print e
			#attachmentsssss = msg.get_payload()
			#for attachmentss in attachmentsssss:
				#try:
					#fnam=attachmentss.get_filename()
					#print fnam
					#print attachmentss.get_payload()
				#except Exception as e:
					#print e
			if msg.is_multipart():
				for payload in msg.get_payload():
					emailBody += str(payload)
			else:
				emailBody = msg.get_payload()
			#emailBody = unicode(str(msg.get_payload(decode=False)), errors = 'replace')
			emailAttachments = msg.get_payload()
			iterEmailAttachments = iter(emailAttachments)
			next(iterEmailAttachments)
			for emailAttach in iterEmailAttachments:
				try:
					extraJSONattachment += "Email attachment type: " + str(emailAttach.get_content_type()) + "\n"
					if not str(emailAttach.get_content_type()).startswith("image"):
						pass
				except:
					pass#extraJSONattachment += str(emailAttach)

					#extraJSONattachment += "\nEmail Content: " + str(unicode(str(emailAttach.get_payload(decode=True)) + "\n", errors = 'replace'))
			#base64.b64decode(coded_string)
	if emailBody is None:
		emailBody = ""
	if not emailBody == "":
		emailBody = "*Email Body:*\n" + emailBody

	emailBody = emailBody.replace('=\r\n', '')
	try:
		#tempEmailBody = emailBody.replace('\n', '').replace('\r', '')


		#tempEmailBody += 'From'
		emailSendMesage += emailBody
		#emailBody = base64.b64decode(Base64String.encode('utf-8').strip())



	except Exception as e:
		print e
	comments = jira.comments(key)
	lukeComment = "\n\n*Luke\'s automation Comment*\n"
	otherComment = "\n\n*Other Comments*\n\n"
	for comment in comments:
		if comment.author.name == automationCommentAuthor:
			set_current_comment_URLs(key, comment.body)
			lukeComment += str(comment.body) + '\n\n'
		else:
			otherComment += "Author: " + str(comment.author.name.encode("utf-8")) + "\nComment:\n" + str(comment.body.encode("utf-8"))
	slack_client.api_call(
			"chat.postMessage",
			text = '*Ticket ' + key + '*',
			channel = channel,
			as_user = 'true',
			mrkdwn = 'true',
			attachments = [
				{
				"text": '\n*Issue Body*\n' + re.sub(COLOR_REGEX, "", issue.fields.description),
				"color": "#f9f61d"
				},
				{
				"text": lukeComment,
				"fallback": "You are unable to choose mimecast block",
				"color": "#f91de3",
				"callback_id": "mimeCastBlock|" +key,
				"attachment_type": "default",
				"actions":[
					{
						"name": "mimecastOptions",
						"type": "select",
						"text": "Mimecast URL Block",
						"data_source": "external"
					}
				]
				},
				{
				"text": re.sub(COLOR_REGEX, "", otherComment),
				"color": "#f9921d"
				},
				{
				"text": from_to_string + emailSendMesage,
				"color": "#ff0000",
				},
				{
				"text": extraJSONattachment,
				"color": "#ad0d0d"
				},
				{
				"text": "Choose a resolution for `" + key +"`",
				"fallback": "You are unable to choose a resolution",
				"callback_id": "phishingTicketResolution",
				"color": "#3AA3E3",
				"attachment_type": "default",
				"actions": [
					{
						"name": "game",
						"text": "Blocked Canned Response",
						"type": "button",
						"value": "blocked|" + key + "|" + LoggedInUser + "|" + jiraPass
					},
					{
						"name": "game",
						"text": "Threat Canned Response",
						"type": "button",
						"value": "threat|" + key + "|" + LoggedInUser + "|" + jiraPass
					},
					{
						"name": "game",
						"text": "Spam Canned Response",
						"type": "button",
						"value": "spam|" + key + "|" + LoggedInUser + "|" + jiraPass
					},
					{
						"name": "game",
						"text": "DNR Canned response",
						"type": "button",
						"value": "donotreply|" + key + "|" + LoggedInUser + "|" + jiraPass
					},
					{
						"name": "game",
						"text": "Custom Response",
						"type": "button",
						"value": "custom|" + key + "|" + LoggedInUser + "|" + jiraPass
					}
				]
				},
				{
				"fallback": "You are unable to choose a resolution",
				"callback_id": "phishingTicketResolution",
				"attachment_type": "default",
				"actions": [
					{
						"type": "button",
						"text": "Take me to the ticket",
						"style": "primary",
						"url": "https://jira.Company.com/browse/" + key
					},
					{
						"name": "nobutton",
						"text": "Cancel - Next Ticket",
						"type": "button",
						"value": "cancel|" + key + "|" + LoggedInUser + "|" + jiraPass,
						"style": "danger"
					},
					{
						"name": "closebutton",
						"text": "Close Session",
						"type": "button",
						"value": "close|" + key + "|" + LoggedInUser + "|" + jiraPass
					},
					{
						"name": "reloadbutton",
						"text": "Reload Ticket",
						"type": "button",
						"value": "reload|" + key + "|" + LoggedInUser + "|" + jiraPass
					}
				]
				}
			]
	)

#launched when a ticket is to be resolved in the slack bot.  We resolve the issue -assign it to whomever logged in 
# and send a confirmation comment.  Then we send the next ticket back to slack.
def JiraAssignCommentAndResolveTicket(key, JiraUserName, jiraMessage, channel, JiraPassword):
	jira = JIRA(basic_auth=(JiraUserName, JiraPassword), options = {'server': 'https://jira.Company.com'})
	issue = jira.issue(key)
	jira.assign_issue(issue, JiraUserName)
	#sleep to make sure the assign change goes through and we can find the resolve issue id
	time.sleep(5)
	transitions = jira.transitions(issue)
	#print [(t['id'], t['name']) for t in transitions]
	for t in transitions:
		if t['name'] == 'Resolve Issue':
			id = t['id']
			#print id
			continue
	try:
		jira.transition_issue(issue, id)
	except:
		time.sleep(1)
		try:
			jira.transition_issue(issue, id)
		except:
			print 'ERROR JIRA WAS UNABLE TO FINISH RESOLVING: ' + issue.key
			jiraSlackSendMessage(channel, 'We were unable to resolve this issue for some reason...  Get Luke to fix this!')
	jira.add_comment(issue = issue.key, body = jiraMessage, is_internal = False)
	#send the next ticket
	thread.start_new_thread(jiraPhishingMain,(channel, jira, JiraUserName, JiraPassword))

#called only when the users decides to skip over the ticket - jiraPhishingMain cannot be called without a valid jira object.
# since jira cannot be passed between slack and our server we have to relogin everytime.  This is the reason we are passing login/pass
# between all these methods
def JiraSendNext(channel, JiraUserName, JiraPassword):
	jira = JIRA(basic_auth=(JiraUserName, JiraPassword), options = {'server': 'https://jira.Company.com'})
	thread.start_new_thread(jiraPhishingMain,(channel, jira, JiraUserName, JiraPassword))

#reloads the ticket, used for testing purposes
def JiraResend(channel, JiraUserName, JiraPassword, key):
	jira = JIRA(basic_auth=(JiraUserName, JiraPassword), options = {'server': 'https://jira.Company.com'})
	thread.start_new_thread(jiraSendIssue, (key, jira, channel, JiraUserName, JiraPassword))


#Custom dialog response for if the user needs a response to the customer outside of the canned responses.
def launchCustomCommentDialog(sdticket, JiraUserName, triggerID, jiraPass):
	open_dialog = slack_client.api_call(
		"dialog.open",
		trigger_id = triggerID,
		dialog = 
		{
		"title": "Comment for: " + sdticket,
		"callback_id": "customCommentDialog|" + sdticket + "|" + JiraUserName + "|" + jiraPass,
		"submit_label": "Submit",
		"elements": [
				{
				"type": "text",
				"label": "Enter comment",
				"name": "comment"
				}
		]
		}
	)


####################################### BEGIN jiraKeys.json HANDLING ###################################

"""		what the .json is going to look like in jiraKeys.json
[
	{"key": "SD-#####"}, 
	{"key": "SD-#####"}, 
	{"key": "SD-#####"}, 
	{"key": "SD-#####"}, 
	{"key": "SD-#####"}
]
"""

#Here we put a key back into jiraKeys.json.  This happens when an issue is skipped over - that way other people can resolve the issue
# or the user can come back to it later as it is put back into the issue Queue
def put_JSON_key(key):
	key = key.upper()
	try:
		with open('jiraKeys.json', mode='r') as feedsjson:
			feeds = json.load(feedsjson)
	except:
		printWarning("Unable to find proper JSON data in jiraKeys.json")
		feeds = list()

	for item in feeds:
		if key in item["key"]:
			return False


	with open('jiraKeys.json', mode='w') as f:
		json.dump([], f)

	with open('jiraKeys.json', mode='w') as feedsjson:
		entry = {'key': key}
		feeds.append(entry)
		json.dump(feeds, feedsjson)
	return True

#returns the key if it exists, used for testing purposes
def get_JSON_Key(key):
	key = key.upper()
	try:
		with open('jiraKeys.json') as f:
			data = json.load(f)
		for item in data:
			if key in item["key"]:
				return item["key"]
		return None
	except:
		return None

#returns the next key in the queue if there are any
def get_next_JSON_Key():
	try:
		with open('jiraKeys.json') as f:
			data = json.load(f)
		for item in data:
			return item["key"]
		return None
	except Exception as e:
		print e
		return None

def delete_JSON_key(key):
	key = key.upper()
	try:
		with open('jiraKeys.json', mode='r') as feedsjson:
			feeds = json.load(feedsjson)
	except:
		printWarning("Unable to find proper JSON data in jiraKeys.json")
		feeds = list()

	i = 0
	for item in feeds:
		if key in item["key"]:
			feeds.pop(i)
			with open('jiraKeys.json', 'w') as data_file:
				json.dump(feeds, data_file)
			return True
		i += 1

	return False

def update_JSON_keys(user,passw, channel):
	jira,pwd = jiraAttemptLogin(user,passw)
	if jira is False:
		jiraSlackSendMessage(channel, "Failed somehow")
		return

	feeds = list()
	count = 1
	commentedJiraTicketObjects = list()
	JiraTicketObjects = JiraGetTickets(jira, 200)
	#JiraTicketObjects = set(JiraTicketObjects)
	dupesCheck = list()
	#TODO make this wait until resolution to send the next ticket
	for ticket in JiraTicketObjects:
		for comment in jira.comments(ticket.key):
			if comment.author.name == automationCommentAuthor:
				commentedJiraTicketObjects.append(ticket)
	for commentedTicket in commentedJiraTicketObjects:
		if not commentedTicket.key in dupesCheck:
			entry = {'key': commentedTicket.key}
			feeds.append(entry)
			count += 1
			if count > 200:
				break
		dupesCheck.append(commentedTicket.key)

	with open('jiraKeys.json', mode='w') as feedsjson:
		json.dump(feeds, feedsjson)

	jiraSlackSendMessage(channel, "Updated JSON key file!")

####################################### END jiraKeys.json HANDLING ###################################

####################################### BEGIN currentURLS.json HANDLING ###################################

"""		what the .json is going to look like in currentURLS.json
[
	{
	"elements": [
		{"URL": "https://example.com"},
		{"URL": "https://example.com"}
	], 
	"key": "SD-#####"
	}, 
	{
	"elements": [], 
	"key": "SD-#####"
	}, 
	{
	"elements": [
		{"URL": "https://example.com"},
		{"URL": "https://example.com"},
		{"URL": "https://example.com"}
	], 
	"key": "SD-#####"
	}
]
"""

#generates the currentURLS.json file if it does not exist, adds the entry if it does not exist in a dynamic list.
def set_current_comment_URLs(key, automationComment):
	try:
		with open('currentURLS.json', mode='r') as feedsjsondata:
			data = json.load(feedsjsondata)
	except:
		printWarning("Unable to find proper JSON data in currentURLS.json")
		data = list()

	urllist = list()
	entry = {}
	feeds = list()
	urls = list()
	ticketList = list()
	lines = automationComment.split("\n")
	for line in lines:
		space_split = line.split(" ")
		for candidate in space_split:
			if candidate.startswith("http"):
				#print candidate
				urls.append(candidate)


	urls = set(urls)

	for sdTicket in data:
		#print sdTicket
		ticketList = sdTicket['key']

	#print 'ticketList: ' + str(ticketList)
	if not key in ticketList:
		for url in urls:
			entry = {'URL': url}
			urllist.append(entry)

		listEntry = (
		{
		'key': key,
		'elements': urllist
		}
		)
		data.append(listEntry)


	with open('currentURLS.json', mode='w') as feedsjson:
		json.dump(data, feedsjson)

#returns a list of all the URL elements in currentURLS.json.  This is used to populate the dynamic dropdown menu in our slack messages.
def get_current_comment_URLs(key):
	URL_list = list()
	with open('currentURLS.json', mode='r') as feedsjson:
		feeds = json.load(feedsjson)
	for ticket in feeds:
		if key in ticket["key"]:
			for item in ticket["elements"]:
				try:
					URL_list.append(item["URL"])
				except:
					return None
	return URL_list

# when the dropdown menu url is clicked on we want to remove it from the list so we are not sending redudant requests to mimecast.
# this opens and modifies the currentURLs.json file deleting only the URL in the elements list.
def delete_current_comment_URLs(key, url):
	try:
		with open('currentURLS.json', mode='r') as feedsjson:
			feeds = json.load(feedsjson)
	except:
		printWarning("Unable to find proper JSON data in currentURLS.json")
		feeds = list()
	for ticket in feeds:
		if key in ticket["key"]:
			i = 0
			for item in ticket["elements"]:
				#print item
				if url in item["URL"]:
					print ticket["elements"].pop(i)
					with open('currentURLS.json', 'w') as data_file:
						json.dump(feeds, data_file)
					return True
				i += 1
	return False


####################################### END currentURLS.json HANDLING ###################################



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

def handle_bot_command(command, channel, slackUserID):
	try:
		handle_command(command, channel, slackUserID)
	except Exception as e:
		jiraSlackSendMessage(channel, 'You broke me because of: \n' + str(e))
		time.sleep(5)

#TODO: MAKE THREADS TIME OUT

if __name__ == "__main__":
	while True:
		if slack_client.rtm_connect(with_team_state=False, auto_reconnect = True):
			print("Jira Phish Bot connected and running!")
			# Read bot's user ID by calling Web API method `auth.test`
			starterbot_id = slack_client.api_call("auth.test")["user_id"]
			while True:
				command, channel, slackUserID = parse_bot_commands(slack_client.rtm_read())
				if command:
					thread.start_new_thread(handle_bot_command, (command, channel, slackUserID))
				time.sleep(RTM_READ_DELAY)
		else:
			print("Connection failed. Exception traceback printed above.")

