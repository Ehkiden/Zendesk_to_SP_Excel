import json
import requests
from datetime import datetime, timedelta
import ms_graph_sp_PolicyReview
import os

'''
might need to cover the potential situation where ticket created >14 days are then closed but will not be updated in the excel file
'''

# query ref: developer.zendesk.com/documentation/ticketing/using-the-zendesk-api/searching-with-the-zendesk-api/

# format data into nested array
def query_format(zendesk_resp):
    # excel fields: Ticket ID, Status, Severity, Subject, Origin, Requestor, Requested Time, Resolved Time, Assignee, Assignee Group, Current Review Notes, Last Review Notes
    zendesk_rows = []

    for i in zendesk_resp['values']:
        zendesk_rows.append([i['id'], i['status'], i['priority'], i['subject'], 'Zendesk', i['requester_id'], i['created_at'], i['updated_at'], i['assignee_id'], 'Data Security', '', ''])

    zendesk_rowsV2 = {"values": zendesk_rows}

    return zendesk_rowsV2

def id_to_str(zendesk_resp, user, pwd):
    id_fields = ['requester_id', 'submitter_id', 'assignee_id']
    url_tenant = os.environ['url_tenant']
    headers = {
        "Content-Type": "application/json",
    }

    # iterate through the zendesk tickets and update the desired key values
    index = 0
    for dic in zendesk_resp['values']:
        for i in id_fields:
            if i in dic:
                if dic[i]:
                    try:
                        response = json.loads(requests.get(f"https://{url_tenant}.zendesk.com/api/v2/users/{dic[i]}/identities", auth=(user, pwd), headers=headers).content)

                        zendesk_resp['values'][index][i] = response['identities'][0]['value']

                    except:
                        # if there is any errors trying to get the ID, just fill it with a empty value
                        zendesk_resp['values'][index][i] = ""
                        # raise e
                else:
                    zendesk_resp['values'][index][i] = ""
                
        index += 1

    return zendesk_resp


def lambda_handler(event, context):
    # Set the request parameters
    user = os.environ['user']
    pwd = os.environ['pwd']
    url_tenant = os.environ['url_tenant']
    url = f'https://{url_tenant}.zendesk.com/api/v2/search.json'

    # get the time delta for the past 7 days
    time_delta = (datetime.today() - timedelta(weeks=1)).strftime("%Y-%m-%d")

    # Prod query
    params = {
        'query': f'group:"Data Security" -subject:"FW: [Box Shield]*" -subject:"New Hauler Portal Setup Notification" created>{time_delta}'
    }

    try:
        response = json.loads(requests.get(url, auth=(user, pwd), params=params).content)
    except requests.exceptions.HTTPError as e:
        raise e

    # use a boolean flag to indicate if a match for the current i has already been found
    flag_bool = False
    filtered_resp = {'values':[]}
    for i in response['results']:
        for j in i['tags']:
            if "incident" in j and flag_bool == False:
                filtered_resp['values'].append(i)
                flag_bool = True
        flag_bool = False

    # NOTE: could try adding the user ids to str vals to a local json to reduce the amount of requests we send to zendesk but tis a pipe dream
    update_resp = id_to_str(filtered_resp, user, pwd)

    zendesk_rows = query_format(update_resp)

    ms_graph_sp_PolicyReview.main(zendesk_rows)

    return {
        'statusCode': 200,
        'body': json.dumps('Script exited Successfully!')
    }

