# -*- coding: utf-8 -*-

import datetime
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import cv2
import numpy as np
import sys
import ibmiotf.application
import ibmiotf.device
import random
import time

from cloudant.client import Cloudant
from cloudant.error import CloudantException 
from cloudant.result import Result, ResultByKey
#Provide your IBM Watson Device Credentials
organization = "yj35v1"
deviceType = "project"
deviceId = "7777"
authMethod = "token"
authToken = "123456789"



def myCommandCallback(cmd):
        print("Command received: %s" % cmd.data)
        print(cmd.data['command'])
       
        if(cmd.data['command']=="open"):
                print("gate open")
                
        if(cmd.data['command']=="close"):
                print("gate close")
                

        if(cmd.data['command']=="entry"):
                print("entry")
                
        if(cmd.data['command']=="exit"):
                print("exit")
               
        if(cmd.data['command']=="filled slots"):
                print("filled slots")
        if(cmd.data['command']=="empty slots"):
                print("empty slots")

try:
	deviceOptions = {"org": organization, "type": deviceType, "id": deviceId, "auth-method": authMethod, "auth-token": authToken}
	deviceCli = ibmiotf.device.Client(deviceOptions)
	#..............................................
	
except Exception as e:
	print("Caught exception connecting device: %s" % str(e))
	sys.exit()

# Connect and send a datapoint "hello" with value "world" into the cloud as an event of type "greeting" 10 times
deviceCli.connect()
car_classifier=cv2.CascadeClassifier("cars.xml")


#It will read the first frame/image of the video
video=cv2.VideoCapture('cars2.mp4')



COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "tD4oM6k1dLctb5ZW6yr103quV_5hpuD18XQGw6D1zPYx" # eg "W00YiRnLW4a3fTjMB-oiB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/3f309106247d4e799cc270a23f1bde40:1fb7171d-ba67-4ee9-9b7c-b767eab3a7f4::"

client = Cloudant("d613fe38-fcff-4aa6-af10-9bbad53806c9-bluemix", "8f01736ba3c010370fe6a4e6c4f851b6c2da83ef4bf65412aa292019e3c5e72b", url="https://d613fe38-fcff-4aa6-af10-9bbad53806c9-bluemix:8f01736ba3c010370fe6a4e6c4f851b6c2da83ef4bf65412aa292019e3c5e72b@d613fe38-fcff-4aa6-af10-9bbad53806c9-bluemix.cloudantnosqldb.appdomain.cloud")
client.connect()
database_name = "doorbell"

# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_RESOURCE_CRN,
    ibm_auth_endpoint=COS_AUTH_ENDPOINT,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)
        
        
def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))
        # set 5 MB chunks
        part_size = 1024 * 1024 * 5

        # set threadhold to 15 MB
        file_threshold = 1024 * 1024 * 15

        # set the transfer threshold and chunk size
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        # the upload_fileobj method will automatically execute a multi-part upload
        # in 5 MB chunks for all files over 15 MB
        with open(file_path, "rb") as file_data:
            cos.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )

        print("Transfer for {0} Complete!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))
        

       
while True:
    #capture the first frame
    check,frame=video.read()
    gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    #detect the cars from the video using detectMultiScale function
    cars=car_classifier.detectMultiScale(gray,1.1,1)
    
    
    #drawing rectangle boundries for the detected car
    for(x,y,w,h) in cars:
        cv2.rectangle(frame, (x,y), (x+w,y+h), (127,0,255), 2)
        cv2.imshow('cars detection', frame)
        picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        picname=picname+".jpg"
        pic=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        cv2.imwrite(picname,frame)
        car=5
        my_database = client.create_database(database_name)        
        multi_part_upload("cloud-object-storage-dsx-cos-standard-jbp",picname,pic+".jpg")      
        if my_database.exists():
            print("'{database_name}' successfully created.")
            json_document = {
                    "_id": pic,
                    "link":COS_ENDPOINT+"/cloud-object-storage-dsx-cos-standard-jbp/"+picname
                    }
            new_document = my_database.create_document(json_document)
            if new_document.exists():
                print("Document '{new_document}' successfully created.")
        time.sleep(1)
        f=34
        e=45
        data = {"d":{ 'filledslots' : f, 'emptyslots': e, 'car': car}}
        #print data
        def myOnPublishCallback():
            print ("Published data to IBM Watson")

        success = deviceCli.publishEvent("Data", "json", data, qos=0, on_publish=myOnPublishCallback)
        if not success:
            print("Not connected to IoTF")
        time.sleep(1)
        deviceCli.commandCallback = myCommandCallback
        car=0
    #waitKey(1)- for every 1 millisecond new frame will be captured
        Key=cv2.waitKey(1)
        if Key==ord('q'):
        #release the camera
            video.release()
        #destroy all windows
            cv2.destroyAllWindows()
            break
deviceCli.disconnect()
    
