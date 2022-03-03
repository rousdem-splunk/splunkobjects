
import urllib
import os
import sys
import requests
import xml.dom.minidom as minidom
from requests.exceptions import HTTPError

###############
### Config ####
###############
SPLUNK_8000="http://localhost:8000/"
SPLUNK_LOGIN="http://localhost:8000/en-US/account/login"
SPLUNK_VIEWS='http://localhost:8000/en-US/splunkd/__raw/servicesNS/-/-/data/ui/views/'
SPLUNK_VIEWS8089='https://localhost:8089/servicesNS/-/-/data/ui/views/'
loginData={ "username": "admin", "password": "a" }
auth=("admin","a")
headers = { 'Content-type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest', 'Connection':'Keep-alive', }
cookies={}
cval={}

pageSize = 30

#-- Testing with file input
#FileName="./sample_parser.xml"

##############
### Parsing ###
##############
def def_mkdir(dirname):
  output_dir = "./views"
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
        #print("skey --> {}={}\n".format(key, node.firstChild.data ))
        if (key == 'eai:data'):
          for data in node.childNodes:
            fn.write(data.nodeValue)

def def_write_details(content, title):
  try:
    path=def_mkdir(title)
    if isinstance(content, minidom.Element):
      with open (path+"/"+"detail.txt","w") as fn:
        def_extract_kv(content, fn)
    else :
      with open (path+"/"+"detail.txt","wb") as fn:
        def_extract_kv(content, fn)
        
  except Exception as e:
    print("## Exception in def_write_details {}".format(e))
    sys.exit()

def getFromSplunk():
  getPage=True
  page=0
  s = requests.Session()
  adapt = requests.adapters.HTTPAdapter(max_retries=3)

  while getPage:
    params={"count":pageSize,"offset":page*pageSize}
  
    ###############################
    ### Get  saved searches #####
    ###############################
    try:
      r = s.get(SPLUNK_VIEWS8089, headers=headers, auth=auth, params = params, verify=False)
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
      def_write_details(content, title.firstChild.data)

    page+=1
    if (searchSize < page*pageSize):
      getPage = False

def main():
  getFromSplunk()

if __name__ == "__main__":
  main()
