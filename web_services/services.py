#!/usr/bin/env python

"""
This script implements the VMChecker's Web Services.
It's based on apache2 and mod_python.
"""


# Use simplejson or Python 2.6 json, prefer simplejson.
try:
    import simplejson as json
except ImportError:
    import json

import os
import sys
import ldap
import tempfile
import subprocess
import time
import traceback

import ConfigParser
from mod_python import Cookie, apache, Session

from vmchecker.courselist import CourseList
from vmchecker import submit, config, assignments


# define ERROR_MESSAGES
ERR_AUTH = 1
ERR_EXCEPTION = 2 
ERR_OTHER = 3

LDAP_SERVER = ""
LDAP_REQ_OU = []
LDAP_BIND_USER = ""
LDAP_BIND_PASS = ""

class OutputString():
    def __init__(self):
        self.st = ""

    def write(self, st):
        self.st += st
	
    def get(self):
        return self.st 

# using a LDAP server
def get_user(credentials):
    try:
        con = ldap.initialize(LDAP_SERVER)
        con.simple_bind_s(LDAP_BIND_USER,
                         LDAP_BIND_PASS)
   
        baseDN = 'dc=cs,dc=curs,dc=pub,dc=ro'
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = None 
        searchFilter = 'uid=' + credentials['username'] 
        timeout = 0
        count = 0

        # find the user's dn
        result_id = con.search(baseDN, 
                          searchScope, 
                          searchFilter, 
                          retrieveAttributes)
        result_set = []
        while 1:
            result_type, result_data = con.result(result_id, timeout)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    result_set.append(result_data)

        if len(result_set) == 0:
            #no results
            return None

        if len(result_set) > 1:
            # too many results for the same uid
            raise

        user_dn, entry = result_set[0][0]	
	    con.unbind_s()
    except:
        raise 
    
    # check the password 
    try:  
        con = ldap.initialize(LDAP_SERVER)
        con.simple_bind_s(user_dn,
                          credentials['password'])
    except ldap.INVALID_CREDENTIALS:
        return None
    except:
        raise

    return entry['cn'][0]

  
# Generator to buffer file chunks
def fbuffer(f, chunk_size=10000):
    while True:
        chunk = f.read(chunk_size)
        if not chunk: 
            break
        yield chunk


########## @ServiceMethod
def uploadAssignment(req, courseId, assignmentId, archiveFile):
    """ Saves a temp file of the uploaded archive and calls
        vmchecker.submit.submit method to put the homework in
        the testing queue"""
	
    # Check permission
    s = Session.Session(req)
    if s.is_new():
        s.invalidate()
        return json.dumps({'errorType':ERR_AUTH,
                'errorMessage':"",
                'errorTrace':""})

    strout = OutputString()
    try:
        s.load()
        username = s['username']
    except:
        traceback.print_exc(file = strout)
        return json.dumps({'errorType':ERR_EXCEPTION,
            'errorMessage':"",
            'errorTrace':strout.get()})  	
	
    # Reset the timeout
    s.save()

    if archiveFile.filename == None:
        return  json.dumps({'errorType':ERR_OTHER,
                    'errorMessage':"File not uploaded.",
                    'errorTrace':""})

    #  Save file in a temp
    fd, tmpname = tempfile.mkstemp('.zip')
    f = open(tmpname, 'wb', 10000)
    ## Read the file in chunks
    for chunk in fbuffer(archiveFile.file):
        f.write(chunk)
    f.close()

    # Call submit.py
    ## Redirect stdout to catch logging messages from submit
    strout = OutputString()
    sys.stdout = strout
    try:
        status = submit.submit(tmpname, assignmentId, 
                   username, courseId)
    except:
        traceback.print_exc(file = strout)
        return json.dumps({'errorType':ERR_EXCEPTION,
            'errorMessage':"",
            'errorTrace':strout.get()})
	
    return json.dumps({'status':status,
                       'dumpLog':strout.get()}) 


########## @ServiceMethod
def getResults(req, courseId, assignmentId):
    """ Returns the result for the current user"""

    # Check permission 	
    s = Session.Session(req)
    if s.is_new():
        s.invalidate()
        return json.dumps({'errorType':ERR_AUTH,
                'errorMessage':"",
                'errorTrace':""})

    # Get username session variable
    strout = OutputString()
    try:
        s.load()
        username = s['username']
    except:
        traceback.print_exc(file = strout)
        return json.dumps({'errorType':ERR_EXCEPTION,
                'errorMessage':"",
                'errorTrace':strout.get()})  	
		 	
    # XXX E nevoie? Redirect stdout
    strout = OutputString()
    sys.stdout = strout
    try:
        vmcfg = config.CourseConfig(CourseList().course_config(courseId))
    except:
        traceback.print_exc(file = strout)
        return json.dumps({'errorType':ERR_EXCEPTION,
            'errorMessage':"",
            'errorTrace':strout.get()})  	
						
    r_path =  vmcfg.repository_path() + "/" + assignmentId + \
            "/" + username + "/results/"

    # Reset the timeout
    s.save()

    if not os.path.isdir(r_path):
        #TODO fortune
        #TODO cand se updateaza baza de date?
        return json.dumps({'resultLog':'The results are not ready.'});
    else:
        resultlog = ""
        for fname in os.listdir(r_path):
            f_path = os.path.join(r_path, fname)
            if os.path.isfile(f_path):
                f = open(f_path, "r")
                resultlog += "===== " + fname + " =====\n"
                resultlog += f.read()
        return json.dumps({'resultlog':resultlog})


######### @ServiceMethod
def getCourses(req):
    """ Returns a JSON object containing the list of available courses """

    s = Session.Session(req)
    if s.is_new():
        s.invalidate()
        return json.dumps({'errorType':ERR_AUTH,
                'errorMessage':"",
                'errorTrace':""})
		
    # Reset the timeout
    s.save()

    strout = OutputString()
    try:
        clist = CourseList()
    except:
        traceback.print_exc(file = strout)
        return json.dumps({'errorType':ERR_EXCEPTION,
             'errorMessage':"",
             'errorTrace':strout.get()})  	
				
    course_arr = []
    for course_id in clist.course_names():
        course_arr.append({'id' : course_id,
            'title' : course_id}) # XXX: TODO: get a long name
    return json.dumps(course_arr)


######### @ServiceMethod
def getAssignments(req, courseId): 
    """ Returns the list of assignments for a given course """

    s = Session.Session(req)
    if s.is_new():
        s.invalidate()
        return json.dumps({'errorType':ERR_AUTH,
                'errorMessage':"",
                'errorTrace':""})
		
    # Reset the timeout
    s.save()

    strout = OutputString()
    try:
        vmcfg = config.CourseConfig(CourseList().course_config(courseId))
    except:
        traceback.print_exc(file = strout)
        return json.dumps({'errorType':ERR_EXCEPTION,
            'errorMessage':"",
            'errorTrace':strout.get()})  	
		
    assignments = vmcfg.assignments()
    ass_arr = []

    for key in assignments:
        a = {}
        a['assignmentId'] = key
        a['assignmentTitle'] = assignments.get(key, "AssignmentTitle")
        a['deadline'] = assignments.get(key, "Deadline")
        ass_arr.append(a)
    return json.dumps(ass_arr)


######### @ServiceMethod
def login(req, username, password):
    s = Session.Session(req)

    if not s.is_new():
	#TODO take the username from session
        return json.dumps({'status':True, 'username':username,
            'info':'Already logged in'})

    strout = OutputString()
    try:
        user = get_user({'username' : username, 'password' : password}) 
    except:
        traceback.print_exc(file = strout)
        return json.dumps({'errorType':ERR_EXCEPTION,
            'errorMessage':"",
            'errorTrace':strout.get()})  	

    if user is None:
        s.invalidate()
        return json.dumps({'status':False, 'username':"", 
            'info':'Invalid username/password'})

    s["username"] = user
    s.save()
    return json.dumps({'status':True, 'username':user,
            'info':'Succesfully logged in'})


######### @ServiceMethod
def logout(req):
    s = Session.Session(req)
    s.invalidate()
    return json.dumps({'info':'You logged out'})