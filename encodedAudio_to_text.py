#from __future__ import unicode_literals, print_function
from google.cloud import speech
from google.cloud import storage
#import ffmpeg
#import sys


prefix = "gs://"

input_bucket_name = 'encoded_audio_landing'
out_bucket_name = 'transcript_landing'



def get_transcripts(input_bucket_name, in_filename):
    storage_client = storage.Client()
    bucket = storage_client.bucket(input_bucket_name)
    blob = bucket.blob(in_filename)
    gcs_uri = prefix + input_bucket_name + "/" + blob.name
    print(gcs_uri)

    # diarization_config = speech.SpeakerDiarizationConfig(
    # enable_speaker_diarization=True,
    # min_speaker_count=2,
    # max_speaker_count=5,
    # )

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        #use_enhanced=True,
        model= 'medical_conversation', #'phone_call',
        #diarization_config=diarization_config
        audio_channel_count=2,
        enable_separate_recognition_per_channel=True,        
    )
    
    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    response = operation.result(timeout=600)

    # for i, result in enumerate(response.results):
    #     alternative = result.alternatives[0]
    #     print("-" * 20)
    #     print("First alternative of result {}".format(i))
    #     print(u"Transcript: {}".format(alternative.transcript))
    #     print(u"Channel Tag: {}".format(result.channel_tag))
  
    transcripts_json = type(response).to_json(response)
    print('transcribed')
    #move transcript to landing bucket
    print('loading bucket')
    storage_client = storage.Client()
    bucket = storage_client.bucket(out_bucket_name)
    blob = bucket.blob(blob.name)
    blob.upload_from_string(transcripts_json)
    
    return response


def hello_gcs(event, context):
    """Background Cloud Function to be triggered by Cloud Storage.
       This generic function logs relevant data when a file is changed,
       and works for all Cloud Storage CRUD operations.
    Args:
        event (dict):  The dictionary with data specific to this type of event.
                       The `data` field contains a description of the event in
                       the Cloud Storage `object` format described here:
                       https://cloud.google.com/storage/docs/json_api/v1/objects#resource
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None; the output is written to Cloud Logging
    """

    #print('Event ID: {}'.format(context.event_id))
    #print('Event type: {}'.format(context.event_type))
    print('Bucket: {}'.format(event['bucket']))
    print('File: {}'.format(event['name']))
    print('Metageneration: {}'.format(event['metageneration']))
    #print('Created: {}'.format(event['timeCreated']))
    #print('Updated: {}'.format(event['updated']))

    #convert audio encoding
    print('begin create uri')
    get_transcripts(input_bucket_name, event['name'])

   
 
  
#event = {'event_id': 4492351699804882, 'name' : '193065539533.wav', 'metageneration': 1, 'bucket': 'mdata_start', 'data': '/BUS4594041-DL/198253050000/198253051659.wav'}
#context = {'event_id': 4492648559929430, 'timestamp': '2022-04-28T17:40:42.119Z', 'event_type': 'google.storage.object.finalize', 'resource': {'service': 'storage.googleapis.com', 'name': 'projects/_/buckets/mdata_start/objects/GRC_Call.csv', 'type': 'storage#object'}}

#hello_gcs(event, context)