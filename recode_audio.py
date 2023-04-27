#from __future__ import unicode_literals, print_function
#from asyncio.windows_utils import pipe
from google.cloud import speech
from google.cloud import storage
import ffmpeg
import sys
import tempfile
from werkzeug.utils import secure_filename
import os


out_bucket = 'encoded_audio_landing'
input_bucket_name = 'audio_landing'

#this gets around downloading the file to a local folder. it creates some sort of templ location
def get_file_path(filename):
    file_name = secure_filename(filename)
    return os.path.join(tempfile.gettempdir(), file_name)


def process_audio(input_bucket_name, in_filename, out_bucket):
    '''
    converts audio encoding for GSK call center call recordings to linear16 encoding and 16,000
    hertz sample rate

    Params:
        in_filename: a gsk call audio file
        input_bucket_name: location of the sourcefile that needs to be re-encoded
        out_bucket: where to put the newly encoded file

    returns an audio file encoded so that google speech to text api can transcribe
    '''
    storage_client = storage.Client()
    bucket = storage_client.bucket(input_bucket_name)

    blob = bucket.blob(in_filename)

    print(blob.name)

    #creates some sort of temp loaction for the tile
    file_path = get_file_path(blob.name)
 
   
    blob.download_to_filename(file_path)
    print('type contents: ', type('processedfile'))
    #print('blob name / len / type', blob.name, len(blob.name), type(blob.name))

    #envokes the ffmpeg library to re-encode the audio file, it's actually some sort of command line application
    #   that is available in Python and google cloud. The things in the .outuput bit are options from ffmpeg, you
    #   pass these options into ffmpeg there
    try:
        out, err = (
            ffmpeg.input(file_path)
            #ffmpeg.input()
            .output('pipe: a', format="s16le", acodec="pcm_s16le", ac=2, ar="16k")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

    up_bucket = storage_client.bucket(out_bucket)
    up_blob = up_bucket.blob(blob.name)
    #print('type / len out', type(out), len(out))
    up_blob.upload_from_string(out)

    #delete source file
    blob.delete()




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
    print('begin process_audio')
    process_audio(input_bucket_name, event['name'], out_bucket)


  
#event = {'event_id': 4492351699804882, 'name' : '193065539533.wav', 'metageneration': 1, 'bucket': 'mdata_start', 'data': '/BUS4594041-DL/198253050000/198253051659.wav'}
#context = {'event_id': 4492648559929430, 'timestamp': '2022-04-28T17:40:42.119Z', 'event_type': 'google.storage.object.finalize', 'resource': {'service': 'storage.googleapis.com', 'name': 'projects/_/buckets/mdata_start/objects/GRC_Call.csv', 'type': 'storage#object'}}

#hello_gcs(event, context)