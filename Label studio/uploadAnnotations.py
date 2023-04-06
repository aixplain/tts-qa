import json
import requests
import pandas as pd

def getAllTasksPerProject(url, header, projectID):
    output = list()
    response = '[200]'
    i = 1
    while '[200]' in str(response):
        fullUrl = 'http://' + url +'/api/projects/' + str(projectID) + '/tasks/?page=' + str(i)
        response = requests.get(fullUrl, headers=header)
        if '[200]' in str(response):
            output.append(response)
        i += 1
    return output

def getAnnotationsForAllTasksInAProject(projectID, url, headers, organization):
    annotationsPerTaskPerProject = {}
    response = getAllTasksPerProject(url, headers, projectID)
    for r in response:
        for taskInfo in json.loads(r.content):
            key = str(projectID) + '\t' + str(taskInfo['id']) + '\t' + taskInfo['data']['url']
            status = '[not_done]'
            if taskInfo['initial_review_done']:
                status = 'Done'
            
            usersInfo = {}
            if len(taskInfo['annotations']) > 0:
                # for annotation in taskInfo['annotations']:
                annotation = taskInfo['annotations'][len(taskInfo['annotations'])-1]
                df = pd.json_normalize(annotation)
                lastID = ''
                annotationsDict = {}
                created_username = str(df['created_username'][0])
                full_length = 0
                for ss in pd.json_normalize(df['result']).iterrows():
                    for s in ss[1]:
                        if 'id' in s:
                            if s['from_name'] == 'Status':
                                status = s['value.choices'][0]
                                if 'Done' in status:
                                    status = 'Done'
                            if s['id'] not in annotationsDict:
                                annotationsDict[s['id']] = {}
                            if s['type'] == 'labels' and 'value.labels' in s:
                                annotationsDict[s['id']][s['from_name']] = s['value.labels']
                            elif s['type'] == 'choices':
                                annotationsDict[s['id']][s['from_name']] = s['value.choices']
                            elif s['type'] == 'textarea':
                                annotationsDict[s['id']][s['from_name']] = s['value.text']
                            if 'value.start' in s:
#                                    print(str(json.dumps(taskInfo)))
                                annotationsDict[s['id']]['start'] = s['value.start']
                                annotationsDict[s['id']]['end'] = s['value.end']
                                annotationsDict[s['id']]['len'] = s['value.end'] - s['value.start']
                                if full_length < s['value.end']:
                                    full_length = s['value.end']
                for s in annotationsDict:
                    speaker = 'Unknown'
                    if 'labels' in annotationsDict[s] and len(annotationsDict[s]['labels']) > 0:
                        speaker = str(annotationsDict[s]['labels'][0])
                    elif 'labels' in annotationsDict[s]:
                        print(s + '\t' + str(annotationsDict[s]['labels']))
                    if 'asr1' in annotationsDict[s]:
                        annotationsDict[s]['segment_transcription'] = annotationsDict[s]['asr1']
                    elif 'text1' in annotationsDict[s]:
                        annotationsDict[s]['segment_transcription'] = annotationsDict[s]['text1']
                    redFlags = 'None'
                    # if 'len' not in annotationsDict[s]:
                    #     print(annotationsDict[s])
                    if 'Speaker' in speaker \
                        and 'len' in annotationsDict[s] \
                        and  annotationsDict[s]['len'] > 0 \
                        and len(annotationsDict[s]['segment_transcription'][0].replace('\n', ' ').replace('\t', ' ').strip()) > 1 \
                        and len(annotationsDict[s]['segment_transcription'][0].replace('\n', ' ').replace('\t', ' ').strip().split(' '))/annotationsDict[s]['len'] >= 5:
                        redFlags = 'Too many words'
                    if 'len' in annotationsDict[s]:
                        if taskInfo['id'] not in annotationsPerTaskPerProject:
                            annotationsPerTaskPerProject[taskInfo['id']] = []
                        try:
                            outputElement = {}
                            outputElement['projectID'] = projectID
                            outputElement['TaskID'] = taskInfo['id']
                            outputElement['Filename'] = taskInfo['data']['url']
                            outputElement['ID'] = s
                            outputElement['Status'] = status
                            outputElement['Annotator'] = created_username
                            outputElement['FullFileLength'] = full_length
                            outputElement['SegmentLength'] = annotationsDict[s]['len']
                            outputElement['SegmentStart'] = annotationsDict[s]['start']
                            outputElement['SegmentEnd'] = annotationsDict[s]['end']
                            outputElement['Text'] = annotationsDict[s]['segment_transcription'][0].replace('\n', '').replace('\t', '')
                            outputElement['Type'] = annotationsDict[s]['SegmentType'][0]
                            outputElement['Better'] = annotationsDict[s]['BetterText'][0]
                            outputElement['Problems'] = annotationsDict[s]['OtherTags']
                            outputElement['Feedback'] = annotationsDict[s]['feedback'][0]
                            # outputElement['Speaker'] = speaker
                            # outputElement['Organization'] = organization
                            annotationsPerTaskPerProject[taskInfo['id']].append(outputElement)
                        except:
                            pass

    return annotationsPerTaskPerProject

auth_token = '7fbe7f2b6e690b9d63076e16839a713012f25f5a'
headers = {'Content-Type': 'application/json', 'Authorization': f'Token {auth_token}'}
url = 'label.aixplain.com'

# dict = ['1207, 1208'] # put project IDs here
dict = ['1259'] # put project IDs here
with open('anotations.txt', 'w', encoding='utf8') as f:
    for d in dict:
        annotationsOutput = getAnnotationsForAllTasksInAProject(d, url, headers, auth_token)
        for item in annotationsOutput:
            f.write(json.dumps(annotationsOutput[item]) + '\n')