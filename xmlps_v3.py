#!/usr/bin/env python
import urllib
import os
import sys
import requests
import xml.dom.minidom as minidom
from requests.exceptions import HTTPError

#-----------------------------------------------------------------------------------------------------
#https://conf.splunk.com/files/2016/slides/extending-splunks-rest-api-for-fun-and-profit.pdf
# http://localhost:8000/en-US/splunkd/__raw" is important ####
# Doc: https://docs.splunk.com/Documentation/StreamApp/7.1.3/DeployStreamApp/SplunkAppforStreamRESTAPI
#https://docs.python.org/3/library/xml.dom.html
#https://www.splunk.com/en_us/blog/tips-and-tricks/splunk-rest-api-is-easy-to-use.html
#https://docs.splunk.com/DocumentationStatic/RubySDK/1.0.5/test/data/atom/atom_with_several_entries_xml.html
#-----------------------------------------------------------------------------------------------------

###############
### Config ####
###############
SPLUNK_8000="http://localhost:8000/"
SPLUNK_LOGIN="http://localhost:8000/en-US/account/login"
SPLUNK_RAW="http://localhost:8000/en-US/splunkd/__raw/"
SPLUNK_SS='http://localhost:8000/en-US/splunkd/__raw/servicesNS/-/-/saved/searches/'


# SPLUNK_RAW="https://products-telemetry.splunkcloud.com/en-US/splunkd/__raw/"
# SPLUNK_SS='https://products-telemetry.splunkcloud.com/servicesNS/-/-/saved/searches/'
# SPLUNK_8000="https://products-telemetry.splunkcloud.co"
# SPLUNK_LOGIN="https://products-telemetry.splunkcloud.com/en-US/account/login"



# SPLUNK_SS='http://localhost:8000/en-US/splunkd/__raw/servicesNS/-/-/data/ui/views'
loginData={ "username": "<admin user name>", "password": "<place admin password here>" }
headers = { 'Content-type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest', 'Connection':'Keep-alive', }
cookies={}
cval={}

pageSize = 30

#-- Testing with file input
#FileName="./sample_parser.xml"

###################
# howToDownload:
#0:def_write_details - get all once and write
#  - default 0: no need to download it each time.
#1:def_session_get_details - get a search each time.
###################
howToDownload = 0

##############
### Parsing ###
##############
def def_mkdir(dirname):
  output_dir = "./output"
  path = os.path.join(output_dir, dirname)
  if not os.path.exists(path):
    os.makedirs(path)
  return(path)

def def_extract_kv(content, fn):
  configs={}
  sdict = content.getElementsByTagName("s:dict")[0]
  for node in sdict.childNodes:
    if (node.nodeType!=node.TEXT_NODE and node.nodeName == 's:key'):
      key=node.getAttribute("name")
      if node.firstChild is not None:
        #print("skey --> {}={}\n".format(key, node.firstChild.nodeValue ))
        if (key != 'eai:acl'):
            configs[key]=node.firstChild.nodeValue
  for k,v in configs.items():
    fn.write ("{}={}\n".format(k,v))



#  skeys=sdict.getElementsByTagName("s:key")
#  for skey in skeys:
#    key=skey.attributes["name"].value
#    if skey.firstChild is not None:
#      fn.write("{}={}\n".format(key, skey.firstChild.nodeValue ))
#    else:
#      fn.write("{}\n".format(key))


def def_write_details(content, title):
  try:
    path=def_mkdir(title)
    if isinstance(content, minidom.Element):
      with open (path+"/"+"savedsearches.conf","w") as fn:
        def_extract_kv(content, fn)
    else :
      with open (path+"/"+"savedsearches.conf","wb") as fn:
        def_extract_kv(content, fn)

  except Exception as e:
    print("## Exception in def_write_details {}".format(e))
    sys.exit()

""" <entry>
    <title>Bucket Copy Trigger</title>
    <id>https://10.140.48.173:8000/servicesNS/nobody/splunk_archiver/saved/searches/Bucket%20Copy%20Trigger</id>
    <link href="/servicesNS/nobody/splunk_archiver/saved/searches/Bucket%20Copy%20Trigger" rel="alternate"/>
"""
def def_session_get_details(entry, title):
  for link in entry.getElementsByTagName("link"):
     if link.getAttribute("rel") in ["list", "alternate"]:
       urlref = link.getAttribute("href")[1:]
       resp = s.get(SPLUNK_URL+urlref,  headers=headers, cookies=cookies)
       if resp.status_code != 200:
         print("ERROR title:{} >> {}{}".format(title, SPLUNK_URL,urlref))
         return

       xmlData = minidom.parseString(resp.content)
       if xmlData.getElementsByTagName("opensearch:totalResults"):
         searchSize=int(xmlData.getElementsByTagName("opensearch:totalResults")[0].firstChild.wholeText)
         if searchSize==1:
           def_write_details(resp.content,title)
       else:
         print(">>> no opensearch:totalResults")

def getFromSplunk(howToDownload):
  getPage=True
  page=0
  s = requests.Session()
  adapt = requests.adapters.HTTPAdapter(max_retries=3)
  try:
    r = s.post(SPLUNK_8000, data=loginData)
    r.raise_for_status()
  except HTTPError as http_err:
    print ("### HTTP Error received : {}".format(http_err))
    sys.exit()
  except Exception as e:
    print("## Exception: {}".format(e))
    sys.exit()

  cookies_dict = r.cookies.get_dict()
  #cval['cval'] = cookies_dict['cval']
  loginData['cval'] = cookies_dict['cval']

  r = s.post(SPLUNK_LOGIN, headers=headers, data=loginData, verify=False)
  if (r.status_code != 200):
    print("2nd failed, {}".format(r.status_code))
    sys.exit()

  cookies_dict = r.cookies.get_dict()
  cookies['splunkweb_csrf_token_8000'] = cookies_dict['splunkweb_csrf_token_8000']
  cookies['splunkd_8000'] = cookies_dict['splunkd_8000']
  headers['X-Splunk-Form-Key'] = cookies_dict['splunkweb_csrf_token_8000']

  while getPage:
    params={"count":pageSize,"offset":page*pageSize}

    ###############################
    ### Get  saved searches #####
    ###############################
    try:
      r = s.get(SPLUNK_SS, headers=headers, cookies=cookies, params = params)
      r.raise_for_status()
    except HTTPError as http_error:
      print("### get :{}".format(http_error))
      sys.exit()

    p=minidom.parseString(r.content)
    if p.getElementsByTagName("opensearch:totalResults"):
      searchSize=int(p.getElementsByTagName("opensearch:totalResults")[0].firstChild.wholeText)
      offset=int(p.getElementsByTagName("opensearch:startIndex")[0].firstChild.wholeText)
    entries = p.getElementsByTagName('entry')
    # printing status
    print("##### Printing searches ...{}/{}".format(entries.length+params['offset'], searchSize))
    count=0
    for ent in entries:
      count+=1
      title = ent.getElementsByTagName("title")[0]
      content = ent.getElementsByTagName("content")[0]
      print ("#----- entry{}: {} prettyxml --".format(count, title.firstChild.data))

      if howToDownload == 0:
        def_write_details(content, title.firstChild.data)
      # else:
      #   def_session_get_details(ent, title.firstChild.data)
    page+=1
    if (searchSize < page*pageSize):
      getPage = False

def main():
  getFromSplunk(howToDownload)

if __name__ == "__main__":
  main()
