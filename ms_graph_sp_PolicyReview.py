import json
import requests
import os

'''
Reference links for uploading excel rows:
    https://learn.microsoft.com/en-us/graph/api/table-post-rows?view=graph-rest-1.0&tabs=http
    https://learn.microsoft.com/en-us/answers/questions/811341/is-there-any-graph-api-to-append-row-to-excel-work

    Note:   Ran into an issue where the script was unable to download/upload the excel file if the file was open somewhere else. 
            Switched to updating the rows instead of replacing the entire file.
'''

def token_gains():
    appId = os.environ['appId']
    appSecret = os.environ['appSecret']
    tenantId = os.environ['tenantId']

    # Azure Active Directory token endpoint.
    url = "https://login.microsoftonline.com/%s/oauth2/v2.0/token" % (tenantId)
    body = {
        'client_id' : appId,
        'client_secret' : appSecret,
        'grant_type' : 'client_credentials',
        'scope': 'https://graph.microsoft.com/.default'
    }

    # authenticate and obtain AAD Token for future calls
    resp = json.loads(requests.post(url, data=body).content)

    # Grab the token from the response then store it in the headers dict.
    return resp["access_token"]

def sp_upload(incident_array, aadToken, excelFile_id, siteId, tbl_id):
    headers = { 
        'Content-Type' : 'application/json',
        'Accept' : 'application/json',
        'Authorization' : "Bearer " + aadToken
    }

    sp_url  = f"https://graph.microsoft.com/v1.0/sites/{siteId}/drive/items/{excelFile_id}/workbook/tables/{tbl_id}/rows"

    try:
        sp_response = json.loads(requests.post(sp_url, headers=headers, json=incident_array).content)
        print("Zendesk incidents appended to Review excel file successfully.")

    except requests.exceptions.HTTPError as e:
        print("An error occured during the upload attempt.")
        raise e


def main(incident_array):
    # Grab the token 
    aadToken = token_gains()
    headers = { 
        'Content-Type' : 'application/json',
        'Accept' : 'application/json',
        'Authorization' : "Bearer " + aadToken
    }

    # Prod vars
    siteId = os.environ['siteId'] # Policy & Exception Teams site
    tbl_id = "Incidents_tbl"
    excelFile_id = os.environ['excelFile_id'] # prod final excel file id

    # append the incidents array to the bottom of the excel sheet
    sp_upload(incident_array, aadToken, excelFile_id, siteId, tbl_id)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Script exited Successfully!')
    }
